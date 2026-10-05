extends Node
## The connection to the Python core (spec 007, contracts/local-api.md).
##
## Starts `pythonw -m manager_core.server` as a child process and talks to it over its stdio,
## one JSON message per line. Callers `await Core.request(method, params)` and get either
## {"result": ...} or {"error": {"code", "message", "data"}}. No game rules live here
## (Constitution III): this node only carries requests and answers.

signal state_changed(new_state: String)
signal busy_changed(busy: bool)
signal progress(params: Dictionary)

const CONTRACT_MAJOR := 1
const HELLO_TIMEOUT_MS := 30000
const STOP_GRACE_MS := 3000
const CONFIG_PATH := "res://core.cfg"
## Messages needed before `hello` brings the catalogue (or when the core is gone).
const LOCAL := {
	"start_failed": "Não foi possível iniciar o núcleo do jogo (Python): {detail}",
	"no_answer": "O núcleo do jogo não respondeu.",
	"version": "Versões incompatíveis: cliente {client}, núcleo {core}. Atualize o projeto.",
	"lost": "O núcleo do jogo parou inesperadamente.",
	"not_running": "O núcleo do jogo não está rodando.",
	"starting": "Iniciando o jogo…",
	"retry": "Tentar de novo",
}

class Pending:
	extends RefCounted
	signal done(answer: Dictionary)

var state := "idle"  ## idle / starting / ready / failed / closed
var failure := ""
var strings: Dictionary = {}
var contract := ""
var core_version := ""
var model_version := ""

var _pid := -1
var _io: FileAccess
var _err: FileAccess
## The core's last diagnostics (stderr), kept for error reports.
var stderr_tail := ""
var _buffer := PackedByteArray()
var _next_id := 0
var _pending: Dictionary = {}


## Start the core and shake hands. Returns true when ready.
func start() -> bool:
	if state == "ready":
		return true
	_set_state("starting")
	var python := _python_path()
	var args := PackedStringArray(["-m", "manager_core.server", "--saves", _saves_path()])
	var info := OS.execute_with_pipe(python, args, false)
	if info.is_empty():
		return _fail(LOCAL["start_failed"].format({"detail": python}))
	_pid = info["pid"]
	_io = info["stdio"]
	_err = info["stderr"]
	var hello := await request("hello", {"client": "godot " + Engine.get_version_info()["string"]},
			HELLO_TIMEOUT_MS)
	if hello.has("error"):
		return _fail(LOCAL["start_failed"].format({"detail": hello["error"]["message"]}))
	var result: Dictionary = hello["result"]
	contract = str(result["contract"])
	if not compatible(contract):
		return _fail(LOCAL["version"].format({"client": "%d.x" % CONTRACT_MAJOR, "core": contract}))
	core_version = str(result["core_version"])
	model_version = str(result["model_version"])
	strings = result["strings"]
	_set_state("ready")
	return true


## Send a request and wait for its answer: {"result": ...} or {"error": {...}}.
func request(method: String, params: Dictionary = {}, timeout_ms: int = 0) -> Dictionary:
	if state not in ["starting", "ready"] or _io == null:
		return _error("P900", LOCAL["not_running"])
	_next_id += 1
	var id := _next_id
	var pending := Pending.new()
	_pending[id] = pending
	_io.store_line(JSON.stringify({"jsonrpc": "2.0", "id": id, "method": method,
			"params": params}))
	_io.flush()
	busy_changed.emit(true)
	if timeout_ms > 0:
		_watch(id, timeout_ms)
	var answer: Dictionary = await pending.done
	if _pending.is_empty():
		busy_changed.emit(false)
	return answer


## Shut the core down cleanly (it saves the open career), then make sure it is gone.
func stop() -> void:
	if state == "ready":
		await request("shutdown", {}, STOP_GRACE_MS)
	if _pid > 0 and OS.is_process_running(_pid):
		OS.kill(_pid)
	_io = null
	_err = null
	_pid = -1
	_set_state("closed")


## Whether a core speaking this contract version can serve this client (same major version).
static func compatible(version: String) -> bool:
	var parts := version.split(".")
	return parts.size() == 2 and parts[0].is_valid_int() and int(parts[0]) == CONTRACT_MAJOR


## A localised string from the core's catalogue, with {placeholders}.
func t(key: String, params: Dictionary = {}) -> String:
	var text: String = strings.get(key, key)
	return text.format(params) if not params.is_empty() else text


func is_busy() -> bool:
	return not _pending.is_empty()


func _process(_delta: float) -> void:
	if _io == null:
		return
	_drain_stderr()
	var chunk := _io.get_buffer(65536)
	if chunk.size() > 0:
		_buffer.append_array(chunk)
		_drain()
	# a core that dies while starting (broken .venv, import error) fails at once, with its error
	if state in ["starting", "ready"] and _pid > 0 and not OS.is_process_running(_pid):
		_lost()


func _drain() -> void:
	while true:
		var newline := _buffer.find(10)
		if newline < 0:
			return
		var line := _buffer.slice(0, newline).get_string_from_utf8()
		_buffer = _buffer.slice(newline + 1)
		if line.strip_edges().is_empty():
			continue
		var message = JSON.parse_string(line)
		if typeof(message) != TYPE_DICTIONARY:
			push_warning("core: unreadable line: " + line.left(200))
			continue
		if not message.has("id"):
			if message.get("method") == "progress":
				progress.emit(message.get("params", {}))
			continue
		_answer(int(message["id"]), message)


func _answer(id: int, message: Dictionary) -> void:
	var pending: Pending = _pending.get(id)
	if pending == null:
		return
	_pending.erase(id)
	if message.has("error"):
		pending.done.emit({"error": message["error"]})
	else:
		pending.done.emit({"result": message.get("result")})


func _watch(id: int, timeout_ms: int) -> void:
	await get_tree().create_timer(timeout_ms / 1000.0).timeout
	if _pending.has(id):
		_answer(id, {"error": {"code": "P901", "message": LOCAL["no_answer"]}})


## Drain stderr: a full pipe would block the core on its next warning; keep the tail for reports.
func _drain_stderr() -> void:
	if _err == null:
		return
	var diagnostics := _err.get_buffer(65536)
	if diagnostics.size() > 0:
		var text := diagnostics.get_string_from_utf8()
		printerr("[core] ", text.strip_edges())
		stderr_tail = (stderr_tail + text).right(4000)


## The last few lines the core wrote to stderr (why it stopped), for the owner.
func last_diagnostics(lines := 3) -> String:
	var all := stderr_tail.strip_edges().split("\n", false)
	return "\n".join(all.slice(max(0, all.size() - lines)))


func _lost() -> void:
	_drain_stderr()
	var message: String = LOCAL["lost"]
	var why := last_diagnostics()
	if not why.is_empty():
		message += "\n" + why
	for id in _pending.keys():
		_answer(id, {"error": {"code": "P902", "message": message}})
	_io = null
	_err = null
	_pid = -1
	_fail(message)


func _fail(message: String) -> bool:
	failure = message
	_set_state("failed")
	return false


func _set_state(new_state: String) -> void:
	state = new_state
	state_changed.emit(new_state)


func _error(code: String, message: String) -> Dictionary:
	return {"error": {"code": code, "message": message}}


func _config() -> ConfigFile:
	var cfg := ConfigFile.new()
	cfg.load(CONFIG_PATH)  # a missing file keeps the defaults below
	return cfg


func _repo() -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").simplify_path()


## The Python to run: MANAGER_PYTHON, else core.cfg, else the repo's .venv (windowless).
func _python_path() -> String:
	var env := OS.get_environment("MANAGER_PYTHON")
	if not env.is_empty():
		return env
	var configured: String = _config().get_value("core", "python", ".venv/Scripts/pythonw.exe")
	return configured if configured.is_absolute_path() else _repo().path_join(configured)


func _saves_path() -> String:
	var env := OS.get_environment("MANAGER_SAVES")
	if not env.is_empty():
		return env
	var configured: String = _config().get_value("core", "saves", "saves")
	return configured if configured.is_absolute_path() else _repo().path_join(configured)

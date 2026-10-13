extends "res://scenes/screen.gd"
## A played match again on the pitch (spec 008b US3): the whole record from the core
## (`match.record`), a timeline to drag, and a jump to each goal, card and penalty. Nothing here
## can change the match.

const Playback := preload("res://scenes/match/playback.gd")
const Pitch := preload("res://scenes/match/pitch.gd")
const SPEEDS := [1.0, 2.0, 4.0, 8.0]
const LEAD_S := 6.0  # a jump lands this long before the event
const JUMP_KINDS := {"goal": "⚽", "own_goal": "⚽", "penalty_goal": "⚽", "penalty_miss": "✖",
		"yellow": "🟨", "second_yellow": "🟥", "red": "🟥"}

var match_id := ""  # the match to watch; empty for the live match just played
var playback: RefCounted
var _replay: Dictionary = {}
var _pitch: Control
var _board: Dictionary
var _slider: HSlider
var _pause_button: Button
var _info: Label
var _speed := 1.0
var _paused := false
var _dragging := false
var _names := {}
var _highlights := false
var _mode_button: Button


func open() -> void:
	clear()
	var found = await ask("match.record", {"match_id": match_id} if match_id != "" else {})
	if found == null:
		if is_inside_tree() and main._message.text == "":
			main.message(UI.t("ui.replay.none"))
		return
	_replay = found
	playback = Playback.new()
	playback.setup(_replay["pitch"])
	playback.add(_replay["frames"])
	for side in ["home", "away"]:
		for p in _replay["pitch"][side]["players"] + _replay["pitch"][side]["bench"]:
			_names[p["player_id"]] = p["name"]
	add_child(UI.title(UI.t("ui.replay.title")))
	_board = UI.scoreboard()
	_board["home"].text = str(_replay["match"]["home_name"]).to_upper()
	_board["away"].text = str(_replay["match"]["away_name"]).to_upper()
	add_child(_board["panel"])
	var controls := UI.row([UI.label(UI.t("ui.desktop.speed"))])
	for speed in SPEEDS:
		controls.add_child(UI.button("%d×" % speed, _set_speed.bind(speed)))
	_pause_button = UI.button(UI.t("ui.live.pause"), toggle_pause)
	controls.add_child(_pause_button)
	_mode_button = UI.button(UI.t("ui.live.mode_highlights"), toggle_highlights)
	_mode_button.visible = not _replay.get("passages", []).is_empty()
	controls.add_child(_mode_button)
	controls.add_child(UI.spacer())
	controls.add_child(UI.button(UI.t("ui.desktop.back"), main.go_back))
	add_child(controls)
	_pitch = Pitch.new()
	_pitch.playback = playback
	_pitch.slot_picked.connect(_show_disc)
	add_child(_pitch)
	_slider = HSlider.new()
	_slider.min_value = 0.0
	_slider.max_value = maxf(1.0, playback.count - 1.0)
	_slider.step = 1.0
	_slider.drag_started.connect(func(): _dragging = true)
	_slider.drag_ended.connect(func(_changed): _dragging = false)
	_slider.value_changed.connect(_on_slider)
	add_child(_slider)
	var jumps := HFlowContainer.new()
	for event in playback.events:
		if JUMP_KINDS.has(event["kind"]):
			jumps.add_child(UI.button(_jump_text(event), jump_to.bind(int(event["sample"]))))
	add_child(jumps)
	_info = UI.label(UI.t("ui.pitch.pick"))
	_info.add_theme_color_override("font_color", UI.MUTE)
	add_child(_info)
	_paint()


func _jump_text(event: Dictionary) -> String:
	var minute: Dictionary = event["minute"]
	var stamp := "%d'" % minute["base"]
	if minute["added"] > 0:
		stamp = "%d+%d'" % [minute["base"], minute["added"]]
	return "%s %s %s" % [stamp, JUMP_KINDS[event["kind"]], _names.get(event["player_id"], "")]


func _process(delta: float) -> void:
	if playback == null or _pitch == null:
		return
	if not _paused and not _dragging:
		playback.advance(delta, _speed)
		if _highlights:
			_keep_to_passages()
	_paint()


## Highlights: outside a passage, go to the start of the next one; after the last, stop.
func _keep_to_passages() -> void:
	var now: float = playback.time_s()
	for passage in _replay["passages"]:
		if now < passage[0]:
			playback.seek(passage[0] * playback.hz)
			return
		if now <= passage[1]:
			return
	playback.seek(playback.count)
	if not _paused:
		toggle_pause()


func toggle_highlights() -> void:
	_highlights = not _highlights
	_mode_button.text = UI.t("ui.live.mode_full" if _highlights else "ui.live.mode_highlights")
	if _highlights and _paused:
		toggle_pause()


func _paint() -> void:
	var score: Array = playback.score()
	_board["score"].text = "%d-%d" % [score[0], score[1]]
	_board["clock"].text = clock_text(playback.playhead)
	_board["note"].text = UI.t("ui.live.paused") if _paused else ""
	if not _dragging:
		_slider.set_value_no_signal(playback.playhead)
	_pitch.queue_redraw()


## The scoreboard's clock at a sample, from the core's table of minute changes.
func clock_text(sample: float) -> String:
	var shown := ""
	for row in _replay.get("clock", []):
		if row[0] > sample:
			break
		shown = ("%d+%d'" % [row[1], row[2]]) if row[2] > 0 else ("%d'" % row[1])
	return shown


func _on_slider(value: float) -> void:
	playback.seek(value)
	_paint()


func _set_speed(speed: float) -> void:
	_speed = speed
	if _paused:
		toggle_pause()


func toggle_pause() -> void:
	_paused = not _paused
	_pause_button.text = UI.t("ui.live.resume") if _paused else UI.t("ui.live.pause")


## Go to a few seconds before an event and play.
func jump_to(sample: int) -> void:
	if _highlights:  # a card is not a highlight: show what was asked for
		toggle_highlights()
	playback.seek(sample - LEAD_S * playback.hz)
	if _paused:
		toggle_pause()
	_paint()


func _show_disc(slot: int) -> void:
	if slot < 0:
		_info.text = UI.t("ui.pitch.pick")
		return
	var who: Dictionary = playback.player(slot)
	_info.text = "%d  %s" % [int(who.get("number", 0)), who.get("name", "")]

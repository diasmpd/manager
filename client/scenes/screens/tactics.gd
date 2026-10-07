extends "res://scenes/screen.gd"
## The user's tactic (spec 007 US2, the 006 Tactics screen): formations, mentality, team
## instructions by phase, IP and OOP roles per slot with suitability, player instructions (role
## locks marked) and set pieces. Double-click cycles a setting; the core validates and saves.

var live := false  # opened from a live match: confirm sends the change to the match
var _options: Dictionary = {}
var _tactic: Dictionary = {}
var _positions: Array = []
var _players: Dictionary = {}  # slot -> player id
var _names: Dictionary = {}
var _roles: Dictionary = {}  # "position|phase" -> [Role]
var _suitability: Dictionary = {}  # "pid|role" -> float
var _slot := 0
var _heading: Label
var _instructions: Tree
var _slots: Tree
var _player_instructions: Tree
var _takers: Tree


func open() -> void:
	clear()
	var options = await ask("tactic.options")
	var tactic = await ask("tactic.current")
	if live:
		var state = await ask("match.state")
		if state != null:
			tactic = state["tactic"]
	var current = await ask("selection.current")
	if options == null or tactic == null or current == null:
		return
	_options = options
	_tactic = tactic
	for pair in current["selection"]["starters"]:
		_players[int(pair[0])] = pair[1]
	for r in current["squad"]:
		_names[r["player_id"]] = r["name"]
	await _load_shape()
	_heading = UI.title("")
	add_child(_heading)
	var left := UI.column([UI.label(UI.t("ui.tactics.instruction"), 16, true)])
	_instructions = UI.table([UI.t("ui.tactics.instruction"), UI.t("ui.tactics.setting")])
	_instructions.item_activated.connect(_cycle_instruction)
	left.add_child(_instructions)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var right := UI.column()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.size_flags_stretch_ratio = 1.5
	_slots = UI.table([UI.t("ui.tactics.slot"), UI.t("ui.tactics.player"), UI.t("ui.tactics.ip_role"),
			UI.t("ui.tactics.oop_role")])
	_slots.item_activated.connect(func(): _cycle_role("ip"))
	_slots.item_selected.connect(_select_slot)
	_player_instructions = UI.table([UI.t("ui.tactics.player_instruction"),
			UI.t("ui.tactics.setting")])
	_player_instructions.item_activated.connect(_cycle_player_instruction)
	_takers = UI.table([UI.t("ui.tactics.taker"), UI.t("ui.tactics.player")])
	_takers.item_activated.connect(_cycle_taker)
	for tree in [_slots, _player_instructions, _takers]:
		right.add_child(tree)
	var columns := UI.row([left, right])
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(columns)
	add_child(UI.row([UI.button(UI.t("ui.tactics.oop_role"), func(): _cycle_role("oop")),
			UI.button(UI.t("ui.desktop.reset"), _reset), UI.spacer(),
			UI.button(UI.t("ui.desktop.back"), main.go_back),
			UI.primary_button(UI.t("ui.desktop.confirm"), _confirm)]))
	add_child(UI.paragraph(UI.t("ui.desktop.tactics_help"), 13))
	_render()


# ---- data --------------------------------------------------------------------------------------


func _load_shape() -> void:
	var formations = await ask("formations.list")
	if formations != null:
		for f in formations:
			if f["name"] == _tactic["ip_formation"]:
				_positions = f["positions"]
	var pairs := []
	for slot in _tactic["slots"]:
		var position: String = _positions[int(slot["slot"])]
		for phase in ["ip", "oop"]:
			var key: String = position + "|" + str(phase)
			if not _roles.has(key):
				_roles[key] = await ask("tactic.roles", {"position": position, "phase": phase})
		var pid = _players.get(int(slot["slot"]))
		if pid != null:
			for phase in ["ip", "oop"]:
				for role in _roles[position + "|" + phase]:
					if not _suitability.has(pid + "|" + role["id"]):
						pairs.append([pid, role["id"]])
	if not pairs.is_empty():
		var values = await ask("tactic.suitability", {"pairs": pairs})
		if values != null:
			for i in pairs.size():
				_suitability[pairs[i][0] + "|" + pairs[i][1]] = values[i]


func _option(list: Array, id: String) -> Dictionary:
	for o in list:
		if o["id"] == id:
			return o
	return {}


func _label(option: Dictionary, setting: String) -> String:
	var i: int = option["settings"].find(setting)
	return option["labels"][i] if i >= 0 else setting


func _team() -> Dictionary:
	var team := {}
	for pair in _tactic["team"]:
		team[pair[0]] = pair[1]
	return team


func _set_team(id: String, setting: String) -> void:
	var team := _team()
	team[id] = setting
	var pairs := []
	var keys := team.keys()
	keys.sort()
	for k in keys:
		pairs.append([k, team[k]])
	_tactic["team"] = pairs


func _next(values: Array, current) -> Variant:
	var i := values.find(current)
	return values[(i + 1) % values.size()] if i >= 0 else values[0]


func _role(position: String, phase: String, id: String) -> Dictionary:
	for r in _roles.get(position + "|" + phase, []):
		if r["id"] == id:
			return r
	return {}


func _locked(slot: Dictionary) -> Dictionary:
	var position: String = _positions[int(slot["slot"])]
	var locked := {}
	for phase in ["ip", "oop"]:
		var role := _role(position, phase, slot[phase + "_role"])
		locked.merge(role.get("locked", {}), true)
	return locked


# ---- drawing -----------------------------------------------------------------------------------


func _render() -> void:
	_heading.text = UI.t("ui.tactics.title", {"club": main.status.get("club_name", ""),
			"ip": _tactic["ip_formation"], "oop": _tactic["oop_formation"],
			"mentality": _label(_options["mentality"], _tactic["mentality"])})
	var rows := [[UI.t("ui.tactics.ip_formation"), _tactic["ip_formation"]],
			[UI.t("ui.tactics.oop_formation"), _tactic["oop_formation"]],
			[UI.t("ui.tactics.mentality"), _label(_options["mentality"], _tactic["mentality"])]]
	var keys := ["ip_formation", "oop_formation", "mentality"]
	var team := _team()
	var phase := ""
	for o in _options["team"]:
		if o["phase"] != phase:
			phase = o["phase"]
			rows.append(["— " + UI.t("tactics.phase." + phase) + " —", ""])
			keys.append("phase:" + phase)
		rows.append(["   " + o["label"], _label(o, team.get(o["id"], o["default"]))])
		keys.append("team:" + o["id"])
	rows.append(["— " + UI.t("tactics.phase.set_pieces") + " —", ""])
	keys.append("phase:set_pieces")
	var setups := {}
	for pair in _tactic["set_pieces"]["setups"]:
		setups[pair[0]] = pair[1]
	for o in _options["setups"]:
		rows.append(["   " + o["label"], _label(o, setups.get(o["id"], o["default"]))])
		keys.append("setup:" + o["id"])
	_redraw(_instructions, rows, keys)
	rows = []
	keys = []
	for slot in _tactic["slots"]:
		var i := int(slot["slot"])
		var position: String = _positions[i]
		var pid = _players.get(i)
		var cells := [position, _names.get(pid, "–")]
		for phase_name in ["ip", "oop"]:
			var role := _role(position, phase_name, slot[phase_name + "_role"])
			var text: String = role.get("label", slot[phase_name + "_role"])
			if pid != null and _suitability.has(pid + "|" + slot[phase_name + "_role"]):
				text += " (%d)" % roundi(_suitability[pid + "|" + slot[phase_name + "_role"]])
			cells.append(text)
		rows.append(cells)
		keys.append(i)
	_redraw(_slots, rows, keys)
	_render_player_instructions()
	rows = []
	keys = []
	for pair in _tactic["set_pieces"]["takers"]:
		var i: int = _options["takers"].find(pair[0])
		var label: String = _options["taker_labels"][i] if i >= 0 else pair[0]
		rows.append([label, _names.get(pair[1], UI.t("ui.tactics.auto")) if pair[1] != null
				else UI.t("ui.tactics.auto")])
		keys.append(pair[0])
	_redraw(_takers, rows, keys)


func _render_player_instructions() -> void:
	var slot: Dictionary = _tactic["slots"][_slot]
	var chosen := {}
	for pair in slot["instructions"]:
		chosen[pair[0]] = pair[1]
	var locked := _locked(slot)
	var rows := []
	var keys := []
	for o in _options["player"]:
		var text: String
		if locked.has(o["id"]):
			text = "%s 🔒 %s" % [_label(o, locked[o["id"]]), UI.t("ui.tactics.locked")]
		else:
			text = _label(o, chosen.get(o["id"], o["default"]))
		rows.append([o["label"], text])
		keys.append(o["id"])
	_redraw(_player_instructions, rows, keys)


func _redraw(tree: Tree, rows: Array, keys: Array) -> void:
	var selected = UI.selected_key(tree)
	UI.fill(tree, rows, keys)
	if selected != null:
		UI.select_key(tree, selected)


# ---- editing -----------------------------------------------------------------------------------


func _cycle_instruction() -> void:
	var key = UI.selected_key(_instructions)
	if key == null:
		return
	main.message("")
	var parts: PackedStringArray = str(key).split(":")
	match parts[0]:
		"ip_formation":
			main.message(UI.t("ui.tactics.formation_from_selection"))
		"oop_formation":
			var choices = await ask("tactic.suggest_oop", {"formation": _tactic["ip_formation"]})
			if choices != null:
				_tactic["oop_formation"] = _next(choices, _tactic["oop_formation"])
		"mentality":
			_tactic["mentality"] = _next(_options["mentality"]["settings"], _tactic["mentality"])
		"team":
			var o := _option(_options["team"], parts[1])
			_set_team(parts[1], _next(o["settings"], _team().get(parts[1], o["default"])))
		"setup":
			var o := _option(_options["setups"], parts[1])
			var setups: Array = _tactic["set_pieces"]["setups"]
			for pair in setups:
				if pair[0] == parts[1]:
					pair[1] = _next(o["settings"], pair[1])
	_render()


func _select_slot() -> void:
	var key = UI.selected_key(_slots)
	if key != null and int(key) != _slot:
		_slot = int(key)
		_render_player_instructions()


func _cycle_role(phase: String) -> void:
	var key = UI.selected_key(_slots)
	if key == null:
		return
	_slot = int(key)
	var slot: Dictionary = _tactic["slots"][_slot]
	var choices := []
	for r in _roles.get(_positions[_slot] + "|" + phase, []):
		choices.append(r["id"])
	if choices.is_empty():
		return
	# the core applies the change, including the instructions the new roles lock (one rule
	# for every client, Constitution III)
	var changed = await ask("tactic.set_role", {"tactic": _tactic, "slot": slot["slot"],
			"phase": phase, "role_id": _next(choices, slot[phase + "_role"])})
	if changed != null:
		_tactic = changed
		_render()


func _cycle_player_instruction() -> void:
	var id = UI.selected_key(_player_instructions)
	if id == null:
		return
	var slot: Dictionary = _tactic["slots"][_slot]
	if _locked(slot).has(id):
		main.message(UI.t("ui.tactics.locked_refused"))
		return
	var o := _option(_options["player"], id)
	var chosen := {}
	for pair in slot["instructions"]:
		chosen[pair[0]] = pair[1]
	var setting = _next(o["settings"], chosen.get(id, o["default"]))
	if setting == o["default"]:
		chosen.erase(id)
	else:
		chosen[id] = setting
	var pairs := []
	var keys := chosen.keys()
	keys.sort()
	for k in keys:
		pairs.append([k, chosen[k]])
	slot["instructions"] = pairs
	_render_player_instructions()


func _cycle_taker() -> void:
	var taker = UI.selected_key(_takers)
	if taker == null:
		return
	var order := [null]
	var slots := _players.keys()
	slots.sort()
	for s in slots:
		order.append(_players[s])
	for pair in _tactic["set_pieces"]["takers"]:
		if pair[0] == taker:
			pair[1] = _next(order, pair[1])
	_render()


func _reset() -> void:
	var fresh = await ask("tactic.default", {"formation": _tactic["ip_formation"]})
	if fresh != null:
		_tactic = fresh
		main.message("")
		_render()


func _confirm() -> void:
	var issues = await ask("tactic.validate", {"tactic": _tactic})
	if issues == null:
		return
	if not issues.is_empty():
		main.message(UI.t("ui.tactics.errors",
				{"problems": ", ".join(issues.map(func(i): return i["code"] + " " + i["path"]))}))
		return
	var method := "match.tactic" if live else "tactic.confirm"
	if await ask(method, {"tactic": _tactic}) != null:
		main.go_back()  # not awaited: frees this screen
		main.message(UI.t("ui.tactics.confirmed"))

extends "res://scenes/screen.gd"
## Team selection (spec 007 US2): the assistant's XI and bench, swaps, formation, assistant,
## tactics, confirm. Every rule is the core's: swaps and confirmation are checked by it. Beside the
## lists, the assistant's briefing (spec 010): the opposition report and its suggestions, each
## with "Aplicar" when it has an action, sent through the same methods as a change by hand.

var _selection: Dictionary = {}
var _positions: Array = []
var _rows: Dictionary = {}  # player id -> squad row
var _xi: Tree
var _others: Tree
var _formation: OptionButton
var _formations: Array = []
var _heading: Label
var _warned := false
var _advice: VBoxContainer
var _advice_token := 0


func open() -> void:
	clear()
	var current = await ask("selection.current")
	if current == null:
		return
	_selection = current["selection"]
	_positions = current["positions"]
	for r in current["squad"]:
		_rows[r["player_id"]] = r
	_heading = UI.title("")
	add_child(_heading)
	_formation = OptionButton.new()
	var formations = await ask("formations.list")
	if formations == null:
		return
	for f in formations:
		_formation.add_item(f["name"])
		_formations.append(f["name"])
	_formation.item_selected.connect(_change_formation)
	add_child(UI.row([UI.label(UI.t("ui.desktop.formation")), _formation,
			UI.button(UI.t("ui.desktop.assistant"), _assistant),
			UI.button(UI.t("ui.menu.tactics"), func(): main.show_screen("tactics")),
			UI.spacer(), UI.button(UI.t("ui.desktop.confirm_and_play"), _confirm)]))
	var titles := [UI.t("ui.select.slot"), UI.t("ui.select.player"), UI.t("ui.select.pos"),
			UI.t("ui.select.stars"), UI.t("ui.select.status")]
	_xi = UI.table(titles)
	_others = UI.table(titles)
	_others.item_activated.connect(_swap)
	_xi.item_activated.connect(_swap)
	var lists := UI.row([UI.column([UI.label(UI.t("ui.select.xi"), 16, true), _xi]),
			UI.column([UI.label(UI.t("ui.select.others"), 16, true), _others])])
	for child in lists.get_children():
		child.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_advice = UI.column()
	_advice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(_advice)
	var panel := UI.column([UI.label(UI.t("ui.assistant.title"), 16, true), scroll])
	panel.custom_minimum_size.x = 360
	lists.add_child(panel)
	lists.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(lists)
	add_child(UI.row([UI.button(UI.t("ui.desktop.swap"), _swap),
			UI.label(UI.t("ui.desktop.selection_help"), 13)]))
	_render()


func _row_cells(slot_label: String, pid: String) -> Array:
	var r: Dictionary = _rows.get(pid, {})
	var state: String = UI.t("ui.select.suspended") if r.get("suspended", 0) > 0 else ""
	return [slot_label, r.get("name", pid), r.get("position", ""), UI.stars(r.get("stars", 0.0)),
			state]


func _render() -> void:
	_heading.text = UI.t("ui.select.title", {"club": main.status.get("club_name", ""),
			"formation": _selection["formation"]})
	var index := _formations.find(_selection["formation"])
	if index >= 0:
		_formation.select(index)
	var xi_slot = UI.selected_key(_xi)
	var other_pid = UI.selected_key(_others)
	var rows := []
	var keys := []
	var starters: Array = _selection["starters"].duplicate()
	starters.sort_custom(func(a, b): return a[0] < b[0])
	for pair in starters:
		rows.append(_row_cells(_positions[int(pair[0])], pair[1]))
		keys.append(int(pair[0]))
	UI.fill(_xi, rows, keys)
	var in_xi := starters.map(func(pair): return pair[1])
	rows = []
	keys = []
	for pid in _selection["bench"]:
		rows.append(_row_cells(UI.t("ui.select.bench"), pid))
		keys.append(pid)
	for pid in _rows:
		if pid not in in_xi and pid not in _selection["bench"]:
			rows.append(_row_cells("", pid))
			keys.append(pid)
	UI.fill(_others, rows, keys)
	if xi_slot != null:
		UI.select_key(_xi, xi_slot)
	if other_pid != null:
		UI.select_key(_others, other_pid)
	_refresh_advice()  # not awaited: the lists are drawn first


func _swap() -> void:
	var slot = UI.selected_key(_xi)
	var incoming = UI.selected_key(_others)
	if slot == null or incoming == null:
		main.message(UI.t("ui.desktop.pick_two"))
		return
	var swapped = await ask("selection.swap", {"selection": _selection, "slot": slot,
			"player_id": incoming})
	if swapped == null:
		return
	var issues = await ask("selection.validate", {"selection": swapped})
	if issues == null:
		return
	for issue in issues:
		if issue["code"] == "suspended" and issue["player_id"] == incoming:
			main.message(UI.t("ui.select.refused_suspended",
					{"player": _rows.get(incoming, {}).get("name", incoming)}))
			return
	_selection = swapped
	_warned = false
	main.message("")
	_render()


func _change_formation(index: int) -> void:
	if _formations[index] == _selection["formation"]:
		return
	await _propose(_formations[index])


func _assistant() -> void:
	await _propose(_selection["formation"])


func _propose(formation: String) -> void:
	var proposed = await ask("selection.propose", {"formation": formation})
	if proposed == null:
		return
	_selection = proposed
	var listing = await ask("formations.list")
	if listing != null:
		for f in listing:
			if f["name"] == formation:
				_positions = f["positions"]
	_warned = false
	_render()


func _confirm() -> void:
	var issues = await ask("selection.validate", {"selection": _selection})
	if issues == null:
		return
	var errors: Array = issues.filter(func(i): return i["severity"] == "error")
	if not errors.is_empty():
		main.message(UI.t("ui.select.errors",
				{"problems": ", ".join(errors.map(func(i): return i["code"]))}))
		return
	if not issues.is_empty() and not _warned:
		_warned = true
		main.message(UI.t("ui.desktop.no_goalkeeper"))
		return
	var confirmed = await ask("selection.confirm", {"selection": _selection})
	if confirmed == null:
		return
	if not confirmed["tactic_changes"].is_empty():
		main.message(UI.t("ui.tactics.refitted",
				{"positions": ", ".join(confirmed["tactic_changes"])}))
	main.play_match_day()  # navigation frees this screen: not awaited


# ---- the assistant's briefing (spec 010) -------------------------------------------------------


func _refresh_advice() -> void:
	_advice_token += 1
	var mine := _advice_token
	var briefing = await ask("assistant.briefing", {"selection": _selection})
	if briefing == null or mine != _advice_token or _advice == null:
		return
	for child in _advice.get_children():
		_advice.remove_child(child)
		child.queue_free()
	if briefing["report"] != null:
		_advice.add_child(UI.label(UI.t("ui.assistant.report"), 14, true))
		_advice.add_child(UI.label(briefing["report"]["text"], 13))
	var shown := 0
	for group in [["selection", "ui.assistant.selection"], ["tactic", "ui.assistant.tactic"],
			["squad", "ui.assistant.squad"]]:
		var items: Array = briefing[group[0]]
		if items.is_empty():
			continue
		_advice.add_child(UI.label(UI.t(group[1]), 14, true))
		for advice in items:
			shown += 1
			var text: String = ("⚠ " if advice["severity"] == "warning" else "") + advice["text"]
			var line := UI.label(text, 13)
			line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			var row := UI.row([line])
			if advice["action"] != null:
				row.add_child(UI.button(UI.t("ui.assistant.apply"), _apply.bind(advice["action"])))
			_advice.add_child(row)
	if shown == 0:
		_advice.add_child(UI.label(UI.t("ui.assistant.nothing"), 13))


## A suggestion applied exactly as by hand: a swap changes the selection on screen (confirmed with
## the rest); a role or a tactic is confirmed through the tactic methods.
func _apply(action: Dictionary) -> void:
	match action["type"]:
		"swap":
			var swapped = await ask("selection.swap", {"selection": _selection,
					"slot": action["slot"], "player_id": action["player_id"]})
			if swapped == null:
				return
			_selection = swapped
			_warned = false
			main.message(UI.t("ui.assistant.applied"))
			_render()
		"role", "tactic":
			var tactic = action.get("tactic")
			if action["type"] == "role":
				var current = await ask("tactic.current")
				if current == null:
					return
				tactic = await ask("tactic.set_role", {"tactic": current, "slot": action["slot"],
						"phase": action["phase"], "role_id": action["role_id"]})
			if tactic == null or await ask("tactic.confirm", {"tactic": tactic}) == null:
				return
			main.message(UI.t("ui.assistant.applied"))
			_refresh_advice()

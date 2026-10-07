extends "res://scenes/screen.gd"
## Team selection (spec 007 US2): the assistant's XI and bench, swaps, formation, assistant,
## tactics, confirm. Every rule is the core's: swaps and confirmation are checked by it.

var _selection: Dictionary = {}
var _positions: Array = []
var _rows: Dictionary = {}  # player id -> squad row
var _xi: Tree
var _others: Tree
var _formation: OptionButton
var _formations: Array = []
var _heading: Label
var _warned := false


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
	lists.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(lists)
	add_child(UI.row([UI.button(UI.t("ui.desktop.swap"), _swap),
			UI.paragraph(UI.t("ui.desktop.selection_help"), 13)]))
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

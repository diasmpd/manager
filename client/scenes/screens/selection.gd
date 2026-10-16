extends "res://scenes/screen.gd"
## Team selection (spec 007 US2): the assistant's XI and bench, swaps, formation, assistant,
## tactics. Every rule is the core's. Each valid change is kept at once (FM's way, owner report
## 2026-10-16); the top bar's Ir para o jogo starts the match (main.go_to_match).

var _selection: Dictionary = {}
var _positions: Array = []
var _rows: Dictionary = {}  # player id -> squad row
var _xi: Tree
var _others: Tree
var _formation: OptionButton
var _formations: Array = []
var _heading: Label


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
			UI.button(UI.t("ui.menu.tactics"), func(): main.show_screen("tactics"))]))
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
	main.message("")
	_render()
	await _keep()


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
	_render()
	await _keep()


## Keep the selection on the career (warnings such as no goalkeeper are told on Ir para o jogo).
func _keep() -> void:
	var issues = await ask("selection.validate", {"selection": _selection})
	if issues == null or issues.any(func(i): return i["severity"] == "error"):
		return
	main.warned_no_keeper = false
	var kept = await ask("selection.confirm", {"selection": _selection})
	if kept != null and not kept["tactic_changes"].is_empty():
		main.message(UI.t("ui.tactics.refitted",
				{"positions": ", ".join(kept["tactic_changes"])}))

extends "res://scenes/screen.gd"
## Tables (overall classification or a group) and the club's fixtures (spec 007 US3).

var _choice: OptionButton
var _groups: Array = []
var _table: Tree


func open() -> void:
	clear()
	add_child(UI.title(UI.t("ui.menu.tables")))
	_choice = OptionButton.new()
	_choice.add_item(UI.t("ui.tables.overall"))
	var groups = await ask("view.groups")
	if groups == null:
		return
	for g in groups:
		_choice.add_item(UI.t("ui.desktop.group", {"label": g["label"]}))
		_groups.append(g["label"])
	_choice.item_selected.connect(func(_i): _load_table())
	add_child(UI.row([_choice]))
	var titles := []
	for k in ["pos", "club", "p", "w", "d", "l", "gf", "ga", "gd", "pts"]:
		titles.append(UI.t("table." + k))
	_table = UI.table(titles)
	_table.custom_minimum_size.y = 330
	add_child(_table)
	await _load_table()
	add_child(UI.label(UI.t("ui.tables.fixtures", {"club": main.status.get("club_name", "")}), 18,
			true))
	var fixtures = await ask("view.fixtures", {"club_id": main.status.get("club_id", "")})
	if fixtures == null:
		return
	var list := ItemList.new()
	list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	for m in fixtures:
		list.add_item(UI.match_text(m))
	add_child(list)


func _load_table() -> void:
	var params := {}
	if _choice.selected > 0:
		params["group"] = _groups[_choice.selected - 1]
	var rows_data = await ask("view.table", params)
	if rows_data == null:
		return
	var rows := []
	var keys := []
	for r in rows_data:
		rows.append([UI.num(r["place"]), r["club_name"], UI.num(r["played"]), UI.num(r["won"]),
				UI.num(r["drawn"]), UI.num(r["lost"]), UI.num(r["goals_for"]), UI.num(r["goals_against"]),
				UI.num(r["goal_difference"]), UI.num(r["points"])])
		keys.append(r["club_id"])
	UI.fill(_table, rows, keys)
	UI.select_key(_table, main.status.get("club_id", ""))

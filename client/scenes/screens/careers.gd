extends "res://scenes/screen.gd"
## Saved careers (open one) and a new career (name + club) — spec 007 US4.

var _saves: Tree
var _name: LineEdit
var _clubs: OptionButton
var _club_ids: Array = []


func open() -> void:
	clear()
	add_child(UI.title(UI.t("ui.careers.title")))
	var saves = await ask("career.list")
	if saves == null:
		return
	var clubs = await ask("career.clubs")  # names for the list, and the new-career choice
	if clubs == null:
		return
	var club_names := {}
	for club in clubs:
		club_names[club["id"]] = club["name"]
	if saves.is_empty():
		add_child(UI.label(UI.t("ui.careers.none"), 16))
	else:
		var rows := []
		var keys := []
		for s in saves:
			if s["name"] == "autosave":
				continue
			rows.append([s["name"], club_names.get(s["user_club_id"], s["user_club_id"]),
					UI.date_text(s["current_date"]),
					UI.num(s["year"]), str(s["saved_at"]).left(16).replace("T", " ")])
			keys.append(s["name"])
		_saves = UI.table([UI.t("ui.careers.name"), UI.t("ui.careers.club"),
				UI.t("ui.careers.date"), UI.t("ui.careers.season"), UI.t("ui.careers.saved_at")],
				rows, keys)
		_saves.custom_minimum_size.y = 220
		_saves.size_flags_vertical = Control.SIZE_FILL  # leave room for the new-career form
		_saves.item_activated.connect(_open_selected)
		add_child(_saves)
		add_child(UI.row([UI.button(UI.t("ui.careers.open"), _open_selected)]))
		if not keys.is_empty():
			_saves.get_root().get_first_child().select(0)
	add_child(HSeparator.new())
	add_child(UI.label(UI.t("ui.careers.new"), 18, true))
	_name = LineEdit.new()
	_name.placeholder_text = UI.t("ui.careers.name_hint")
	_name.custom_minimum_size.x = 260
	_clubs = OptionButton.new()
	for club in clubs:
		_clubs.add_item("%s  %s" % [club["name"], UI.stars(club["reputation"] / 4.0)])
		_club_ids.append(club["id"])
	add_child(UI.row([UI.label(UI.t("ui.careers.name")), _name, UI.label(UI.t("ui.careers.club")),
			_clubs, UI.button(UI.t("ui.careers.create"), _create)]))


func _open_selected() -> void:
	var name = UI.selected_key(_saves) if _saves != null else null
	if name == null:
		return
	var opened = await ask("career.open", {"name": name})
	if opened == null:
		return
	# navigation frees this screen: start it last, without awaiting, and let main follow up
	main.open_career(opened["status"], opened["notices"])


func _create() -> void:
	var name := _name.text.strip_edges()
	if name.is_empty() or _clubs.selected < 0:
		return
	var created = await ask("career.new", {"name": name, "club_id": _club_ids[_clubs.selected]})
	if created == null:
		return
	main.open_career(created, [])

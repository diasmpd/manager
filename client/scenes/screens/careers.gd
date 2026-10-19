extends "res://scenes/screen.gd"
## Saved careers (open one) and a new career (name + club) — spec 007 US4. The new career's world
## (the sample, or a real dataset) is chosen first when there is more than one (spec 013, FM's
## database choice).

var _saves: Tree
var _name: LineEdit
var _clubs: OptionButton
var _club_ids: Array = []
var _worlds: OptionButton
var _world_ids: Array = []


func open() -> void:
	clear()
	add_child(UI.title(UI.t("ui.careers.title")))
	var saves = await ask("career.list")
	if saves == null:
		return
	if saves.is_empty():
		add_child(UI.label(UI.t("ui.careers.none"), 16))
	else:
		var rows := []
		var keys := []
		for s in saves:
			if s["name"] == "autosave":
				continue
			rows.append([s["name"], s["user_club_id"], UI.date_text(s["current_date"]),
					str(s["year"]), str(s["saved_at"]).left(16).replace("T", " ")])
			keys.append(s["name"])
		_saves = UI.table([UI.t("ui.careers.name"), UI.t("ui.careers.club"),
				UI.t("ui.careers.date"), UI.t("ui.careers.season"), UI.t("ui.careers.saved_at")],
				rows, keys)
		_saves.custom_minimum_size.y = 220
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
	var worlds = await ask("worlds.list")
	if worlds == null:
		return
	_worlds = OptionButton.new()
	for world in worlds:
		_worlds.add_item(UI.t("ui.careers.world_item", {"label": world["label"],
				"clubs": str(int(world["clubs"])), "players": str(int(world["players"]))}))
		_world_ids.append(world["id"])
	_worlds.item_selected.connect(func(_index): _load_clubs())
	if worlds.size() > 1:
		add_child(UI.row([UI.label(UI.t("ui.careers.world")), _worlds]))
	if not await _load_clubs():
		return
	add_child(UI.row([UI.label(UI.t("ui.careers.name")), _name, UI.label(UI.t("ui.careers.club")),
			_clubs, UI.button(UI.t("ui.careers.create"), _create)]))


## The chosen world's clubs; false when the core refused.
func _load_clubs() -> bool:
	var clubs = await ask("career.clubs", {"world": _world()})
	if clubs == null:
		return false
	_clubs.clear()
	_club_ids.clear()
	for club in clubs:
		_clubs.add_item("%s  %s" % [club["name"], UI.stars(club["reputation"] / 4.0)])
		_club_ids.append(club["id"])
	return true


func _world() -> String:
	return _world_ids[_worlds.selected] if _worlds.selected >= 0 else "sample"


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
	var created = await ask("career.new", {"name": name, "club_id": _club_ids[_clubs.selected],
			"world": _world()})
	if created == null:
		return
	main.open_career(created, [])

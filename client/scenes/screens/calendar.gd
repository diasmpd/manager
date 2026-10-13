extends "res://scenes/screen.gd"
## The calendar, one month at a time: the club's matches, other match days and reserved windows
## (spec 007 US3).

var month := 0
var _list: ItemList
var _heading: Label
var _replay_button: Button


func open() -> void:
	clear()
	if month == 0:
		month = int(str(main.status.get("current_date", "2027-01-01")).substr(5, 2))
	_heading = UI.title("")
	add_child(UI.row([UI.button("◀", _move.bind(-1)), _heading, UI.button("▶", _move.bind(1))]))
	_list = ItemList.new()
	_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.item_selected.connect(func(_index): _refresh_replay())
	_list.item_activated.connect(func(_index): _watch())
	add_child(_list)
	# a played match of the club that has a positional record can be watched again (spec 008b)
	_replay_button = UI.button(UI.t("ui.replay.watch"), _watch)
	_replay_button.disabled = true
	add_child(UI.row([_replay_button]))
	await _load()


func _move(step: int) -> void:
	month = (month - 1 + step + 12) % 12 + 1
	await _load()


func _load() -> void:
	_heading.text = UI.t("ui.calendar.title", {"month": UI.t("month.%d" % month).capitalize(),
			"year": main.status.get("year", "")})
	var days = await ask("view.calendar", {"month": month})
	if days == null:
		return
	_list.clear()
	for d in days:
		var text := UI.date_text(d["day"])
		var mine = d["user_match"]
		if mine != null:
			text += "   ●  %s x %s" % [mine["home_name"], mine["away_name"]]
		elif d["match_count"] > 0:
			text += "   " + UI.t("ui.desktop.matches_that_day", {"n": d["match_count"]})
		if not d["windows"].is_empty():
			text += "   [%s]" % ", ".join(d["windows"])
		var index := _list.add_item(text)
		if mine != null:
			_list.set_item_custom_fg_color(index, Color(1, 0.86, 0.45))
			if d.get("user_match_replay", false):
				_list.set_item_metadata(index, mine["id"])
				_list.set_item_text(index, text + "   ▶")
	_refresh_replay()


func _selected_match() -> String:
	var picked := _list.get_selected_items()
	if picked.is_empty():
		return ""
	var match_id = _list.get_item_metadata(picked[0])
	return match_id if match_id is String else ""


func _refresh_replay() -> void:
	_replay_button.disabled = _selected_match() == ""


func _watch() -> void:
	var match_id := _selected_match()
	if match_id != "":
		main.show_screen("replay", {"match_id": match_id})  # not awaited: frees this screen

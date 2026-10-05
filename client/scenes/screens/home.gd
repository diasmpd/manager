extends "res://scenes/screen.gd"
## Home: the club, the date, the table position, the next match, the last match and the latest
## news (spec 007 US1).


func open() -> void:
	clear()
	var home = await ask("view.home")
	if home == null:
		return
	var status: Dictionary = home["status"]
	main.update_status(status)
	add_child(UI.title(status["club_name"]))
	add_child(UI.label(UI.t("ui.home.date", {"date": UI.date_text(status["current_date"]),
			"year": status["year"]}), 16))
	if status["position"] != null:
		add_child(UI.label(UI.t("ui.home.position", {"place": status["position"]}), 16))
	add_child(HSeparator.new())
	add_child(UI.label(UI.t("ui.home.next_match"), 18, true))
	add_child(UI.label(UI.match_text(status["next_match"]) if status["next_match"] != null
			else UI.t("ui.home.no_match"), 16))
	if home["last_match"] != null:
		add_child(UI.label(UI.t("ui.home.last_match"), 18, true))
		add_child(UI.label(UI.match_text(home["last_match"]), 16))
	if not status["suspended"].is_empty():
		add_child(UI.label(UI.t("ui.home.suspended"), 18, true))
		for s in status["suspended"]:
			add_child(UI.label("%s (%d)" % [s.get("player_name", s.get("player_id", "")),
					s.get("matches", 0)]))
	add_child(HSeparator.new())
	add_child(UI.label(UI.t("ui.home.latest_news"), 18, true))
	for item in home["news"]:
		add_child(UI.label("%s  %s" % [UI.date_text(item["day"]), item["text"]]))

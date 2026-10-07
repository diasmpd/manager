extends "res://scenes/screen.gd"
## The squad: position, age, level (stars relative to the squad; CA is never shown), status,
## appearances, goals, assists and cards. Double-click opens the profile (spec 007 US3).


func open() -> void:
	clear()
	add_child(UI.title(UI.t("ui.squad.title", {"club": main.status.get("club_name", "")})))
	var rows_data = await ask("view.squad")
	if rows_data == null:
		return
	var rows := []
	var keys := []
	for r in rows_data:
		var state := ""
		if r["suspended"] > 0:
			state = UI.t("ui.select.suspended")
		elif r["yellows"] > 0:
			state = UI.t("ui.squad.yellows_count", {"n": r["yellows"]})
		rows.append([r["position"], r["name"], UI.num(r["age"]), UI.stars(r["stars"]), state,
				UI.num(r["appearances"]), UI.num(r["goals"]), UI.num(r["assists"]),
				"%d/%d" % [r["yellow_cards"], r["red_cards"]]])
		keys.append(r["player_id"])
	var table := UI.table([UI.t("ui.select.pos"), UI.t("ui.select.player"), UI.t("ui.squad.age"),
			UI.t("ui.select.stars"), UI.t("ui.select.status"), UI.t("ui.squad.apps"),
			UI.t("ui.squad.goals"), UI.t("ui.squad.assists"), UI.t("ui.squad.cards")], rows, keys)
	table.item_activated.connect(func(): _profile(UI.selected_key(table)))
	add_child(table)
	add_child(UI.paragraph(UI.t("ui.desktop.open_profile"), 13))


func _profile(player_id) -> void:
	if player_id != null:
		main.show_screen("player", {"player_id": player_id})  # not awaited: frees this screen

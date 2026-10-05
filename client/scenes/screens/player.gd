extends "res://scenes/screen.gd"
## A player's profile: name, age, positions with familiarity, and attributes by group (spec 007
## US3). Hidden attributes and ability are never shown (FM style).

var player_id := ""


func open() -> void:
	clear()
	var p = await ask("view.player", {"player_id": player_id})
	if p == null:
		return
	add_child(UI.title("%s (%s)" % [p["full_name"], p["display_name"]]))
	var info := "%d · %s" % [p["age"], p["best_position"]]
	if p["club_name"] != null:
		info += " · " + p["club_name"]
	if p["shirt_number"] != null:
		info += " · #%d" % p["shirt_number"]
	add_child(UI.label(info, 16))
	var positions := []
	for entry in p["positions"]:
		positions.append("%s (%s)" % [entry["position"], UI.t("band." + entry["band"])])
	add_child(UI.label(", ".join(positions)))
	var groups := UI.row()
	for group in p["attributes"]:
		var column := UI.column([UI.label(UI.t("group." + group["group"]), 18, true)])
		var grid := GridContainer.new()
		grid.columns = 2
		grid.add_theme_constant_override("h_separation", 16)
		for pair in group["values"]:
			grid.add_child(UI.label(UI.t("attr." + pair[0])))
			var value := UI.label(str(int(pair[1])), 0, int(pair[1]) >= 15)
			grid.add_child(value)
		column.add_child(grid)
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		groups.add_child(column)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	groups.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(groups)
	add_child(scroll)
	add_child(UI.button(UI.t("ui.desktop.back"), main.go_back))

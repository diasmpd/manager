extends "res://scenes/screen.gd"
## The news, most recent first (spec 007 US3).


func open() -> void:
	clear()
	add_child(UI.title(UI.t("ui.news.title")))
	var items = await ask("view.news")
	if items == null:
		return
	var list := ItemList.new()
	list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	for item in items:  # newest first, as the core returns them
		list.add_item("%s   %s" % [UI.date_text(item["day"]), item["text"]])
	add_child(list)

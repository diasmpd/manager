extends RefCounted
## Small helpers shared by the screens: widgets, and formatting of the core's data.
## Only presentation lives here; every value comes from the core (Constitution III).

const GAP := 8


static func t(key: String, params: Dictionary = {}) -> String:
	var core = Engine.get_main_loop().root.get_node("/root/Core")
	return core.t(key, params)


static func label(text: String, size: int = 0, bold := false) -> Label:
	var l := Label.new()
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	if size > 0:
		l.add_theme_font_size_override("font_size", size)
	if bold:
		l.add_theme_color_override("font_color", Color(1, 0.86, 0.45))
	return l


static func title(text: String) -> Label:
	return label(text, 22, true)


static func button(text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(action)
	return b


static func row(children: Array = []) -> HBoxContainer:
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", GAP)
	for child in children:
		box.add_child(child)
	return box


static func column(children: Array = []) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", GAP)
	for child in children:
		box.add_child(child)
	return box


static func spacer() -> Control:
	var c := Control.new()
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return c


## A table: a Tree with titled columns and no root. `rows` are arrays of cell texts; `keys`
## (optional) are stored as each row's metadata.
static func table(titles: Array, rows: Array = [], keys: Array = []) -> Tree:
	var tree := Tree.new()
	tree.columns = titles.size()
	tree.column_titles_visible = true
	tree.hide_root = true
	tree.select_mode = Tree.SELECT_ROW
	tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tree.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for i in titles.size():
		tree.set_column_title(i, titles[i])
		tree.set_column_expand(i, i == 1 or titles.size() <= 2)
	fill(tree, rows, keys)
	return tree


static func fill(tree: Tree, rows: Array, keys: Array = []) -> void:
	tree.clear()
	var root := tree.create_item()
	for i in rows.size():
		var item := tree.create_item(root)
		for c in rows[i].size():
			item.set_text(c, str(rows[i][c]))
		if i < keys.size():
			item.set_metadata(0, keys[i])


static func selected_key(tree: Tree) -> Variant:
	var item := tree.get_selected()
	return item.get_metadata(0) if item != null else null


static func select_key(tree: Tree, key: Variant) -> void:
	var item := tree.get_root().get_first_child() if tree.get_root() else null
	while item != null:
		if item.get_metadata(0) == key:
			item.select(0)
			tree.scroll_to_item(item)
			return
		item = item.get_next()


static func stars(value: float) -> String:
	return "★".repeat(int(value)) + ("½" if fmod(value, 1.0) > 0.0 else "")


## "sáb 17/01/2027" from an ISO date (or datetime).
static func date_text(iso: String) -> String:
	var d := Time.get_datetime_dict_from_datetime_string(iso.left(10), false)
	var unix := Time.get_unix_time_from_datetime_dict(d)
	var weekday: int = (Time.get_datetime_dict_from_unix_time(unix)["weekday"] + 6) % 7  # Mon = 0
	return "%s %02d/%02d/%04d" % [t("weekday.%d" % weekday), d["day"], d["month"], d["year"]]


static func time_text(iso: String) -> String:
	return iso.substr(11, 5) if iso.length() >= 16 else ""


## "sáb 17/01/2027 16:00  Alvorada 2 x 1 Serra Negra" from a MatchView.
static func match_text(m: Dictionary) -> String:
	var result = m.get("result")
	var score := "x" if result == null else "%d x %d" % [result["home_goals"], result["away_goals"]]
	return "%s %s  %s %s %s" % [date_text(m["kickoff"]), time_text(m["kickoff"]), m["home_name"],
			score, m["away_name"]]


static func error_text(answer: Dictionary) -> String:
	return str(answer.get("error", {}).get("message", ""))

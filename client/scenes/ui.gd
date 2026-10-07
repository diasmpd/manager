extends RefCounted
## Small helpers shared by the screens: widgets, and formatting of the core's data.
## Only presentation lives here; every value comes from the core (Constitution III).

const GAP := 8


static func t(key: String, params: Dictionary = {}) -> String:
	var core = Engine.get_main_loop().root.get_node("/root/Core")
	return core.t(key, params)


## A one-line label. It does not wrap: a wrapping label in a row asks for no width and the row
## squeezes it to one letter a line. Long text goes in `paragraph`.
static func label(text: String, size: int = 0, bold := false) -> Label:
	var l := Label.new()
	l.text = text
	if size > 0:
		l.add_theme_font_size_override("font_size", size)
	if bold:
		l.add_theme_color_override("font_color", Color(1, 0.86, 0.45))
	return l


## Text that wraps: it takes the width it is given (news, help, messages).
static func paragraph(text: String, size: int = 0) -> Label:
	var l := label(text, size)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return l


## A number as the core meant it: JSON gives every number as a float, so 2027 arrives as 2027.0.
static func num(value: Variant) -> String:
	if value is float and is_finite(value) and value == floorf(value):
		return str(int(value))
	return str(value)


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
			item.set_text(c, num(rows[i][c]))
		if i < keys.size():
			item.set_metadata(0, keys[i])
	_fit_columns(tree, rows)


## Columns that do not expand get the width of their longest text (title or cell): otherwise
## Godot cuts the cells ("0." for a number, "qui 31/" for a date).
static func _fit_columns(tree: Tree, rows: Array) -> void:
	var font := tree.get_theme_font("font")
	var size := tree.get_theme_font_size("font_size")
	for c in tree.columns:
		if tree.is_column_expanding(c):
			continue
		var widest := font.get_string_size(tree.get_column_title(c), HORIZONTAL_ALIGNMENT_LEFT,
				-1, size).x
		for row in rows:
			if c < row.size():
				widest = maxf(widest, font.get_string_size(num(row[c]), HORIZONTAL_ALIGNMENT_LEFT,
						-1, size).x)
		tree.set_column_custom_minimum_width(c, int(widest) + 24)


## The window's look: buttons that read as buttons (spec 007 polish).
static func make_theme() -> Theme:
	var theme := Theme.new()
	var states := {
		"normal": [Color(0.17, 0.2, 0.25), Color(0.3, 0.35, 0.42)],
		"hover": [Color(0.22, 0.26, 0.32), Color(0.45, 0.5, 0.58)],
		"pressed": [Color(0.35, 0.29, 0.12), Color(1, 0.86, 0.45)],
		"disabled": [Color(0.13, 0.14, 0.16), Color(0.2, 0.22, 0.25)],
		"focus": [Color(0, 0, 0, 0), Color(1, 0.86, 0.45)],
	}
	for state in states:
		var box := StyleBoxFlat.new()
		box.bg_color = states[state][0]
		box.border_color = states[state][1]
		box.set_border_width_all(1)
		box.set_corner_radius_all(6)
		box.content_margin_left = 12
		box.content_margin_right = 12
		box.content_margin_top = 6
		box.content_margin_bottom = 6
		for type in ["Button", "OptionButton"]:
			theme.set_stylebox(state, type, box)
	theme.set_color("font_disabled_color", "Button", Color(0.45, 0.47, 0.5))
	return theme


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

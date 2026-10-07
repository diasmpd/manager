extends RefCounted
## Small helpers shared by the screens: widgets, and formatting of the core's data.
## Only presentation lives here; every value comes from the core (Constitution III).

const GAP := 8

# ---- the look: direction C, "Placar eletronico" (owner's choice, 2026-10-07) ----------------------
# Dark and modern, amber LED scoreboard digits, the user's club colours on the accents.
const BG := Color("0d1512")
const PANEL := Color("13201b")
const PANEL_DARK := Color("0f1a16")
const TOPBAR := Color("070b09")
const LINE := Color("24362e")
const INK := Color("e3efe8")
const MUTE := Color("8fa79b")
const LED := Color("ffb53a")
const FONT_DIR := "res://assets/fonts/"
## Fonts are SIL OFL (licences beside them). Loaded from the .ttf directly, so a checkout runs
## without Godot's import step (a packaged build must include *.ttf).
const REGULAR := "Barlow-Regular"
const SEMIBOLD := "Barlow-SemiBold"
const CONDENSED := "BarlowCondensed-SemiBold"
const CONDENSED_BOLD := "BarlowCondensed-Bold"
const DIGITS := "VT323-Regular"
const POSITION_GROUPS := {"gk": ["GK"], "def": ["DL", "DC", "DR", "WBL", "WBR"],
		"att": ["ST", "CF"]}

static var club_primary := Color("f2c230")  # until a career is open
static var club_secondary := Color("0e2a5c")
static var _fonts := {}


static func font(name: String) -> FontFile:
	if not _fonts.has(name):
		var f := FontFile.new()
		f.load_dynamic_font(FONT_DIR + name + ".ttf")
		_fonts[name] = f
	return _fonts[name]


## The user club's colours ("#RRGGBB" pair from the core's status).
static func set_club_colors(colors: Variant) -> void:
	if colors is Array and colors.size() == 2:
		club_primary = Color(str(colors[0]))
		club_secondary = Color(str(colors[1]))


## The club colour for thin accents (menu marker, focus, selection): the primary, unless it is
## hard to see on the dark background and the secondary shows better (royal blue and yellow
## gets yellow markers). Filled surfaces (the main button) keep the primary.
static func accent() -> Color:
	var primary := _contrast(club_primary, BG)
	if primary >= 3.0 or _contrast(club_secondary, BG) <= primary:
		return club_primary
	return club_secondary


static func _contrast(a: Color, b: Color) -> float:
	var la := a.get_luminance()
	var lb := b.get_luminance()
	return (maxf(la, lb) + 0.05) / (minf(la, lb) + 0.05)


## Readable text on a coloured surface.
static func on_color(c: Color) -> Color:
	return Color("10140f") if c.get_luminance() > 0.45 else Color.WHITE


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
		l.add_theme_font_override("font", font(CONDENSED))
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
	var l := label(text.to_upper(), 26)
	l.add_theme_font_override("font", font(CONDENSED_BOLD))
	return l


## Scoreboard digits: dates, the score, the clock.
static func led(text: String, size: int = 24) -> Label:
	var l := label(text, size)
	l.add_theme_font_override("font", font(DIGITS))
	l.add_theme_color_override("font_color", LED)
	l.add_theme_color_override("font_outline_color", Color(LED, 0.22))
	l.add_theme_constant_override("outline_size", 4)
	return l


static func button(text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(action)
	return b


## The screen's main action (Continuar, Confirmar): filled with the club colour.
static func primary_button(text: String, action: Callable) -> Button:
	var b := button(text.to_upper(), action)
	b.theme_type_variation = "Primary"
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
			_style_cell(item, c, rows[i][c])
		if i < keys.size():
			item.set_metadata(0, keys[i])
	_fit_columns(tree, rows)


## Positions as coloured chips, numbers in scoreboard digits.
static func _style_cell(item: TreeItem, c: int, value: Variant) -> void:
	var text := num(value)
	var group := position_group(text)
	if group != "":
		var colors: Array = {"gk": [Color("4a3a10"), Color("ffe08a")],
				"def": [Color("23402f"), Color("bfe8cf")], "mid": [Color("1f3550"), Color("b7d4ff")],
				"att": [Color("4a1f22"), Color("ffb3b8")]}[group]
		item.set_custom_bg_color(c, colors[0])
		item.set_custom_color(c, colors[1])
		item.set_custom_font(c, font(CONDENSED_BOLD))
		item.set_text_alignment(c, HORIZONTAL_ALIGNMENT_CENTER)
	elif _is_number(text):
		item.set_custom_font(c, font(DIGITS))
		item.set_custom_font_size(c, 21)
		item.set_custom_color(c, LED)


## "gk", "def", "mid" or "att" for a position code ("" for anything else).
static func position_group(text: String) -> String:
	for group in POSITION_GROUPS:
		if text in POSITION_GROUPS[group]:
			return group
	if text in ["DM", "MC", "ML", "MR", "AMC", "AML", "AMR", "AM"]:
		return "mid"
	return ""


static func _is_number(text: String) -> bool:
	return text.is_valid_int() or text.is_valid_float() or (text.contains("/") and text.replace("/", "").is_valid_int())


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
		var digits: Font = load_digits()
		for row in rows:
			if c < row.size():
				var text := num(row[c])
				var shown: Font = digits if _is_number(text) else font
				widest = maxf(widest, shown.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1,
						21 if _is_number(text) else size).x)
		tree.set_column_custom_minimum_width(c, int(widest) + 24)


static func load_digits() -> Font:
	return font(DIGITS)


static func _box(bg: Color, border: Color = Color(0, 0, 0, 0), width: int = 0,
		radius: int = 6, margin_x: int = 12, margin_y: int = 6) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = bg
	box.border_color = border
	box.set_border_width_all(width)
	box.set_corner_radius_all(radius)
	box.content_margin_left = margin_x
	box.content_margin_right = margin_x
	box.content_margin_top = margin_y
	box.content_margin_bottom = margin_y
	return box


## The window's look (direction C), in the user club's colours.
static func make_theme() -> Theme:
	var theme := Theme.new()
	var hi := accent()
	theme.default_font = font(REGULAR)
	theme.default_font_size = 15
	theme.set_color("font_color", "Label", INK)
	# buttons
	var buttons := {"normal": _box(PANEL, LINE, 1), "hover": _box(PANEL.lightened(0.08), MUTE, 1),
		"pressed": _box(hi.darkened(0.35), hi, 1), "disabled": _box(PANEL_DARK, LINE, 1),
		"focus": _box(Color(0, 0, 0, 0), hi, 2)}
	for type in ["Button", "OptionButton"]:
		for state in buttons:
			theme.set_stylebox(state, type, buttons[state])
		theme.set_font("font", type, font(CONDENSED))
		theme.set_font_size("font_size", type, 16)
		theme.set_color("font_color", type, INK)
		theme.set_color("font_hover_color", type, Color.WHITE)
		theme.set_color("font_pressed_color", type, Color.WHITE)
		theme.set_color("font_disabled_color", type, MUTE.darkened(0.3))
	# the main action (Continuar, Confirmar): filled with the club colour
	theme.set_type_variation("Primary", "Button")
	var fill := club_primary
	theme.set_stylebox("normal", "Primary", _box(fill, Color(0, 0, 0, 0), 0, 6, 18, 8))
	theme.set_stylebox("hover", "Primary", _box(fill.lightened(0.12), Color(0, 0, 0, 0), 0, 6, 18, 8))
	theme.set_stylebox("pressed", "Primary", _box(fill.darkened(0.15), Color(0, 0, 0, 0), 0, 6, 18, 8))
	theme.set_stylebox("focus", "Primary", _box(Color(0, 0, 0, 0), hi, 2))
	for key in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		theme.set_color(key, "Primary", on_color(fill))
	theme.set_font("font", "Primary", font(CONDENSED_BOLD))
	theme.set_font_size("font_size", "Primary", 17)
	# the menu: quiet entries, the current one marked in the club colour
	for variation in ["Nav", "NavCurrent"]:
		theme.set_type_variation(variation, "Button")
		var current: bool = variation == "NavCurrent"
		var base := _box(PANEL if current else Color(0, 0, 0, 0), hi if current else Color(0, 0, 0, 0),
				0, 4, 12, 8)
		base.border_width_left = 3
		for state in ["normal", "pressed", "focus"]:
			theme.set_stylebox(state, variation, base)
		var hover := base.duplicate() as StyleBoxFlat
		hover.bg_color = PANEL
		theme.set_stylebox("hover", variation, hover)
		theme.set_color("font_color", variation, INK if current else MUTE)
		theme.set_color("font_hover_color", variation, INK)
		theme.set_font_size("font_size", variation, 17)
	# fields and lists
	theme.set_stylebox("normal", "LineEdit", _box(PANEL_DARK, LINE, 1))
	theme.set_stylebox("focus", "LineEdit", _box(PANEL_DARK, hi, 1))
	theme.set_color("font_color", "LineEdit", INK)
	theme.set_color("font_placeholder_color", "LineEdit", MUTE)
	var selected := _box(Color(hi, 0.22), Color(0, 0, 0, 0), 0, 0, 4, 2)
	for type in ["Tree", "ItemList"]:
		theme.set_stylebox("panel", type, _box(PANEL, LINE, 1, 8, 2, 2))
		theme.set_stylebox("focus", type, StyleBoxEmpty.new())
		theme.set_stylebox("selected", type, selected)
		theme.set_stylebox("selected_focus", type, selected)
		theme.set_color("font_color", type, INK)
		theme.set_color("font_selected_color", type, Color.WHITE)
		theme.set_color("guide_color", type, LINE)
	theme.set_stylebox("cursor", "Tree", StyleBoxEmpty.new())
	theme.set_stylebox("cursor_unfocused", "Tree", StyleBoxEmpty.new())
	var header := _box(PANEL_DARK, Color(0, 0, 0, 0), 0, 0, 8, 6)
	for state in ["title_button_normal", "title_button_hover", "title_button_pressed"]:
		theme.set_stylebox(state, "Tree", header)
	theme.set_color("title_button_color", "Tree", MUTE)
	theme.set_font("title_button_font", "Tree", font(CONDENSED))
	theme.set_font_size("title_button_font_size", "Tree", 14)
	theme.set_constant("v_separation", "Tree", 6)
	theme.set_constant("h_separation", "Tree", 10)
	theme.set_color("default_color", "RichTextLabel", INK)
	theme.set_stylebox("panel", "PopupMenu", _box(PANEL, LINE, 1, 6, 6, 6))
	theme.set_stylebox("hover", "PopupMenu", _box(Color(hi, 0.25), Color(0, 0, 0, 0), 0, 4, 6, 4))
	theme.set_color("font_color", "PopupMenu", INK)
	theme.set_color("font_hover_color", "PopupMenu", Color.WHITE)
	var rule := StyleBoxLine.new()
	rule.color = LINE
	rule.thickness = 1
	theme.set_stylebox("separator", "HSeparator", rule)
	theme.set_stylebox("panel", "PanelContainer", _box(PANEL, LINE, 1, 8, 12, 10))
	for bar in ["VScrollBar", "HScrollBar"]:
		theme.set_stylebox("scroll", bar, _box(PANEL_DARK, Color(0, 0, 0, 0), 0, 4, 2, 2))
		theme.set_stylebox("grabber", bar, _box(LINE, Color(0, 0, 0, 0), 0, 4, 2, 2))
		theme.set_stylebox("grabber_highlight", bar, _box(MUTE, Color(0, 0, 0, 0), 0, 4, 2, 2))
		theme.set_stylebox("grabber_pressed", bar, _box(hi, Color(0, 0, 0, 0), 0, 4, 2, 2))
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

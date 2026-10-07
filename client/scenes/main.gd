extends Control
## The game window (spec 007): top bar (date, club, Continuar), left menu and the content area.
## The Continue flow follows the terminal UI: a user match day opens team selection; after
## confirming, the match day is played and shown as a live feed; events go to the news; the
## season end shows the outcome.

const UI := preload("res://scenes/ui.gd")
const Screen := preload("res://scenes/screen.gd")
const MENU := [["home", "ui.menu.home"], ["squad", "ui.menu.squad"], ["tables", "ui.menu.tables"],
		["calendar", "ui.menu.calendar"], ["news", "ui.menu.news"], ["tactics", "ui.menu.tactics"]]
const SCREENS := {
	"careers": preload("res://scenes/screens/careers.gd"),
	"home": preload("res://scenes/screens/home.gd"),
	"squad": preload("res://scenes/screens/squad.gd"),
	"player": preload("res://scenes/screens/player.gd"),
	"tables": preload("res://scenes/screens/tables.gd"),
	"calendar": preload("res://scenes/screens/calendar.gd"),
	"news": preload("res://scenes/screens/news.gd"),
	"selection": preload("res://scenes/screens/selection.gd"),
	"tactics": preload("res://scenes/screens/tactics.gd"),
	"match_day": preload("res://scenes/screens/match_day.gd"),
}

var Core: Node
var current: Screen
var current_name := ""
var history: Array[String] = []
var status: Dictionary = {}

var _top: HBoxContainer
var _menu: VBoxContainer
var _content: MarginContainer
var _date_label: Label
var _club_label: Label
var _busy_label: Label
var _continue_button: Button
var _message: Label
var _ready_to_play := false
var _navigating_back := false
var _closing := false
var live_lines: Array = []  # the live match's feed so far (kept across screens)
var live_match: Dictionary = {}  # the live match's MatchView
# a whole-season continue plays the user's matches on the positional engine (spec 008 SC-004:
# up to 2 minutes), so closing waits up to 3 minutes for it
const CLOSE_WAIT_MS := 180000


func _ready() -> void:
	Core = get_node("/root/Core")
	get_tree().set_auto_accept_quit(false)
	_build()
	Core.busy_changed.connect(_on_busy)
	Core.progress.connect(_on_progress)
	Core.state_changed.connect(_on_core_state)
	await start_core()


func _build() -> void:
	theme = UI.make_theme()
	var background := ColorRect.new()
	background.color = Color(0.09, 0.11, 0.14)
	background.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var outer := VBoxContainer.new()
	outer.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(outer)
	_top = UI.row()
	_top.custom_minimum_size.y = 48
	_club_label = UI.label("", 20, true)
	_date_label = UI.label("", 16)
	_busy_label = UI.label("", 14)
	_continue_button = UI.button("Continuar", continue_game)
	_continue_button.custom_minimum_size = Vector2(160, 40)
	for child in [_club_label, _date_label, UI.spacer(), _busy_label, _continue_button]:
		_top.add_child(child)
	var top_margin := _margin(_top, 12)
	outer.add_child(top_margin)
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	outer.add_child(body)
	_menu = UI.column()
	_menu.custom_minimum_size.x = 190
	body.add_child(_margin(_menu, 12))
	_content = MarginContainer.new()
	_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	for side in ["left", "right", "top", "bottom"]:
		_content.add_theme_constant_override("margin_" + side, 12)
	body.add_child(_content)
	_message = UI.paragraph("", 14)
	_message.add_theme_color_override("font_color", Color(1, 0.6, 0.5))
	outer.add_child(_margin(_message, 8))
	_set_playing(false)


func _margin(child: Control, size: int) -> MarginContainer:
	var m := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		m.add_theme_constant_override("margin_" + side, size)
	m.add_child(child)
	return m


# ---- core lifecycle ----------------------------------------------------------------------------


func start_core() -> void:
	message("")
	_show_text(Core.LOCAL["starting"])
	if await Core.start():
		_continue_button.text = Core.t("ui.continue")
		_build_menu()
		show_screen("careers")
	else:
		_show_failure(Core.failure)


func _show_failure(text: String) -> void:
	_set_playing(false)
	var box := UI.column([UI.title("Manager"), UI.label(text, 16)])
	box.add_child(UI.button(Core.LOCAL["retry"], start_core))
	_set_content(box)


func _show_text(text: String) -> void:
	_set_content(UI.column([UI.paragraph(text, 18)]))


func _on_core_state(state: String) -> void:
	if state == "failed" and _ready_to_play:
		_ready_to_play = false
		_show_failure(Core.failure)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		await close_game()
		get_tree().quit()


## Let a running request finish (so its progress is saved), then shut the core down: it saves
## the open career. Closing twice does nothing more.
func close_game() -> void:
	if _closing:
		return
	_closing = true
	if Core.is_busy():
		message(Core.t("ui.desktop.saving"))
		var deadline := Time.get_ticks_msec() + CLOSE_WAIT_MS
		while Core.is_busy() and Time.get_ticks_msec() < deadline:
			await get_tree().process_frame
	await Core.stop()


# ---- layout ------------------------------------------------------------------------------------


func _build_menu() -> void:
	for child in _menu.get_children():
		child.queue_free()
	for entry in MENU:
		var b := UI.button(Core.t(entry[1]), show_screen.bind(entry[0]))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size.y = 36
		_menu.add_child(b)
	_menu.add_child(UI.spacer())
	var careers := UI.button(Core.t("ui.careers.title"), show_screen.bind("careers"))
	careers.alignment = HORIZONTAL_ALIGNMENT_LEFT
	_menu.add_child(careers)


func _set_playing(playing: bool) -> void:
	_ready_to_play = playing
	_menu.visible = playing
	_continue_button.visible = playing
	_date_label.visible = playing
	_club_label.visible = playing


func _set_content(node: Control) -> void:
	for child in _content.get_children():
		_content.remove_child(child)
		child.queue_free()
	_content.add_child(node)


func show_screen(name: String, args: Dictionary = {}) -> Screen:
	if current_name != "" and current_name != name and not _navigating_back:
		history.append(current_name)
	var screen: Screen = SCREENS[name].new()
	screen.main = self
	for key in args:
		screen.set(key, args[key])
	current = screen
	current_name = name
	_set_content(screen)
	message("")
	await screen.open()
	return screen


func go_back() -> void:
	if current != null and current.back():
		return
	if history.is_empty():
		return
	var previous: String = history.pop_back()
	_navigating_back = true
	await show_screen(previous)
	_navigating_back = false


func message(text: String) -> void:
	_message.text = text


## A career was opened or created: the top bar, the home screen, then any notices.
func open_career(new_status: Dictionary, notices: Array) -> void:
	career_opened(new_status)
	await show_screen("home")
	for notice in notices:
		message(notice)


## After a career opens (or the date changes): the top bar.
func career_opened(new_status: Dictionary) -> void:
	_set_playing(true)
	history.clear()
	update_status(new_status)


func update_status(new_status: Dictionary) -> void:
	status = new_status
	_club_label.text = str(status.get("club_name", ""))
	_date_label.text = Core.t("ui.home.date", {
		"date": UI.date_text(str(status.get("current_date", ""))), "year": status.get("year", "")})


func refresh_status() -> void:
	var answer: Dictionary = await Core.request("career.status")
	if answer.has("result"):
		update_status(answer["result"])


# ---- the loop ----------------------------------------------------------------------------------


func continue_game() -> void:
	if not _ready_to_play or Core.is_busy():
		return
	var pending = status.get("pending")
	if pending is Dictionary and pending.get("kind") == "user_match":
		await show_screen("selection")
		return
	var answer: Dictionary = await Core.request("career.continue")
	if answer.has("error"):
		message(UI.error_text(answer))
		return
	await handle_stop(answer["result"])


func handle_stop(stop: Dictionary) -> void:
	await refresh_status()
	match stop.get("kind"):
		"user_match":
			await show_screen("selection")
		"event":
			message(Core.t("ui.stop.event", {"date": UI.date_text(str(stop["day"]))}))
			await show_screen("home")
		_:
			message(Core.t("ui.stop.season_end", {"year": status.get("year", "")}))
			await show_screen("home")


## Team selection confirmed: the match is played live (spec 008); its screen starts it.
func play_match_day() -> void:
	await show_screen("match_day")


func _on_busy(busy: bool) -> void:
	_busy_label.text = Core.t("ui.desktop.busy") if busy else ""
	_continue_button.disabled = busy


func _on_progress(params: Dictionary) -> void:
	_busy_label.text = Core.t("ui.desktop.progress", {"date": UI.date_text(str(params.get("day", "")))})


func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	if get_viewport().gui_get_focus_owner() is LineEdit:
		return
	match event.keycode:
		KEY_SPACE:
			if current_name == "match_day":
				current._toggle_pause()
				get_viewport().set_input_as_handled()
			elif current_name not in ["selection", "tactics", "careers"]:
				continue_game()
				get_viewport().set_input_as_handled()
		KEY_X:
			if _ready_to_play and current_name != "tactics":
				show_screen("tactics")
				get_viewport().set_input_as_handled()
		KEY_ESCAPE:
			go_back()
			get_viewport().set_input_as_handled()

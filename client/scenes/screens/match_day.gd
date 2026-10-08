extends "res://scenes/screen.gd"
## Match day, live (spec 008 US3/US5): the window drives the match clock through the core
## (`match.advance`); Pausar stops it. While paused: substitutions (here) and the tactic (the
## tactics screen in live mode). After full time: the stats, then Continuar commits the match and
## goes on to the next stop. Every rule is the core's.

const SPEEDS := {1: 7.5, 2: 15.0, 3: 45.0, 4: 900.0}  # match seconds per 0.25 s tick
const TICK := 0.25

var _feed: RichTextLabel
var _score: Label  # LED digits on the scoreboard
var _clock: Label
var _home_name: Label
var _away_name: Label
var _half_time: Label
var _pause_button: Button
var _subs_panel: VBoxContainer
var _on_list: ItemList
var _bench_list: ItemList
var _subs_info: Label
var _stats: Tree
var _continue_button: Button
var _paused_for_subs := false
var _timer: Timer
var _speed := 2
var _paused := false
var _state: Dictionary = {}
var _finished := false
var _names := {}


func open() -> void:
	clear()
	var started = await _start_or_resume()
	if started == null:
		return
	add_child(UI.title(UI.t("ui.match.title")))
	add_child(_scoreboard())
	var controls := UI.row([UI.label(UI.t("ui.desktop.speed"))])
	for s in [1, 2, 3, 4]:
		controls.add_child(UI.button(str(s), _set_speed.bind(s)))
	_pause_button = UI.button(UI.t("ui.live.pause"), _toggle_pause)
	controls.add_child(_pause_button)
	controls.add_child(UI.button(UI.t("ui.live.subs"), _show_subs))
	controls.add_child(UI.button(UI.t("ui.menu.tactics"), _open_tactics))
	controls.add_child(UI.spacer())
	_continue_button = UI.primary_button(UI.t("ui.continue"), _done)
	_continue_button.visible = false
	controls.add_child(_continue_button)
	add_child(controls)
	_feed = RichTextLabel.new()
	_feed.bbcode_enabled = true
	_feed.scroll_following = true
	_feed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(_feed)
	for line in main.live_lines:
		_show_line(line)
	_build_subs_panel()
	_stats = UI.table(["", "", ""])
	_stats.custom_minimum_size.y = 250
	_stats.visible = false
	add_child(_stats)
	_timer = Timer.new()
	_timer.wait_time = TICK
	_timer.timeout.connect(_tick)
	add_child(_timer)
	_update(started)
	if _finished:
		_show_end()
	elif not _paused:
		_timer.start()


## The live match: resume the one in progress (after visiting the tactics screen), or start it.
func _start_or_resume() -> Variant:
	var core = get_node("/root/Core")
	var state: Dictionary = await core.request("match.state")
	if state.has("result"):
		_paused = true  # coming back from the tactics screen: still paused
		return {"state": state["result"], "feed": [], "finished": state["result"]["finished"]}
	main.live_lines = []
	var started = await ask("match.start")
	if started != null:
		main.live_match = started["match"]
	return started


func _build_subs_panel() -> void:
	_subs_panel = UI.column([UI.label(UI.t("ui.live.subs"), 16, true)])
	_on_list = ItemList.new()
	_bench_list = ItemList.new()
	for list in [_on_list, _bench_list]:
		list.custom_minimum_size = Vector2(320, 220)
	_subs_info = UI.label("")
	_subs_panel.add_child(UI.row([
		UI.column([UI.label(UI.t("ui.live.on_pitch")), _on_list]),
		UI.column([UI.label(UI.t("ui.live.bench")), _bench_list]),
	]))
	_subs_panel.add_child(UI.row([UI.button(UI.t("ui.live.substitute"), _substitute), _subs_info,
			UI.spacer(), UI.button(UI.t("ui.desktop.back"), _close_subs)]))
	_subs_panel.visible = false
	add_child(_subs_panel)


func _set_speed(speed: int) -> void:
	_speed = speed
	if _paused and not _finished:
		_toggle_pause()


func _toggle_pause() -> void:
	_paused_for_subs = false  # a pause by hand (button, Esc) is the user's: Voltar keeps it
	if _finished:
		return
	_paused = not _paused
	_pause_button.text = UI.t("ui.live.resume") if _paused else UI.t("ui.live.pause")
	if _paused:
		_timer.stop()
	else:
		_subs_panel.visible = false
		_timer.start()


func _tick() -> void:
	_timer.stop()
	var step = await ask("match.advance", {"seconds": SPEEDS[_speed]})
	if step == null:
		return
	_update(step)
	if _finished:
		_show_end()
	elif not _paused:
		_timer.start()


## The stadium scoreboard: names either side, the score and the clock in LED digits.
func _scoreboard() -> PanelContainer:
	_home_name = UI.label("", 26)
	_away_name = UI.label("", 26)
	for name in [_home_name, _away_name]:
		name.add_theme_font_override("font", UI.font(UI.CONDENSED_BOLD))
		name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		name.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_home_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_score = UI.led("", 54)
	_score.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_clock = UI.led("", 30)
	_half_time = UI.led("", 22)
	var clock_row := UI.row([_clock, _half_time])
	clock_row.alignment = BoxContainer.ALIGNMENT_CENTER
	var middle := UI.column([_score, clock_row])
	middle.custom_minimum_size.x = 220
	var board := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color.BLACK
	style.border_color = Color("2a1d06")
	style.set_border_width_all(1)
	style.set_corner_radius_all(6)
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 6
	style.content_margin_bottom = 8
	board.add_theme_stylebox_override("panel", style)
	board.add_child(UI.row([_home_name, middle, _away_name]))
	return board


func _update(step: Dictionary) -> void:
	for line in step.get("feed", []):
		main.live_lines.append(line)
		_show_line(line)
	_state = step["state"]
	_finished = step.get("finished", false)
	var m: Dictionary = main.live_match
	var score: Array = _state["score"]
	_home_name.text = str(m.get("home_name", "")).to_upper()
	_away_name.text = str(m.get("away_name", "")).to_upper()
	_score.text = "%d-%d" % [score[0], score[1]]
	var minute: Dictionary = _state["minute"]
	_clock.text = ("%d+%d'" % [minute["base"], minute["added"]]) if minute["added"] > 0 \
			else ("%d'" % minute["base"])
	_half_time.text = UI.t("ui.live.half_time").to_upper() if _state["at_half_time"] else ""
	for p in _state["on_pitch"] + _state["bench"]:
		_names[p["player_id"]] = p["name"]
	if _subs_panel != null and _subs_panel.visible:
		_fill_subs()


func _show_line(line: Dictionary) -> void:
	var minute: Dictionary = line["minute"]
	var stamp := "%d'" % minute["base"]
	if minute["added"] > 0:
		stamp = "%d+%d'" % [minute["base"], minute["added"]]
	var important: bool = line["kind"] in ["goal", "penalty_goal", "own_goal", "red",
			"second_yellow", "full_time"]
	var text := "[b]%s[/b]  %s" % [stamp, line["text"]]
	_feed.append_text(("[color=#ffd970]%s[/color]" % text if important else text) + "\n")


func _show_subs() -> void:
	if _subs_panel.visible:
		_close_subs()
		return
	var pausing := not _paused
	if pausing:
		_toggle_pause()
	_paused_for_subs = pausing  # set after the toggle, which clears it
	_subs_panel.visible = true
	_fill_subs()


## Back out of the substitutions: resume if opening them had paused the match.
func _close_subs() -> void:
	_subs_panel.visible = false
	if _paused_for_subs and _paused and not _finished:
		_toggle_pause()
	_paused_for_subs = false


func _fill_subs() -> void:
	_on_list.clear()
	_bench_list.clear()
	for p in _state["on_pitch"]:
		var text := "%s  %s  %d%%" % [p["position"], p["name"], roundi(p["energy"] * 100)]
		if p["yellow"]:
			text += "  🟨"
		var i := _on_list.add_item(text)
		_on_list.set_item_metadata(i, p["player_id"])
	for p in _state["bench"]:
		var i := _bench_list.add_item(p["name"])
		_bench_list.set_item_metadata(i, p["player_id"])
	_subs_info.text = UI.t("ui.live.subs_left", {"subs": _state["subs_left"],
			"windows": _state["windows_left"]})


func _substitute() -> void:
	var off := _on_list.get_selected_items()
	var on := _bench_list.get_selected_items()
	if off.is_empty() or on.is_empty():
		main.message(UI.t("ui.desktop.pick_two"))
		return
	var state = await ask("match.substitute", {
		"off": _on_list.get_item_metadata(off[0]), "on": _bench_list.get_item_metadata(on[0])})
	if state != null:
		_update({"state": state, "feed": [], "finished": _finished})
		main.message("")


func _open_tactics() -> void:
	if not _paused:
		_toggle_pause()
	main.show_screen("tactics", {"live": true})  # not awaited: navigation frees this screen


func _show_end() -> void:
	_timer.stop()
	_pause_button.disabled = true
	_subs_panel.visible = false
	var m: Dictionary = main.live_match
	_stats.set_column_title(1, m.get("home_name", ""))
	_stats.set_column_title(2, m.get("away_name", ""))
	var rows := []
	for key in ["shots", "shots_on_target", "xg", "possession", "corners", "fouls", "yellows",
			"reds"]:
		var home = _state["home"][key]
		var away = _state["away"][key]
		if key == "possession":
			home = "%d%%" % home
			away = "%d%%" % away
		rows.append([UI.t("stat." + key), str(home), str(away)])
	UI.fill(_stats, rows)
	_stats.visible = true
	_continue_button.visible = true


func _done() -> void:
	_continue_button.disabled = true
	var finished = await ask("match.finish")
	if finished == null:
		_continue_button.disabled = false
		return
	main.live_lines = []
	main.handle_stop(finished["stop"])  # navigation frees this screen: not awaited


func back() -> bool:
	if _subs_panel.visible:
		_close_subs()
		return true
	if not _paused and not _finished:
		_toggle_pause()
	return true  # a live match is left only through Continuar

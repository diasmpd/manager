extends "res://scenes/screen.gd"
## Match day, live (spec 008 US3/US5): the window drives the match clock through the core
## (`match.advance`); Pausar stops it. While paused: substitutions and the tactic. After full
## time: the stats, then Continuar commits the match and goes on to the next stop. Every rule is
## the core's.
##
## The scoreboard and the controls stay on top for the whole match day: the menu's screens (news,
## tables, the tactic...) open below them, inside this screen, and Partida comes back to the match
## (owner report 2026-10-16). The tactic and the substitutions pause the match while open.
##
## Two views of the same match (spec 008b): the pitch, drawn from the positions the core sends
## with each step, and the text feed. The pitch asks for the match a little ahead of the screen
## and plays it back; pausing stops the asking, and the screen stops when it has shown what it
## holds, so a change made while paused acts from the moment on screen.

const Playback := preload("res://scenes/match/playback.gd")
const Pitch := preload("res://scenes/match/pitch.gd")
const SPEEDS := {1: 7.5, 2: 15.0, 3: 45.0, 4: 900.0}  # text: match seconds per 0.25 s tick
const PITCH_SPEEDS := {1: 1.0, 2: 2.0, 3: 4.0, 4: 8.0}  # pitch: times real time
const TICK := 0.25
const AHEAD_S := 0.75  # real seconds of match the pitch keeps ahead of the screen
const SETTINGS := "user://settings.cfg"
const SKIP_S := 30.0  # highlights: match seconds per tick between two passages
const LOOK_AHEAD_S := 180.0  # highlights: how far ahead the core is asked to look

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
var _pitch_view := true
var _playback: RefCounted
var _pitch: Control
var _line: Label  # the latest feed line, under the pitch
var _info: Label  # the disc the owner clicked
var _view_button: Button
var _speed_buttons: Array = []
var _due: Array = []  # feed lines waiting for the screen to reach them: [match seconds, line]
var _asking := false
var _rush := false  # playing to the end without drawing
var _catch_up := false  # the positions missed while the text view ran are due
var _ended := false
var _replay_button: Button
# Highlights (spec 008b US4): the pitch shows only the passages the core names; between them the
# clock runs on with the feed. The core looks ahead on a copy of the match, so the match itself
# is never ahead of the screen and a pause acts from the minute shown.
var _highlights := false
var _show_until := -1.0  # showing a passage up to this match time; below zero: between passages
var _skip_to := -1.0  # between passages: the match time to run to; below zero: ask the core
var _mode_button: Button
var _body: VBoxContainer  # the match itself: pitch or feed, substitutions, stats
var _inner: VBoxContainer  # a menu screen opened during the match
var _inner_screen: Control
var _inner_name := ""
var _inner_stack: Array[String] = []  # the in-match screens before this one (Esc goes back)
var _paused_for_inner := false
var _match_button: Button


func open() -> void:
	clear()
	var started = await _start_or_resume()
	if started == null:
		return
	add_child(UI.title(UI.t("ui.match.title")))
	add_child(_scoreboard())
	_playback = main.live_playback
	_pitch_view = _saved_view() and _playback != null
	_catch_up = _playback != null
	var controls := UI.row([UI.label(UI.t("ui.desktop.speed"))])
	_speed_buttons = []
	for s in [1, 2, 3, 4]:
		_speed_buttons.append(UI.button(str(s), _set_speed.bind(s)))
		controls.add_child(_speed_buttons[-1])
	controls.add_child(UI.button(UI.t("ui.live.to_end"), _to_end))
	_pause_button = UI.button(UI.t("ui.live.pause"), _toggle_pause)
	controls.add_child(_pause_button)
	_view_button = UI.button("", _toggle_view)
	_view_button.visible = _playback != null
	controls.add_child(_view_button)
	_highlights = _saved("mode", "full") == "highlights"
	_mode_button = UI.button("", _toggle_highlights)
	controls.add_child(_mode_button)
	controls.add_child(UI.button(UI.t("ui.live.subs"), _show_subs))
	controls.add_child(UI.button(UI.t("ui.menu.tactics"), _open_tactics))
	controls.add_child(UI.spacer())
	_match_button = UI.primary_button(UI.t("ui.live.match"), close_inner)
	_match_button.visible = false
	controls.add_child(_match_button)
	_replay_button = UI.button(UI.t("ui.replay.watch"), _watch_again)
	_replay_button.visible = false
	controls.add_child(_replay_button)
	_continue_button = UI.primary_button(UI.t("ui.continue"), _done)
	_continue_button.visible = false
	controls.add_child(_continue_button)
	add_child(controls)
	_body = UI.column()
	_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(_body)
	_inner = UI.column()
	_inner.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_inner.visible = false
	add_child(_inner)
	_pitch = Pitch.new()
	_pitch.playback = _playback
	_pitch.slot_picked.connect(_show_disc)
	_body.add_child(_pitch)
	_line = UI.label("", 16, true)
	_line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_body.add_child(_line)
	_info = UI.label(UI.t("ui.pitch.pick"))
	_info.add_theme_color_override("font_color", UI.MUTE)
	_body.add_child(_info)
	_feed = RichTextLabel.new()
	_feed.bbcode_enabled = true
	_feed.scroll_following = true
	_feed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_body.add_child(_feed)
	for line in main.live_lines:
		_show_line(line)
	_build_subs_panel()
	_stats = UI.table(["", "", ""])
	_stats.custom_minimum_size.y = 250
	_stats.visible = false
	_body.add_child(_stats)
	_timer = Timer.new()
	_timer.wait_time = TICK
	_timer.timeout.connect(_tick)
	add_child(_timer)
	_update(started)
	_apply_view()
	if _finished and not _pitch_view:
		_show_end()
	else:
		_run()


## The live match: resume the one in progress (after visiting the tactics screen), or start it.
func _start_or_resume() -> Variant:
	var core = get_node("/root/Core")
	var state: Dictionary = await core.request("match.state")
	if state.has("result"):
		_paused = true  # coming back from the tactics screen: still paused
		return {"state": state["result"], "feed": [], "finished": state["result"]["finished"]}
	main.live_lines = []
	main.live_playback = null
	var started = await ask("match.start")
	if started != null:
		main.live_match = started["match"]
		if started.has("pitch"):
			main.live_pitch = started["pitch"]
			main.live_playback = Playback.new()
			main.live_playback.setup(main.live_pitch)
	return started


## Start whatever drives the clock in this view: the timer for the text (and for playing to the
## end); the pitch asks from `_process`.
func _run() -> void:
	if _paused or _finished:
		return
	if not _pitch_view or _rush or _skipping():
		_timer.start()


func _saved(key: String, default: String) -> String:
	var config := ConfigFile.new()
	config.load(SETTINGS)
	return config.get_value("match", key, default)


func _save(key: String, value: String) -> void:
	var config := ConfigFile.new()
	config.load(SETTINGS)
	config.set_value("match", key, value)
	config.save(SETTINGS)


func _saved_view() -> bool:
	return _saved("view", "pitch") == "pitch"


## Between two passages of the highlights: the timer runs the clock, the pitch waits.
func _skipping() -> bool:
	return _highlights and _pitch_view and _show_until < 0.0 and not _finished


func _toggle_highlights() -> void:
	_set_highlights(not _highlights)


func _set_highlights(on: bool) -> void:
	if on == _highlights:
		return
	_highlights = on
	_save("mode", "highlights" if on else "full")
	_show_until = -1.0
	_skip_to = -1.0
	if not on and _pitch_view and not _rush:
		_timer.stop()
		_catch_up = true  # back to the whole match, from the current moment
	_apply_view()
	_run()


## Highlights: ask the core what is coming, then either show the passage that has started or
## run the clock to the next one (or as far as the core looked).
func _plan() -> void:
	_asking = true
	var ahead = await ask("match.passages", {"horizon_s": LOOK_AHEAD_S})
	_asking = false
	if ahead == null or not _skipping():
		return
	var now: float = ahead["from_s"]
	if not ahead["passages"].is_empty():
		var next: Array = ahead["passages"][0]
		if next[0] <= now + 0.5:
			_show_until = next[1]
			_catch_up = true  # the pitch takes up the match here
			_timer.stop()
		else:
			_skip_to = next[0]
		return
	_skip_to = ahead["until_s"] if ahead["until_s"] > now + 0.5 else now + SKIP_S


func _toggle_view() -> void:
	_set_view(not _pitch_view)


func _set_view(pitch: bool) -> void:
	if pitch == _pitch_view or _playback == null:
		return
	_pitch_view = pitch
	_save("view", "pitch" if _pitch_view else "text")
	_show_until = -1.0
	_skip_to = -1.0
	_apply_view()
	if _pitch_view:
		_timer.stop()
		_catch_up = true
	else:
		_flush_due()
		if _finished and not _ended:
			_show_end()
	_run()


func _apply_view() -> void:
	_pitch.visible = _pitch_view
	_line.visible = _pitch_view
	_info.visible = _pitch_view
	_feed.visible = not _pitch_view
	_view_button.text = UI.t("ui.live.view_text" if _pitch_view else "ui.live.view_pitch")
	_mode_button.visible = _pitch_view
	_mode_button.text = UI.t("ui.live.mode_full" if _highlights else "ui.live.mode_highlights")
	for i in _speed_buttons.size():
		_speed_buttons[i].text = ("%d×" % PITCH_SPEEDS[i + 1]) if _pitch_view else str(i + 1)
	_paint_score()


## The pitch: move the playhead, show what it reached, and ask for more of the match when the
## screen is about to run out of it.
func _process(delta: float) -> void:
	if not _pitch_view or _playback == null or _timer == null:
		return
	var speed: float = PITCH_SPEEDS[_speed]
	if not _catch_up:
		_playback.advance(delta, speed)
	_release_due()
	_paint_score()
	_pitch.modulate.a = 0.45 if _skipping() and not _rush else 1.0
	_pitch.queue_redraw()
	if _finished and not _ended and not _catch_up and _playback.at_end():
		_show_end()
	if _asking or _rush:
		return
	if _catch_up:
		_fetch(0.0)  # only what was missed: no match time passes
		return
	if _highlights and not _finished:
		if _show_until < 0.0:
			return  # between passages: the timer runs the clock
		if float(_state.get("time_s", 0.0)) >= _show_until:
			if _playback.at_end():  # the passage has been shown: on to the next
				_show_until = -1.0
				_skip_to = -1.0
				_run()
			return
	if not _paused and not _finished and _playback.buffered_s() < speed * AHEAD_S:
		_fetch(speed)


func _fetch(seconds: float) -> void:
	_asking = true
	var step = await ask("match.advance", {"seconds": seconds, "frames_from": _playback.count})
	_asking = false
	if step == null:
		return
	_update(step)


func _release_due() -> void:
	while not _due.is_empty() and _due[0][0] <= _playback.time_s() + 0.01:
		_show_line(_due.pop_front()[1])


func _flush_due() -> void:
	for pair in _due:
		_show_line(pair[1])
	_due = []


## The score on the pitch view is the playhead's, so a goal is not on the board before the ball
## is in the net.
func _paint_score() -> void:
	if _score == null or _state.is_empty():
		return
	var score: Array = _state["score"]
	if _pitch_view and _playback != null and not _catch_up and _playback.count > 0:
		score = _playback.score()
	_score.text = "%d-%d" % [score[0], score[1]]


## Play to full time without drawing (the pitch shows the final whistle afterwards).
func _to_end() -> void:
	if _finished:
		return
	_rush = true
	_speed = 4
	if _paused:
		_toggle_pause()
	else:
		_run()


func _show_disc(slot: int) -> void:
	if slot < 0:
		_info.text = UI.t("ui.pitch.pick")
		return
	var who: Dictionary = _playback.player(slot)
	var text := "%d  %s" % [int(who.get("number", 0)), who.get("name", "")]
	for p in _state.get("on_pitch", []):
		if p["player_id"] == who.get("player_id", ""):
			text = "%d  %s  %s  %s %d%%" % [int(who["number"]), p["position"], p["name"],
					UI.t("ui.live.energy"), roundi(p["energy"] * 100)]
	var card: String = _playback.cards().get(who.get("player_id", ""), "")
	if card != "":
		text += "  🟨" if card == "yellow" else "  🟥"
	_info.text = text


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
	_body.add_child(_subs_panel)


func _set_speed(speed: int) -> void:
	_speed = speed
	if _rush:  # choosing a speed ends "to the end": back to watching
		_rush = false
		if _pitch_view:
			_catch_up = true
			_timer.stop()
	if _paused and not _finished:
		_toggle_pause()


func _toggle_pause() -> void:
	_paused_for_subs = false  # a pause by hand (button, Esc) is the user's: Voltar keeps it
	_paused_for_inner = false
	if _finished:
		return
	_paused = not _paused
	_pause_button.text = UI.t("ui.live.resume") if _paused else UI.t("ui.live.pause")
	if _paused:
		_timer.stop()
	else:
		_subs_panel.visible = false
		_run()


func _tick() -> void:
	_timer.stop()
	var seconds: float = SPEEDS[_speed]
	if _skipping() and not _rush:
		if _skip_to < 0.0:
			await _plan()
			_run()
			return
		seconds = minf(SKIP_S, _skip_to - float(_state.get("time_s", 0.0)))
		if seconds <= 0.01:
			_skip_to = -1.0
			_run()
			return
	var step = await ask("match.advance", {"seconds": seconds})
	if step == null:
		return
	_update(step)
	if _finished:
		_rush = false
		if _pitch_view:
			_catch_up = true  # the pitch fetches what it missed and shows the final whistle
		else:
			_show_end()
	else:
		_run()


func _scoreboard() -> PanelContainer:
	var board := UI.scoreboard()
	_home_name = board["home"]
	_away_name = board["away"]
	_score = board["score"]
	_clock = board["clock"]
	_half_time = board["note"]
	return board["panel"]


func _update(step: Dictionary) -> void:
	_state = step["state"]
	_finished = step.get("finished", false)
	var caught_up := false
	if step.has("frames") and _playback != null:
		_playback.add(step["frames"])
		if _catch_up:  # back on the pitch: resume at the current moment
			_playback.seek(_playback.count)
			_catch_up = false
			caught_up = true
	for line in step.get("feed", []):
		main.live_lines.append(line)
		if _pitch_view and step.has("frames") and not caught_up:
			_due.append([float(_state.get("time_s", 0.0)), line])
		else:
			_show_line(line)
	var m: Dictionary = main.live_match
	_home_name.text = str(m.get("home_name", "")).to_upper()
	_away_name.text = str(m.get("away_name", "")).to_upper()
	_paint_score()
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
	if _line != null:
		_line.text = "%s  %s" % [stamp, line["text"]]
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
	main.show_screen("tactics")


## A menu screen inside the match day (main.show_screen routes here during a match).
func show_inner(name: String, args: Dictionary = {}, remember := true) -> Variant:
	if remember and _inner_name != "" and _inner_name != name:
		_inner_stack.append(_inner_name)
	_leave_inner()
	if _subs_panel.visible:
		_close_subs()
	if name == "tactics":
		args["live"] = true
		if not _paused and not _finished:
			_toggle_pause()
			_paused_for_inner = true  # set after the toggle, which clears it
	var screen: Control = main.make_screen(name)
	for key in args:
		screen.set(key, args[key])
	_inner_name = name
	_inner_screen = screen
	_inner.add_child(screen)
	_body.visible = false
	_inner.visible = true
	_match_button.visible = true
	await screen.open()
	return screen


## Back to the match: resume if opening the tactic had paused it.
func close_inner() -> void:
	_leave_inner()
	_inner_name = ""
	_inner_stack.clear()
	_inner.visible = false
	_body.visible = true
	_match_button.visible = false
	main.mark_menu("")
	main.message("")


func _leave_inner() -> void:
	if _inner_screen != null:
		_inner.remove_child(_inner_screen)
		_inner_screen.queue_free()
		_inner_screen = null
	if _inner_name == "tactics" and _paused_for_inner and _paused and not _finished:
		_toggle_pause()
	_paused_for_inner = false


func _show_end() -> void:
	_ended = true
	_flush_due()
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
	_replay_button.visible = _playback != null


## The match just played, again (it is committed only by Continuar, and Voltar comes back here).
func _watch_again() -> void:
	main.show_screen("replay")  # not awaited: navigation frees this screen


func _done() -> void:
	_continue_button.disabled = true
	var finished = await ask("match.finish")
	if finished == null:
		_continue_button.disabled = false
		return
	main.live_lines = []
	main.handle_stop(finished["stop"])  # navigation frees this screen: not awaited


func back() -> bool:
	if _inner.visible:
		if _inner_stack.is_empty():
			close_inner()
		else:
			var previous: String = _inner_stack.pop_back()
			main.mark_menu(previous)
			show_inner(previous, {}, false)  # not awaited: Esc only starts it
		return true
	if _subs_panel.visible:
		_close_subs()
		return true
	if not _paused and not _finished:
		_toggle_pause()
	return true  # a live match is left only through Continuar

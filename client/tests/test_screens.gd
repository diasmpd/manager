extends RefCounted

const UI := preload("res://scenes/ui.gd")
## The window and its screens against the real core (spec 007 T022): a scripted session.

var main: Node


func _wait(t, condition: Callable, seconds := 60.0) -> bool:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000)
	while Time.get_ticks_msec() < deadline:
		if condition.call():
			return true
		await t.process_frame
	return condition.call()


func _no_error(t, where: String) -> void:
	t.check(main._message.text == "" or not main._message.text.begins_with("Erro"),
			where + ": " + main._message.text)


func test_start_on_the_careers_screen(t) -> void:
	main = load("res://scenes/main.tscn").instantiate()
	t.root.add_child(main)
	var started: bool = await _wait(t, func(): return (main.current_name == "careers"
			and main.current.get_child_count() > 2))
	t.check(started, "careers screen shown (core: %s)" % t.core().failure)


func test_create_a_career(t) -> void:
	var careers = main.current
	var loaded: bool = await _wait(t, func(): return (careers._clubs != null
			and careers._clubs.item_count > 0))
	t.check(loaded, "clubs loaded")
	careers._name.text = "janela"
	careers._clubs.select(0)
	careers._create()
	var home: bool = await _wait(t, func(): return (main.current_name == "home"
			and main.current.get_child_count() > 2))
	t.check(home, "home after creating")
	t.check(main._club_label.text != "", "top bar shows the club")
	t.check(main._continue_button.visible, "Continuar visible")


func test_every_menu_screen_opens(t) -> void:
	for name in ["home", "squad", "tables", "calendar", "news", "tactics"]:
		await main.show_screen(name)
		t.check(main.current_name == name, name + " shown")
		t.check(main.current.get_child_count() > 1, name + " drew something")
		_no_error(t, name)


func test_player_profile(t) -> void:
	await main.show_screen("squad")
	var answer: Dictionary = await t.core().request("view.squad")
	var pid: String = answer["result"][0]["player_id"]
	await main.show_screen("player", {"player_id": pid})
	t.check(main.current.get_child_count() > 3, "profile drawn")
	main.go_back()
	await _wait(t, func(): return main.current_name == "squad")
	t.check(main.current_name == "squad", "back to the squad")


func test_group_tables(t) -> void:
	await main.show_screen("tables")
	var screen = main.current
	t.check(screen._choice.item_count > 1, "groups offered")
	screen._choice.select(1)
	await screen._load_table()
	t.check(screen._table.get_root().get_child_count() >= 3, "a group table drawn")


func test_selection_controls(t) -> void:
	await main.show_screen("selection")
	var screen = main.current
	var before: Array = screen._selection["starters"].duplicate(true)
	UI.select_key(screen._xi, int(before[-1][0]))
	var bench_player: String = screen._selection["bench"][0]
	UI.select_key(screen._others, bench_player)
	await screen._swap()
	var after: Array = screen._selection["starters"]
	t.check(after.any(func(pair): return pair[1] == bench_player), "the bench player starts")
	var other: int = screen._formations.find("4-3-3")
	await screen._change_formation(other)
	t.check(screen._selection["formation"] == "4-3-3", "formation changed")
	t.check(screen._xi.get_root().get_child_count() == 11, "still eleven")
	await screen._assistant()
	t.check(screen._selection["starters"].size() == 11, "assistant proposal")


func test_play_to_the_first_match_and_watch_it(t) -> void:
	await main.show_screen("home")
	var reached := false
	for i in 30:
		await main.continue_game()
		if main.current_name == "selection":
			reached = true
			break
	t.check(reached, "a user match day opened team selection")
	if not reached:
		return
	var selection = main.current
	t.check(selection._xi.get_root().get_child_count() == 11, "eleven starters listed")
	t.check(main._continue_button.text == UI.t("ui.desktop.go_to_match").to_upper(),
			"the top bar says Ir para o jogo on a match day")
	main.continue_game()  # Ir para o jogo
	var shown: bool = await _wait(t, func(): return main.current_name == "match_day")
	if not shown and main.current_name == "selection":  # a no-goalkeeper warning: go again
		main.continue_game()
		shown = await _wait(t, func(): return main.current_name == "match_day")
	t.check(shown, "the match day is shown")
	await _wait(t, func(): return main.current._timer != null)
	var day = main.current
	# the pitch (spec 008b): positions arrive a little ahead of the screen and are played back
	t.check(day._playback != null, "the match came with its pitch")
	day._set_view(true)
	day._set_highlights(false)
	day._set_speed(4)  # 8x
	var playing: bool = await _wait(t, func(): return day._playback.playhead > 6.0, 30.0)
	t.check(playing, "the pitch plays the positions it receives")
	t.check(day._playback.ball() != null and day._playback.position(0) != null
			and day._playback.position(21) != null, "the ball and both sides are on the pitch")
	t.check(day._pitch.visible and not day._feed.visible, "the pitch is shown, not the feed")
	t.check(day._playback.buffered_s() <= 8.0 * 2.0, "the core is not far ahead of the screen")
	# pausing: the screen plays out what it holds and stops at the core's moment
	day._toggle_pause()
	var stopped: bool = await _wait(t, func(): return (day._playback.at_end()
			and not day._asking), 10.0)
	t.check(stopped, "the pitch stops when paused")
	var held: int = day._playback.count
	t.check(absf(day._state["time_s"] - held / 2.0) <= 1.0,
			"the moment on screen is the core's moment")
	for i in 20:
		await t.process_frame
	t.check(day._playback.count == held, "nothing runs while paused")
	day._pitch.slot_picked.emit(3)
	t.check(day._info.text != "" and day._info.text != UI.t("ui.pitch.pick"),
			"a picked disc shows the player")
	day._toggle_pause()
	# highlights: the clock runs to the next passage, then the pitch shows it (spec 008b US4)
	var before_s: float = day._state["time_s"]
	day._set_highlights(true)
	t.check(day._skipping(), "between passages at first")
	var showing: bool = await _wait(t, func(): return day._show_until >= 0.0, 90.0)
	t.check(showing, "a passage is reached and shown")
	t.check(day._state["time_s"] > before_s + 30.0, "the clock ran on to it")
	t.check(day._state["time_s"] <= day._show_until, "the match is not past the passage")
	var caught: bool = await _wait(t, func(): return not day._catch_up, 10.0)
	t.check(caught and absf(day._playback.time_s() - day._state["time_s"]) <= 8.0 * 2.0,
			"the pitch takes up the match at the passage")
	var after: bool = await _wait(t, func(): return day._show_until < 0.0, 60.0)
	t.check(after, "after the passage the clock runs on again")
	day._toggle_pause()
	await _wait(t, func(): return not day._asking and day._timer.is_stopped(), 10.0)
	var paused_at: float = day._state["time_s"]
	for i in 30:
		await t.process_frame
	t.check(day._state["time_s"] == paused_at, "a pause between passages stops the clock")
	day._toggle_pause()
	day._set_highlights(false)
	t.check(not day._skipping(), "back to the whole match")
	# the text view of the same match
	day._set_view(false)
	day._set_speed(2)
	t.check(day._feed.visible and not day._pitch.visible, "the feed is shown, not the pitch")
	var some: bool = await _wait(t, func(): return day._state["minute"]["base"] > 5, 30.0)
	t.check(some, "the live clock runs")
	# the menu's screens open inside the match day: the scoreboard stays, the clock runs on
	await main.show_screen("news")
	t.check(main.current == day and day._inner.visible and not day._body.visible,
			"the news opens inside the match day")
	t.check(day._score.is_visible_in_tree() and day._match_button.visible,
			"the scoreboard and Partida stay on top")
	var news_from: int = day._state["minute"]["base"]
	var ran: bool = await _wait(t, func(): return day._state["minute"]["base"] > news_from, 30.0)
	t.check(ran, "the clock runs while the news is read")
	# the tactic pauses the match, and a change goes to the match at once
	await main.show_screen("tactics")
	t.check(main.current == day and day._paused, "the tactic opens inside, paused")
	var tactics = day._inner_screen
	var mentality: String = tactics._tactic["mentality"]
	UI.select_key(tactics._instructions, "mentality")
	await tactics._cycle_instruction()
	var live_state: Dictionary = await t.core().request("match.state")
	t.check(live_state["result"]["tactic"]["mentality"] != mentality,
			"the new mentality is the match's, with no Confirmar")
	day.close_inner()
	t.check(day._body.visible and not day._inner.visible and not day._paused,
			"Partida: back to the match, playing again")
	# pause, substitute while paused, resume
	day._toggle_pause()
	t.check(day._paused, "paused")
	var minute: int = day._state["minute"]["base"]
	await t.process_frame
	day._show_subs()
	day._on_list.select(1)
	day._bench_list.select(0)
	var incoming: String = day._bench_list.get_item_metadata(0)
	await day._substitute()
	var on_ids: Array = day._state["on_pitch"].map(func(p): return p["player_id"])
	t.check(incoming in on_ids, "the substitute is on the pitch")
	t.check(day._state["minute"]["base"] == minute, "nothing ran while paused")
	day._set_speed(4)  # resumes at full speed
	var ended: bool = await _wait(t, func(): return day._finished, 120.0)
	t.check(ended, "the match reaches full time")
	t.check(day._feed.get_parsed_text().length() > 50, "the feed was written")
	t.check(day._stats.visible and day._continue_button.visible, "the stats and Continuar")
	# back on the pitch after full time: the whole match is there, at the final whistle
	day._set_view(true)
	var whole: bool = await _wait(t, func(): return (day._playback.count > 90 * 60 * 2
			and day._playback.at_end()), 30.0)
	t.check(whole, "the pitch holds the whole match")
	var on_pitch: Array = day._playback.score()
	var final: Array = day._state["score"]
	t.check(int(on_pitch[0]) == int(final[0]) and int(on_pitch[1]) == int(final[1]),
			"the score on the pitch is the final score (%s, %s)" % [on_pitch, final])
	t.check(day._playback.subs.size() >= 1, "the substitution is in the positions")
	# watch it again before going on (spec 008b US3)
	t.check(day._replay_button.visible, "Rever is offered at full time")
	var final_text := "%d-%d" % [int(final[0]), int(final[1])]
	var sub_sample := int(day._playback.subs[0]["sample"])
	day._watch_again()
	var replaying: bool = await _wait(t, func(): return (main.current_name == "replay"
			and main.current.playback != null and main.current._info != null), 30.0)
	t.check(replaying, "the replay of the match just played opens")
	var replay = main.current
	t.check(replay.playback.count > 90 * 60 * 2, "it holds the whole match")
	t.check(replay.clock_text(0.0) == "1'", "the clock starts at 1'")
	t.check(not main._continue_button.visible, "no Continuar over a replay")
	replay.toggle_pause()
	replay._slider.value = replay.playback.count - 1.0
	t.check(replay.playback.at_end(), "dragging the timeline moves the pitch")
	t.check(replay._board["score"].text == final_text, "the score at the end is the final score")
	t.check(replay.clock_text(replay.playback.playhead).begins_with("90"), "the clock ends at 90'")
	replay.jump_to(sub_sample)
	t.check(not replay._paused, "a jump plays on")
	t.check(replay.playback.playhead < sub_sample and replay.playback.playhead > sub_sample - 20,
			"a jump lands a few seconds before the event")
	# highlights in the replay: only the passages are played
	var passages: Array = replay._replay["passages"]
	t.check(not passages.is_empty() and replay._mode_button.visible, "the replay has passages")
	replay.playback.seek(0.0)
	replay.toggle_highlights()
	for i in 5:
		await t.process_frame
	var at: float = replay.playback.time_s()
	t.check(at >= passages[0][0] - 0.01 and at <= passages[0][1], "it starts at the first passage")
	replay.playback.seek(passages[0][1] * 2.0 + 2.0)
	for i in 5:
		await t.process_frame
	if passages.size() > 1:
		t.check(replay.playback.time_s() >= passages[1][0] - 0.01, "and goes on to the next one")
	replay.toggle_highlights()
	await main.go_back()
	var returned: bool = await _wait(t, func(): return (main.current_name == "match_day"
			and main.current._ended), 30.0)
	t.check(returned, "Voltar comes back to full time")
	day = main.current
	t.check(day._continue_button.visible, "and Continuar is still there")
	day._done()
	var moved: bool = await _wait(t, func(): return main.current_name in ["home", "selection"])
	t.check(moved, "on to the next stop")
	# and later from the calendar
	await main.show_screen("calendar")
	var calendar = main.current
	var listed := -1
	for i in calendar._list.item_count:
		if calendar._list.get_item_metadata(i) is String:
			listed = i
	t.check(listed >= 0, "the played match is marked in the calendar")
	t.check(calendar._replay_button.disabled, "Rever needs a match with a replay selected")
	if listed >= 0:
		calendar._list.select(listed)
		calendar._refresh_replay()
		t.check(not calendar._replay_button.disabled, "Rever is offered for it")
		calendar._watch()
		var opened: bool = await _wait(t, func(): return (main.current_name == "replay"
				and main.current.playback != null and main.current._info != null), 30.0)
		t.check(opened, "the replay opens from the calendar")
		t.check(main.current.match_id != "" and main.current.playback.count > 90 * 60 * 2,
				"with the whole match")
		t.check(main.current._board["home"].text != "", "and the clubs on the scoreboard")
		await main.go_back()
		t.check(main.current_name == "calendar", "Voltar returns to the calendar")


func test_a_role_change_goes_through_the_core(t) -> void:
	await main.show_screen("tactics")
	var screen = main.current
	UI.select_key(screen._slots, 1)
	var before: String = screen._tactic["slots"][1]["ip_role"]
	await screen._cycle_role("ip")
	t.check(screen._tactic["slots"][1]["ip_role"] != before, "the IP role changed")


func test_closing_while_busy_waits_for_the_answer(t) -> void:
	await main.show_screen("home")
	var finished := [false]
	var long_request := func():
		await t.core().request("career.continue")  # a real request; a whole season (positional
		# user matches, spec 008) would outlast the test timeout
		finished[0] = true
	long_request.call()
	await main.close_game()
	t.check(finished[0], "the running request was answered before the core stopped")
	t.check(t.core().state == "closed", "the core is closed")


func test_change_the_mentality(t) -> void:
	main._closing = false
	await t.core().start()
	var reopened: Dictionary = await t.core().request("career.open", {"name": "janela"})
	t.check(reopened.has("result"), "career reopened after closing")
	var before: Dictionary = await t.core().request("tactic.current")
	await main.show_screen("tactics")
	var screen = main.current
	UI.select_key(screen._instructions, "mentality")
	await screen._cycle_instruction()  # kept at once: no Confirmar
	var after: Dictionary = await t.core().request("tactic.current")
	t.check(after["result"]["mentality"] != before["result"]["mentality"], "mentality changed")


func teardown(t) -> void:
	if main != null:
		main.queue_free()
	await t.core().stop()

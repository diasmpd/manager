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
	selection._confirm()
	var shown: bool = await _wait(t, func(): return main.current_name == "match_day")
	if not shown and main.current_name == "selection":  # a no-goalkeeper warning: confirm again
		selection._confirm()
		shown = await _wait(t, func(): return main.current_name == "match_day")
	t.check(shown, "the match day is shown")
	await _wait(t, func(): return main.current._stats != null)
	var day = main.current
	day._set_speed(3)
	var some: bool = await _wait(t, func(): return day._shown > 3, 20.0)
	t.check(some, "the feed advances at speed 3")
	day._finish()
	t.check(day._feed.get_parsed_text().length() > 50, "the feed was written")
	t.check(day._stats.visible, "the stats are shown")
	day._done()
	var moved: bool = await _wait(t, func(): return main.current_name in ["home", "selection"])
	t.check(moved, "on to the next stop")


func test_change_the_mentality(t) -> void:
	var before: Dictionary = await t.core().request("tactic.current")
	await main.show_screen("tactics")
	var screen = main.current
	UI.select_key(screen._instructions, "mentality")
	await screen._cycle_instruction()
	screen._confirm()
	await _wait(t, func(): return main.current_name != "tactics")
	var after: Dictionary = await t.core().request("tactic.current")
	t.check(after["result"]["mentality"] != before["result"]["mentality"], "mentality changed")


func teardown(t) -> void:
	if main != null:
		main.queue_free()
	await t.core().stop()

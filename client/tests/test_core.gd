extends RefCounted
## The connection to the core (spec 007 T012, T013), against the real Python server.


func test_version_compatibility(t) -> void:
	var Core = t.core()
	t.check(Core.compatible("1.0"), "1.0 is compatible")
	t.check(Core.compatible("1.7"), "a newer minor is compatible")
	t.check(not Core.compatible("2.0"), "another major is refused")
	t.check(not Core.compatible("garbage"), "nonsense is refused")


func test_a_broken_core_fails_at_once_and_says_why(t) -> void:
	var Core = t.core()
	var broken := OS.get_user_data_dir().path_join("broken_core")
	DirAccess.make_dir_recursive_absolute(broken.path_join("manager_core"))
	var init := FileAccess.open(broken.path_join("manager_core/__init__.py"), FileAccess.WRITE)
	init.store_string("raise ImportError('core quebrado para o teste')\n")
	init.close()
	var previous := OS.get_environment("PYTHONPATH")
	OS.set_environment("PYTHONPATH", broken)
	var started := Time.get_ticks_msec()
	var ok: bool = await Core.start()
	var elapsed := Time.get_ticks_msec() - started
	OS.set_environment("PYTHONPATH", previous)
	t.check(not ok and Core.state == "failed", "a broken core fails")
	t.check(elapsed < 15000, "fails at once, not after the 30 s hello timeout (%d ms)" % elapsed)
	t.check(Core.failure.contains("core quebrado para o teste"), "says why: " + Core.failure)


func test_start_and_hello(t) -> void:
	var Core = t.core()
	var ok: bool = await Core.start()
	t.check(ok, "core started: " + Core.failure)
	t.check(Core.state == "ready", "state is ready")
	t.check(Core.t("ui.continue") == "Continuar", "strings arrived")
	t.check(Core.t("ui.home.position", {"place": 3}).contains("3º"), "placeholders")


func test_answers_and_errors(t) -> void:
	var Core = t.core()
	var listing: Dictionary = await Core.request("career.list")
	t.check(listing.has("result") and listing["result"] is Array, "career.list answers")
	var unknown: Dictionary = await Core.request("no.such.method")
	t.check(unknown.has("error") and unknown["error"]["code"] == "P002", "unknown method error")
	var no_career: Dictionary = await Core.request("career.status")
	t.check(no_career.get("error", {}).get("code") == "P004", "no open career")


func test_a_career_round_trip(t) -> void:
	var Core = t.core()
	var created: Dictionary = await Core.request("career.new", {"name": "godot", "club_id": "alvorada"})
	t.check(created.has("result"), "career.new: " + str(created.get("error")))
	var progressed := []
	var on_progress := func(p): progressed.append(p)
	Core.progress.connect(on_progress)
	var stop: Dictionary = await Core.request("career.continue")
	Core.progress.disconnect(on_progress)
	t.check(stop.get("result", {}).get("kind") in ["user_match", "event", "season_end"], "continue stops")
	var home: Dictionary = await Core.request("view.home")
	t.check(home.get("result", {}).get("status", {}).get("club_name", "") != "", "home view")


func teardown(t) -> void:
	var Core = t.core()
	await Core.stop()
	t.check(Core.state == "closed", "core closed")

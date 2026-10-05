extends RefCounted
## The connection to the core (spec 007 T012, T013), against the real Python server.


func test_version_compatibility(t) -> void:
	var Core = t.core()
	t.check(Core.compatible("1.0"), "1.0 is compatible")
	t.check(Core.compatible("1.7"), "a newer minor is compatible")
	t.check(not Core.compatible("2.0"), "another major is refused")
	t.check(not Core.compatible("garbage"), "nonsense is refused")


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

extends SceneTree
## Headless test runner for the desktop client (spec 007 T013); no add-on needed.
##   godot --headless --path client -s res://tests/run_tests.gd
## Each suite is a script with `test_*` methods taking the runner; they may await.

const TEST_TIMEOUT_MS := 120000
const SUITES := ["res://tests/test_core.gd", "res://tests/test_screens.gd"]

var failures: Array[String] = []
var _current := ""


func _initialize() -> void:
	# never the owner's saves: an empty scratch folder unless MANAGER_SAVES says otherwise
	if OS.get_environment("MANAGER_SAVES") == "":
		var scratch := OS.get_user_data_dir().path_join("test-saves")
		if DirAccess.dir_exists_absolute(scratch):
			for file in DirAccess.get_files_at(scratch):
				DirAccess.remove_absolute(scratch.path_join(file))
		DirAccess.make_dir_recursive_absolute(scratch)
		OS.set_environment("MANAGER_SAVES", scratch)
	_run.call_deferred()


func check(condition: bool, message: String) -> void:
	if not condition:
		failures.append("%s: %s" % [_current, message])


func core() -> Node:
	return root.get_node("/root/Core")


func _run() -> void:
	var count := 0
	for path in SUITES:
		if not ResourceLoader.exists(path):
			continue
		var script = load(path)
		if script == null or not script.can_instantiate():
			failures.append("%s: the suite does not compile" % path)
			continue
		var suite = script.new()
		for method in suite.get_method_list():
			var name: String = method["name"]
			if not name.begins_with("test_"):
				continue
			count += 1
			_current = path.get_file() + "::" + name
			var before := failures.size()
			var finished := [false]
			var run_one := func():
				await suite.call(name, self)
				finished[0] = true
			run_one.call()
			var deadline := Time.get_ticks_msec() + TEST_TIMEOUT_MS
			while not finished[0] and Time.get_ticks_msec() < deadline:
				await process_frame
			if not finished[0]:
				failures.append("%s: timed out after %d s" % [_current, TEST_TIMEOUT_MS / 1000])
			print(("FAIL " if failures.size() > before else "ok   ") + _current)
		if suite.has_method("teardown"):
			await suite.teardown(self)
	for failure in failures:
		printerr(failure)
	print("%d tests, %d failures" % [count, failures.size()])
	quit(1 if failures.size() > 0 else 0)

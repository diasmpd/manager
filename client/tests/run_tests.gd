extends SceneTree
## Headless test runner for the desktop client (spec 007 T013); no add-on needed.
##   godot --headless --path client -s res://tests/run_tests.gd
## Each suite is a script with `test_*` methods taking the runner; they may await.

const SUITES := ["res://tests/test_core.gd", "res://tests/test_screens.gd"]

var failures: Array[String] = []
var _current := ""


func _initialize() -> void:
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
		var suite = load(path).new()
		for method in suite.get_method_list():
			var name: String = method["name"]
			if not name.begins_with("test_"):
				continue
			count += 1
			_current = path.get_file() + "::" + name
			var before := failures.size()
			await suite.call(name, self)
			print(("FAIL " if failures.size() > before else "ok   ") + _current)
		if suite.has_method("teardown"):
			await suite.teardown(self)
	for failure in failures:
		printerr(failure)
	print("%d tests, %d failures" % [count, failures.size()])
	quit(1 if failures.size() > 0 else 0)

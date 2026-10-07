extends SceneTree
## Screenshots of every screen, for checking the layout by eye (not a test). Needs a real window:
##   godot --path client -s res://tests/screenshots.gd -- <output dir>
## Set MANAGER_SAVES to a scratch folder: it creates a career there.

const SCREENS := ["home", "squad", "tables", "calendar", "news", "tactics", "selection"]

var out_dir := ""
var main: Node


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_dir = args[0] if args.size() > 0 else OS.get_user_data_dir()
	_run.call_deferred()


func _wait(condition: Callable, seconds := 60.0) -> bool:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000)
	while Time.get_ticks_msec() < deadline:
		if condition.call():
			return true
		await process_frame
	return condition.call()


func _shot(name: String) -> void:
	for i in 10:  # let containers settle and the frame draw
		await process_frame
	var image := root.get_viewport().get_texture().get_image()
	var path := out_dir.path_join(name + ".png")
	image.save_png(path)
	print("saved ", path)


func _run() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	await _wait(func(): return main.current_name == "careers" and main.current.get_child_count() > 2)
	var careers = main.current
	await _wait(func(): return careers._clubs != null and careers._clubs.item_count > 0)
	await _shot("careers")
	careers._name.text = "tela-%d" % Time.get_ticks_msec()
	careers._clubs.select(0)
	careers._create()
	await _wait(func(): return main.current_name == "home" and main.current.get_child_count() > 2)
	for name in SCREENS:
		await main.show_screen(name)
		await _shot(name)
	var answer: Dictionary = await root.get_node("/root/Core").request("view.squad")
	await main.show_screen("player", {"player_id": answer["result"][0]["player_id"]})
	await _shot("player")
	quit(0)

extends VBoxContainer

const UI := preload("res://scenes/ui.gd")
## Base for the content screens. `main` is the window (main.gd); `open()` asks the core and
## draws; `back()` returns true when the screen handled Esc itself.

var main: Node


func _init() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", UI.GAP)


func open() -> void:
	pass


func back() -> bool:
	return false


func clear() -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()


## Ask the core; on an error, show its message and return null. A screen the owner has already
## left (navigation removes it while it may still be loading) stops quietly: null, no message.
func ask(method: String, params: Dictionary = {}) -> Variant:
	if not is_inside_tree():
		return null
	var core = get_node("/root/Core")
	var answer: Dictionary = await core.request(method, params)
	if not is_inside_tree():
		return null
	if answer.has("error"):
		main.message(UI.error_text(answer))
		return null
	return answer["result"]

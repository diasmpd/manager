extends Control
## The 2D pitch (spec 008b): draws a playback from above. Discs in the clubs' kit colours with
## shirt numbers, the ball, cards, and a flash for goals and substitutions. It draws what the
## playback holds and decides nothing.

signal slot_picked(slot: int)

const UI := preload("res://scenes/ui.gd")
const GRASS := Color("1f6b3a")
const GRASS_DARK := Color("1b6034")
const CHALK := Color(1, 1, 1, 0.75)
const STRIPES := 14
const FLASH_S := 4.0

var playback: RefCounted
var selected := -1


func _init() -> void:
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	custom_minimum_size = Vector2(420, 272)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(event: InputEvent) -> void:
	if playback == null or not (event is InputEventMouseButton and event.pressed
			and event.button_index == MOUSE_BUTTON_LEFT):
		return
	var rect: Rect2 = playback.fit(size)
	if rect.size.x <= 0:
		return
	var cm: Vector2 = (event.position - rect.position) / rect.size \
			* Vector2(playback.length_cm, playback.width_cm)
	selected = playback.slot_near(cm, 250.0)
	slot_picked.emit(selected)
	queue_redraw()


func _draw() -> void:
	if playback == null:
		return
	var rect: Rect2 = playback.fit(size)
	if rect.size.x <= 0:
		return
	_draw_pitch(rect)
	var radius := clampf(rect.size.y / 38.0, 7.0, 15.0)
	var cards: Dictionary = playback.cards()
	var came_on: Dictionary = playback.recent(["sub"], FLASH_S)
	var font := UI.font(UI.CONDENSED_BOLD)
	var font_size := int(radius * 1.25)
	for slot in playback.SLOTS:
		var where = playback.position(slot)
		if where == null:
			continue
		var at: Vector2 = playback.to_screen(where, rect)
		var who: Dictionary = playback.player(slot)
		var kit: Dictionary = playback.sides[playback.side_of(slot)]["kit"]
		var shirt := Color(kit["keeper"] if who.get("keeper", false) else kit["shirt"])
		var ink := UI.on_color(shirt) if who.get("keeper", false) else Color(kit["number"])
		if slot == selected or who.get("player_id", "") == came_on.get("other_id", "-"):
			draw_circle(at, radius + 4.0, Color(1, 1, 1, 0.9))
		draw_circle(at, radius + 1.5, Color(0, 0, 0, 0.55))
		draw_circle(at, radius, shirt)
		var text := str(int(who.get("number", 0)))
		var text_size := font.get_string_size(text, HORIZONTAL_ALIGNMENT_CENTER, -1, font_size)
		draw_string(font, at + Vector2(-text_size.x / 2.0, font_size * 0.36), text,
				HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, ink)
		var card: String = cards.get(who.get("player_id", ""), "")
		if card != "":
			var card_rect := Rect2(at + Vector2(radius * 0.6, -radius * 1.5),
					Vector2(radius * 0.6, radius * 0.85))
			draw_rect(card_rect, Color("ffd400") if card == "yellow" else Color("e3202b"))
	var ball = playback.ball()
	if ball != null:
		var ball_at: Vector2 = playback.to_screen(ball, rect)
		draw_circle(ball_at, radius * 0.45 + 1.0, Color.BLACK)
		draw_circle(ball_at, radius * 0.45, Color.WHITE)
	var goal: Dictionary = playback.recent(playback.GOAL_KINDS, FLASH_S)
	if not goal.is_empty():
		var word := UI.t("ui.pitch.goal")
		var size_px := int(rect.size.y / 6.0)
		var word_size := font.get_string_size(word, HORIZONTAL_ALIGNMENT_CENTER, -1, size_px)
		var origin := rect.get_center() + Vector2(-word_size.x / 2.0, size_px * 0.35)
		draw_string_outline(font, origin, word, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 8,
				Color(0, 0, 0, 0.8))
		draw_string(font, origin, word, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, UI.LED)


func _draw_pitch(rect: Rect2) -> void:
	var stripe := rect.size.x / STRIPES
	for i in STRIPES:
		draw_rect(Rect2(rect.position + Vector2(stripe * i, 0), Vector2(stripe + 1.0, rect.size.y)),
				GRASS if i % 2 == 0 else GRASS_DARK)
	var m := rect.size.x / 105.0  # pixels per metre
	var w := maxf(1.5, m * 0.14)
	var centre := rect.get_center()
	draw_rect(rect, CHALK, false, w)
	draw_line(Vector2(centre.x, rect.position.y), Vector2(centre.x, rect.end.y), CHALK, w)
	draw_arc(centre, 9.15 * m, 0.0, TAU, 64, CHALK, w)
	draw_circle(centre, w * 1.5, CHALK)
	for left in [true, false]:
		var goal_x := rect.position.x if left else rect.end.x
		var inward := 1.0 if left else -1.0
		_box(goal_x, inward, 16.5 * m, 40.32 * m, centre.y, w)
		_box(goal_x, inward, 5.5 * m, 18.32 * m, centre.y, w)
		_box(goal_x, -inward, 2.0 * m, 7.32 * m, centre.y, w)  # the goal, behind the line
		var spot := Vector2(goal_x + inward * 11.0 * m, centre.y)
		draw_circle(spot, w * 1.5, CHALK)
		var reach := acos(5.5 / 9.15)  # the arc outside the penalty area
		var facing := 0.0 if left else PI
		draw_arc(spot, 9.15 * m, facing - reach, facing + reach, 24, CHALK, w)


func _box(goal_x: float, inward: float, depth: float, width: float, centre_y: float,
		w: float) -> void:
	var x := goal_x if inward > 0 else goal_x - depth
	draw_rect(Rect2(Vector2(x, centre_y - width / 2.0), Vector2(depth, width)), CHALK, false, w)

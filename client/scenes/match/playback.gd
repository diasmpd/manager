extends RefCounted
## Playback of a positional record (spec 008b): the samples received so far, a playhead, and what
## is on the pitch at the playhead. It only reads and interpolates what the core recorded
## (contract 1.4 `frames`); no football is decided here. No nodes: the pitch control draws it.

const WIDTH := 47  # values in a sample: the ball (x, y, z), then 22 (x, y), in centimetres
const SLOTS := 22
const OFF := -1
const BALL_JUMP_CM := 2000.0  # farther than a shot flies between two samples: a restart, no slide
const GOAL_KINDS := ["goal", "own_goal", "penalty_goal"]

var hz := 2.0
var length_cm := 10500.0
var width_cm := 6800.0
var count := 0  # samples received
var playhead := 0.0  # the moment on screen, in samples
var events: Array = []  # {sample, kind, side, player_id, other_id, score}, in order
var subs: Array = []  # {sample, slot, player_id, name, number}
var shots: Array = []  # {sample, slot, on_target}
var sides := {}  # "home" / "away" -> the pitch description's side

var _data := PackedByteArray()  # the samples as they came: little-endian int16
var _starters := {}  # slot -> the pitch description's player


func setup(pitch: Dictionary) -> void:
	hz = float(pitch["hz"])
	length_cm = float(pitch["length_cm"])
	width_cm = float(pitch["width_cm"])
	sides = {"home": pitch["home"], "away": pitch["away"]}
	_starters = {}
	for side in ["home", "away"]:
		for p in pitch[side]["players"]:
			_starters[int(p["slot"])] = p


## Add a chunk. One that starts later than what is held is refused (false): the caller asks again
## from `count`. An overlap is cut, so asking twice for the same samples is harmless.
func add(frames: Dictionary) -> bool:
	var first := int(frames["first"])
	if first > count:
		return false
	var raw := Marshalls.base64_to_raw(frames["samples"])
	var skip := count - first  # samples already held
	var incoming := int(frames["count"])
	if skip < incoming:
		_data.append_array(raw.slice(skip * WIDTH * 2))
	var before := count
	count = maxi(count, first + incoming)
	for pair in [[events, "events"], [subs, "subs"], [shots, "shots"]]:
		for mark in frames[pair[1]]:
			if int(mark["sample"]) >= before:
				pair[0].append(mark)
	return true


## Move the playhead by `delta_s` of real time at `speed` (1 = real time), never past the last
## sample held.
func advance(delta_s: float, speed: float) -> void:
	seek(playhead + delta_s * speed * hz)


func seek(sample: float) -> void:
	playhead = clampf(sample, 0.0, maxf(0.0, count - 1.0))


func time_s() -> float:
	return playhead / hz


## Match seconds held ahead of the playhead.
func buffered_s() -> float:
	return maxf(0.0, count - 1.0 - playhead) / hz


func at_end() -> bool:
	return count > 0 and playhead >= count - 1.0


func _value(sample: int, index: int) -> int:
	return _data.decode_s16((sample * WIDTH + index) * 2)


func _point(sample: int, index: int) -> Vector2:
	return Vector2(_value(sample, index), _value(sample, index + 1))


func _on(sample: int, slot: int) -> bool:
	return _value(sample, 3 + 2 * slot) != OFF or _value(sample, 4 + 2 * slot) != OFF


func _replaced_at(sample: int, slot: int) -> bool:
	for sub in subs:
		if int(sub["sample"]) == sample and int(sub["slot"]) == slot:
			return true
	return false


## The ball at the playhead, in centimetres (null before the first sample).
func ball() -> Variant:
	if count == 0:
		return null
	var i := int(playhead)
	var a := _point(i, 0)
	if i + 1 >= count:
		return a
	var b := _point(i + 1, 0)
	if a.distance_to(b) > BALL_JUMP_CM:
		return a
	return a.lerp(b, playhead - i)


## A slot's player at the playhead, in centimetres, or null when nobody is on the pitch in it.
## Between two samples the position is interpolated, except across a substitution or an exit:
## a disc appears and disappears, it never slides in from elsewhere.
func position(slot: int) -> Variant:
	if count == 0:
		return null
	var i := int(playhead)
	if not _on(i, slot):
		return null
	var a := _point(i, 3 + 2 * slot)
	if i + 1 >= count or not _on(i + 1, slot) or _replaced_at(i + 1, slot):
		return a
	return a.lerp(_point(i + 1, 3 + 2 * slot), playhead - i)


## Who is in a slot at the playhead: the starter, or the last substitute to come on in it.
func player(slot: int) -> Dictionary:
	var who: Dictionary = _starters.get(slot, {})
	var i := int(playhead)
	for sub in subs:
		if int(sub["slot"]) == slot and int(sub["sample"]) <= i:
			who = {"slot": slot, "player_id": sub["player_id"], "name": sub["name"],
					"number": sub["number"], "keeper": who.get("keeper", false)}
	return who


func side_of(slot: int) -> String:
	return "home" if slot < SLOTS / 2 else "away"


## The score at the playhead.
func score() -> Array:
	var result := [0, 0]
	var i := int(playhead)
	for event in events:
		if int(event["sample"]) > i:
			break
		if event["kind"] in GOAL_KINDS:
			result = event["score"]
	return result


## Cards shown at the playhead: player id -> "yellow" or "red".
func cards() -> Dictionary:
	var result := {}
	var i := int(playhead)
	for event in events:
		if int(event["sample"]) > i:
			break
		if event["kind"] == "yellow":
			result[event["player_id"]] = "yellow"
		elif event["kind"] in ["red", "second_yellow"]:
			result[event["player_id"]] = "red"
	return result


## The events whose sample lies in (from, to]: what happened while the playhead moved.
func events_between(from: float, to: float) -> Array:
	var result := []
	for event in events:
		var sample := int(event["sample"])
		if sample > from and sample <= to:
			result.append(event)
	return result


## The latest event of one of `kinds` at or before the playhead and at most `within_s` old, or
## an empty dictionary: what the pitch flashes (a goal, a card, a substitution).
func recent(kinds: Array, within_s: float) -> Dictionary:
	var i := int(playhead)
	var found := {}
	for event in events:
		var sample := int(event["sample"])
		if sample > i:
			break
		if event["kind"] in kinds and (i - sample) / hz <= within_s:
			found = event
	return found


## The largest rectangle with the pitch's proportions inside `size`, centred, with a margin.
func fit(size: Vector2, margin := 12.0) -> Rect2:
	var room := size - Vector2(margin, margin) * 2.0
	var scale := minf(room.x / length_cm, room.y / width_cm)
	var area := Vector2(length_cm, width_cm) * maxf(scale, 0.0)
	return Rect2((size - area) / 2.0, area)


## A point of the pitch (centimetres) on the screen.
func to_screen(cm: Vector2, rect: Rect2) -> Vector2:
	return rect.position + Vector2(cm.x / length_cm, cm.y / width_cm) * rect.size


## The slot whose disc is nearest to a pitch point and within `reach_cm` of it, or -1.
func slot_near(cm: Vector2, reach_cm: float) -> int:
	var best := -1
	var best_distance := reach_cm
	for slot in SLOTS:
		var where = position(slot)
		if where != null and cm.distance_to(where) <= best_distance:
			best = slot
			best_distance = cm.distance_to(where)
	return best

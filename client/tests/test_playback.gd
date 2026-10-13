extends RefCounted
## The 2D view's playback (spec 008b FR-022): chunks, the playhead, interpolation, discs that
## appear and disappear, marks and the mapping to the screen. No core and no window needed.

const Playback := preload("res://scenes/match/playback.gd")


func _pitch() -> Dictionary:
	var sides := {}
	for side in ["home", "away"]:
		var first := 0 if side == "home" else 11
		var players := []
		for i in 11:
			players.append({"slot": first + i, "player_id": "%s%d" % [side, i],
					"name": "%s %d" % [side, i], "number": i + 1, "keeper": i == 0})
		sides[side] = {"club_id": side, "name": side, "players": players, "bench": [],
				"kit": {"shirt": "#C8102E", "number": "#FFFFFF", "keeper": "#FF7A00"}}
	return {"length_cm": 10500, "width_cm": 6800, "hz": 2.0, "home": sides["home"],
			"away": sides["away"]}


## One sample: the ball, then every slot at (100 * slot, y); `off` slots are not on the pitch.
func _sample(ball: Vector2, y: int, off: Array = []) -> Array:
	var values := [int(ball.x), int(ball.y), 0]
	for slot in 22:
		values.append_array([-1, -1] if slot in off else [100 * slot, y])
	return values


func _frames(first: int, samples: Array, events: Array = [], subs: Array = []) -> Dictionary:
	var raw := PackedByteArray()
	raw.resize(samples.size() * 47 * 2)
	var at := 0
	for sample in samples:
		for value in sample:
			raw.encode_s16(at, value)
			at += 2
	return {"first": first, "count": samples.size(), "samples": Marshalls.raw_to_base64(raw),
			"events": events, "subs": subs, "shots": []}


func _new() -> RefCounted:
	var playback = Playback.new()
	playback.setup(_pitch())
	return playback


func test_positions_are_read_and_interpolated(t) -> void:
	var p = _new()
	t.check(p.ball() == null and p.position(3) == null, "nothing before the first sample")
	t.check(p.add(_frames(0, [_sample(Vector2(0, 0), 1000), _sample(Vector2(400, 200), 2000)])),
			"the first chunk is taken")
	t.check(p.count == 2, "two samples held")
	t.check(p.position(3) == Vector2(300, 1000), "slot 3 at its first sample")
	p.seek(0.5)
	t.check(p.position(3) == Vector2(300, 1500), "halfway between two samples")
	t.check(p.ball() == Vector2(200, 100), "the ball too")
	p.seek(9.0)
	t.check(p.playhead == 1.0 and p.at_end(), "the playhead stops at the last sample")
	t.check(p.position(21) == Vector2(2100, 2000), "the last slot at the last sample")


func test_the_playhead_follows_the_speed_and_the_buffer(t) -> void:
	var p = _new()
	var samples := []
	for i in 21:
		samples.append(_sample(Vector2(i, 0), 0))
	p.add(_frames(0, samples))
	t.check(is_equal_approx(p.buffered_s(), 10.0), "ten seconds held")
	p.advance(1.0, 1.0)
	t.check(is_equal_approx(p.time_s(), 1.0), "one second at real time")
	p.advance(1.0, 4.0)
	t.check(is_equal_approx(p.time_s(), 5.0), "four more at 4x")
	t.check(is_equal_approx(p.buffered_s(), 5.0), "five left")
	p.advance(60.0, 8.0)
	t.check(p.at_end() and is_equal_approx(p.buffered_s(), 0.0), "never past what is held")


func test_chunks_add_up_overlap_is_cut_and_a_gap_is_refused(t) -> void:
	var p = _new()
	p.add(_frames(0, [_sample(Vector2.ZERO, 1), _sample(Vector2.ZERO, 2)]))
	t.check(not p.add(_frames(5, [_sample(Vector2.ZERO, 9)])), "a chunk after a gap is refused")
	t.check(p.count == 2, "and nothing was added")
	var goal := {"sample": 2, "kind": "goal", "side": "home", "player_id": "home9",
			"other_id": null, "score": [1, 0]}
	var old := {"sample": 1, "kind": "yellow", "side": "away", "player_id": "away4",
			"other_id": null, "score": [0, 0]}
	t.check(p.add(_frames(1, [_sample(Vector2.ZERO, 2), _sample(Vector2.ZERO, 3)], [old, goal])),
			"an overlapping chunk is taken")
	t.check(p.count == 3, "three samples, the repeated one once")
	p.seek(2.0)
	t.check(p.position(0) == Vector2(0, 3), "the new sample is the third")
	t.check(p.events.size() == 1 and p.events[0]["kind"] == "goal",
			"a mark of a sample already held is not added twice")


func test_a_player_off_the_pitch_has_no_disc_and_never_slides(t) -> void:
	var p = _new()
	p.add(_frames(0, [_sample(Vector2.ZERO, 1000), _sample(Vector2.ZERO, 2000, [5]),
			_sample(Vector2.ZERO, 3000, [5]), _sample(Vector2.ZERO, 4000)]))
	p.seek(0.5)
	t.check(p.position(5) == Vector2(500, 1000), "leaving: he stays put, then disappears")
	p.seek(1.5)
	t.check(p.position(5) == null, "off the pitch: no disc")
	p.seek(2.5)
	t.check(p.position(5) == null, "coming on: no disc until his first sample")
	p.seek(3.0)
	t.check(p.position(5) == Vector2(500, 4000), "then he is there")


func test_a_substitution_swaps_the_player_without_a_slide(t) -> void:
	var p = _new()
	var sub := {"sample": 1, "slot": 14, "player_id": "novo", "name": "Novo", "number": 17}
	var samples := [_sample(Vector2.ZERO, 1000), _sample(Vector2.ZERO, 5000),
			_sample(Vector2.ZERO, 5200)]
	p.add(_frames(0, samples, [], [sub]))
	p.seek(0.9)
	t.check(p.position(14) == Vector2(1400, 1000), "the outgoing player does not slide away")
	t.check(p.player(14)["player_id"] == "away3", "still the starter")
	p.seek(1.0)
	t.check(p.player(14)["player_id"] == "novo" and p.player(14)["number"] == 17,
			"the substitute has the slot")
	t.check(p.position(14) == Vector2(1400, 5000), "at his own position")
	p.seek(1.5)
	t.check(p.position(14) == Vector2(1400, 5100), "and moves normally afterwards")
	t.check(p.side_of(14) == "away" and p.side_of(10) == "home", "slots 11-21 are the away side")


func test_the_ball_does_not_slide_across_a_restart(t) -> void:
	var p = _new()
	p.add(_frames(0, [_sample(Vector2(10400, 3400), 0), _sample(Vector2(5250, 3400), 0)]))
	p.seek(0.5)
	t.check(p.ball() == Vector2(10400, 3400), "from the goal to the centre spot: a jump")


func test_the_score_cards_and_recent_events_follow_the_playhead(t) -> void:
	var p = _new()
	var samples := []
	for i in 41:
		samples.append(_sample(Vector2.ZERO, 0))
	var events := [
		{"sample": 4, "kind": "yellow", "side": "away", "player_id": "away4", "other_id": null,
				"score": [0, 0]},
		{"sample": 10, "kind": "goal", "side": "home", "player_id": "home9", "other_id": null,
				"score": [1, 0]},
		{"sample": 30, "kind": "second_yellow", "side": "away", "player_id": "away4",
				"other_id": null, "score": [1, 0]},
	]
	p.add(_frames(0, samples, events))
	p.seek(9.9)
	t.check(p.score() == [0, 0], "no goal before its sample")
	t.check(p.cards() == {"away4": "yellow"}, "the booking shows")
	t.check(p.recent(["goal"], 4.0).is_empty(), "no flash before the goal")
	p.seek(10.0)
	t.check(p.score() == [1, 0], "the goal counts at its sample")
	t.check(p.recent(["goal"], 4.0).get("player_id", "") == "home9", "and flashes")
	p.seek(20.0)
	t.check(p.recent(["goal"], 4.0).is_empty(), "the flash ends")
	t.check(p.events_between(9.0, 10.0).size() == 1 and p.events_between(10.0, 29.0).is_empty(),
			"events between two playheads: after the first, up to the second")
	p.seek(40.0)
	t.check(p.cards() == {"away4": "red"}, "the second yellow is a red")


func test_the_pitch_keeps_its_proportions_on_any_screen(t) -> void:
	var p = _new()
	for size in [Vector2(1280, 400), Vector2(500, 900), Vector2(840, 544)]:
		var rect: Rect2 = p.fit(size, 0.0)
		t.check(is_equal_approx(rect.size.x / rect.size.y, 105.0 / 68.0), "105 x 68 at %s" % size)
		t.check(rect.position.x >= -0.01 and rect.position.y >= -0.01
				and rect.end.x <= size.x + 0.01 and rect.end.y <= size.y + 0.01, "inside %s" % size)
		t.check(p.to_screen(Vector2.ZERO, rect).is_equal_approx(rect.position), "a corner")
		t.check(p.to_screen(Vector2(10500, 6800), rect).is_equal_approx(rect.end), "the far corner")
		t.check(p.to_screen(Vector2(5250, 3400), rect).is_equal_approx(rect.get_center()),
				"the centre spot")


func test_a_click_finds_the_nearest_disc(t) -> void:
	var p = _new()
	p.add(_frames(0, [_sample(Vector2.ZERO, 1000, [7])]))
	t.check(p.slot_near(Vector2(620, 1100), 250.0) == 6, "the disc within reach")
	t.check(p.slot_near(Vector2(700, 1000), 60.0) == -1, "nobody: slot 7 is off the pitch")
	t.check(p.slot_near(Vector2(5000, 6000), 250.0) == -1, "nobody near")

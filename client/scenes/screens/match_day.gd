extends "res://scenes/screen.gd"
## Match day (spec 007 US1): the live feed at the chosen speed (1 slow ... 4 instant), then the
## stats. Continuar goes on to the next stop.

const SPEEDS := {1: 0.8, 2: 0.3, 3: 0.05}  # seconds per feed line; 4 = instant

var match_id := ""
var next_stop: Dictionary = {}
var _feed: RichTextLabel
var _stats: Tree
var _score: Label
var _lines: Array = []
var _shown := 0
var _speed := 2
var _timer: Timer


func open() -> void:
	clear()
	var data = await ask("view.match", {"match_id": match_id})
	if data == null:
		return
	var m: Dictionary = data["match"]
	_lines = data["feed"]
	add_child(UI.title(UI.t("ui.match.title")))
	_score = UI.label("%s  0 x 0  %s" % [m["home_name"], m["away_name"]], 24, true)
	add_child(_score)
	var speed_buttons := UI.row([UI.label(UI.t("ui.desktop.speed"))])
	for s in [1, 2, 3, 4]:
		speed_buttons.add_child(UI.button(str(s), _set_speed.bind(s)))
	speed_buttons.add_child(UI.button(UI.t("ui.desktop.skip"), _finish))
	speed_buttons.add_child(UI.spacer())
	speed_buttons.add_child(UI.button(UI.t("ui.continue"), _done))
	add_child(speed_buttons)
	_feed = RichTextLabel.new()
	_feed.bbcode_enabled = true
	_feed.scroll_following = true
	_feed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(_feed)
	_stats = UI.table(["", m["home_name"], m["away_name"]])
	_stats.custom_minimum_size.y = 250
	_stats.visible = false
	add_child(_stats)
	var rows := []
	for row in data["stats"]:
		rows.append(row)
	UI.fill(_stats, rows)
	_timer = Timer.new()
	_timer.timeout.connect(_tick)
	add_child(_timer)
	_set_speed(_speed)


func _set_speed(speed: int) -> void:
	_speed = speed
	if speed == 4:
		_finish()
		return
	_timer.wait_time = SPEEDS[speed]
	if _shown < _lines.size():
		_timer.start()


func _tick() -> void:
	if _shown >= _lines.size():
		_timer.stop()
		_stats.visible = true
		return
	_show_line(_lines[_shown])
	_shown += 1


func _show_line(line: Dictionary) -> void:
	var minute: Dictionary = line["minute"]
	var stamp := "%d'" % minute["base"]
	if minute["added"] > 0:
		stamp = "%d+%d'" % [minute["base"], minute["added"]]
	var important: bool = line["kind"] in ["goal", "penalty_goal", "own_goal", "red", "second_yellow",
			"full_time"]
	var text := "[b]%s[/b]  %s" % [stamp, line["text"]]
	_feed.append_text(("[color=#ffd970]%s[/color]" % text if important else text) + "\n")
	var score: Array = line["score"]
	var parts := _score.text.split("  ")
	if parts.size() == 3:
		_score.text = "%s  %d x %d  %s" % [parts[0], score[0], score[1], parts[2]]


func _finish() -> void:
	_timer.stop()
	while _shown < _lines.size():
		_show_line(_lines[_shown])
		_shown += 1
	_stats.visible = true


func _done() -> void:
	_finish()
	main.handle_stop(next_stop)  # navigation frees this screen: not awaited


func back() -> bool:
	_done()
	return true

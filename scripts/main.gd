extends Node3D

const PromptAssistantScript = preload("res://scripts/prompt_assistant.gd")
const WeaponFactoryScript = preload("res://scripts/weapon_factory.gd")
const ProjectileScript = preload("res://scripts/projectile.gd")
const TargetDummyScript = preload("res://scripts/target_dummy.gd")
const VoiceBridgeScript = preload("res://scripts/voice_input_bridge.gd")

var _assistant = PromptAssistantScript.new()
var _current_spec: Dictionary = {
	"valid": true,
	"weapon_type": "pistol",
	"theme": "energy",
	"barrels": 1,
	"projectile": "plasma",
	"effect": "none",
	"fire_mode": "semi"
}
var _materials := 12
var _player: CharacterBody3D
var _camera: Camera3D
var _weapon_mount: Node3D
var _weapon: Node3D
var _hud: CanvasLayer
var _prompt_input: LineEdit
var _assistant_label: Label
var _status_label: Label
var _materials_label: Label
var _voice_bridge: Node
var _movement := {"forward": false, "back": false, "left": false, "right": false}
var _fire_cooldown := 0.0

func _ready() -> void:
	_create_world()
	_create_player()
	_create_targets()
	_create_hud()
	_replace_weapon(_current_spec)
	_voice_bridge = VoiceBridgeScript.new()
	add_child(_voice_bridge)
	_voice_bridge.recognized.connect(_on_voice_recognized)
	_voice_bridge.failed.connect(_on_voice_failed)
	_update_materials()

func _physics_process(delta: float) -> void:
	_fire_cooldown = maxf(0.0, _fire_cooldown - delta)
	var move_x := float(Input.is_key_pressed(KEY_D) or _movement["right"]) - float(Input.is_key_pressed(KEY_A) or _movement["left"])
	var move_y := float(Input.is_key_pressed(KEY_S) or _movement["back"]) - float(Input.is_key_pressed(KEY_W) or _movement["forward"])
	var local_move := Vector3(move_x, 0.0, move_y)
	if local_move.length() > 1.0:
		local_move = local_move.normalized()
	var forward := -_player.global_transform.basis.z
	var right := _player.global_transform.basis.x
	var world_move := (right * local_move.x + forward * -local_move.z).normalized()
	_player.velocity.x = world_move.x * 4.2
	_player.velocity.z = world_move.z * 4.2
	if not _player.is_on_floor():
		_player.velocity.y -= 20.0 * delta
	else:
		_player.velocity.y = -0.15
	_player.move_and_slide()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenDrag:
		var screen_width := get_viewport().get_visible_rect().size.x
		if event.position.x > screen_width * 0.38:
			_player.rotate_y(-event.relative.x * 0.004)
			_camera.rotation.x = clampf(_camera.rotation.x - event.relative.y * 0.004, -0.88, 0.88)
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE:
			_fire()
		elif event.keycode == KEY_E:
			_extract_material()

func _create_world() -> void:
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.018, 0.034, 0.060)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.40, 0.53, 0.70)
	environment.ambient_light_energy = 0.68
	environment_node.environment = environment
	add_child(environment_node)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -32, 0)
	sun.light_energy = 1.25
	sun.shadow_enabled = true
	add_child(sun)

	_add_static_box(Vector3(0, -0.35, -3.0), Vector3(28, 0.7, 30), Color(0.075, 0.105, 0.14), 0.25)
	_add_static_box(Vector3(0, 2.0, -17.8), Vector3(28, 4.0, 0.5), Color(0.065, 0.09, 0.13), 0.45)
	_add_static_box(Vector3(-13.8, 2.0, -3.0), Vector3(0.5, 4.0, 30), Color(0.065, 0.09, 0.13), 0.45)
	_add_static_box(Vector3(13.8, 2.0, -3.0), Vector3(0.5, 4.0, 30), Color(0.065, 0.09, 0.13), 0.45)

	for x in range(-10, 11, 2):
		_add_static_box(Vector3(x, 0.32, -8.0), Vector3(0.7, 0.64, 0.7), Color(0.11, 0.16, 0.21), 0.35)

	for x in [-8.0, -4.0, 4.0, 8.0]:
		_add_static_box(Vector3(x, 0.8, -12.0), Vector3(1.3, 1.6, 1.3), Color(0.09, 0.16, 0.22), 0.52)

func _create_player() -> void:
	_player = CharacterBody3D.new()
	_player.name = "Player"
	_player.position = Vector3(0, 0.95, 5.5)
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.32
	capsule.height = 1.8
	var collision := CollisionShape3D.new()
	collision.shape = capsule
	_player.add_child(collision)
	add_child(_player)

	_camera = Camera3D.new()
	_camera.position = Vector3(0, 0.48, 0)
	_camera.fov = 78.0
	_player.add_child(_camera)
	_weapon_mount = Node3D.new()
	_weapon_mount.position = Vector3(0.34, -0.25, -0.36)
	_camera.add_child(_weapon_mount)

func _create_targets() -> void:
	for index in range(3):
		var target = TargetDummyScript.new()
		target.position = Vector3(-3.0 + float(index) * 3.0, 0.85, -8.5)
		target.name = "TrainingTarget_%d" % index
		add_child(target)

func _create_hud() -> void:
	_hud = CanvasLayer.new()
	add_child(_hud)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hud.add_child(root)

	var top_panel := PanelContainer.new()
	top_panel.position = Vector2(14, 12)
	top_panel.size = Vector2(460, 72)
	root.add_child(top_panel)
	var top_box := VBoxContainer.new()
	top_panel.add_child(top_box)
	var title := Label.new()
	title.text = "LAVOICE FORGE ARENA  |  PROTÓTIPO DE COMBATE"
	title.add_theme_color_override("font_color", Color(0.55, 0.86, 1.0))
	top_box.add_child(title)
	_status_label = Label.new()
	_status_label.text = "Colete blocos, descreva uma arma e teste sua criação."
	top_box.add_child(_status_label)
	_materials_label = Label.new()
	top_box.add_child(_materials_label)

	var bottom_panel := PanelContainer.new()
	bottom_panel.anchor_left = 0.0
	bottom_panel.anchor_right = 1.0
	bottom_panel.anchor_top = 1.0
	bottom_panel.anchor_bottom = 1.0
	bottom_panel.offset_left = 14
	bottom_panel.offset_right = -14
	bottom_panel.offset_top = -112
	bottom_panel.offset_bottom = -12
	root.add_child(bottom_panel)
	var bottom_box := VBoxContainer.new()
	bottom_panel.add_child(bottom_box)
	var input_row := HBoxContainer.new()
	bottom_box.add_child(input_row)
	_prompt_input = LineEdit.new()
	_prompt_input.placeholder_text = "Ex.: crie uma pistola de gelo com dois canos que congela inimigos"
	_prompt_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_prompt_input.custom_minimum_size = Vector2(0, 42)
	_prompt_input.text_submitted.connect(_on_prompt_submitted)
	input_row.add_child(_prompt_input)

	var create_button := Button.new()
	create_button.text = "CRIAR"
	create_button.custom_minimum_size = Vector2(86, 42)
	create_button.pressed.connect(_on_create_pressed)
	input_row.add_child(create_button)

	var voice_button := Button.new()
	voice_button.text = "VOZ"
	voice_button.custom_minimum_size = Vector2(70, 42)
	voice_button.pressed.connect(_on_voice_pressed)
	input_row.add_child(voice_button)

	_assistant_label = Label.new()
	_assistant_label.text = "Assistente: descreva uma arma. Também é possível usar o botão de voz."
	_assistant_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bottom_box.add_child(_assistant_label)

	_create_mobile_button(root, "◀", "left")
	_create_mobile_button(root, "▲", "forward")
	_create_mobile_button(root, "▼", "back")
	_create_mobile_button(root, "▶", "right")
	_create_action_button(root, "EXTRAIR", Vector2(-174, -194), Vector2(76, 58), _extract_material)
	_create_action_button(root, "ATIRAR", Vector2(-92, -194), Vector2(76, 58), _fire)

	var crosshair := Label.new()
	crosshair.text = "+"
	crosshair.add_theme_font_size_override("font_size", 24)
	crosshair.add_theme_color_override("font_color", Color(0.7, 0.9, 1.0, 0.85))
	crosshair.set_anchors_preset(Control.PRESET_CENTER)
	crosshair.position = Vector2(-7, -17)
	root.add_child(crosshair)

	root.resized.connect(_layout_action_buttons.bind(root))
	_layout_action_buttons(root)

func _create_mobile_button(root: Control, caption: String, action: String) -> void:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size = Vector2(58, 58)
	root.add_child(button)
	button.button_down.connect(func(): _movement[action] = true)
	button.button_up.connect(func(): _movement[action] = false)
	var positions := {
		"left": Vector2(20, -184),
		"forward": Vector2(82, -246),
		"back": Vector2(82, -122),
		"right": Vector2(144, -184)
	}
	button.set_meta("relative_position", positions[action])

func _create_action_button(root: Control, caption: String, relative_position: Vector2, button_size: Vector2, callback: Callable) -> void:
	var button := Button.new()
	button.text = caption
	button.size = button_size
	button.pressed.connect(callback)
	button.set_meta("relative_position", relative_position)
	root.add_child(button)

func _layout_action_buttons(root: Control) -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	for child in root.get_children():
		if child is Button and child.has_meta("relative_position"):
			var relative_position: Vector2 = child.get_meta("relative_position")
			if relative_position.x < 0.0:
				child.position = viewport_size + relative_position - child.size
			else:
				child.position = Vector2(relative_position.x, viewport_size.y + relative_position.y)

func _on_prompt_submitted(_text: String) -> void:
	_on_create_pressed()

func _on_create_pressed() -> void:
	var spec: Dictionary = _assistant.parse_request(_prompt_input.text)
	_assistant_label.text = _assistant.describe(spec)
	if not spec.get("valid", false):
		_status_label.text = "Pedido incompleto: informe o tipo da arma."
		return

	var cost := 2 + int(spec["barrels"])
	if spec["projectile"] in ["rocket", "grenade"]:
		cost += 2
	if spec["effect"] != "none":
		cost += 1
	if _materials < cost:
		_status_label.text = "Faltam blocos: custo %d, estoque %d. Use EXTRAIR." % [cost, _materials]
		return

	_materials -= cost
	_current_spec = spec
	_replace_weapon(spec)
	_update_materials()
	_status_label.text = "Arma montada! Custo: %d blocos. Teste com ATIRAR." % cost

func _replace_weapon(spec: Dictionary) -> void:
	if is_instance_valid(_weapon):
		_weapon.queue_free()
	_weapon = WeaponFactoryScript.build_weapon(spec)
	_weapon_mount.add_child(_weapon)

func _on_voice_pressed() -> void:
	_assistant_label.text = "Assistente: ouvindo pelo reconhecimento de voz do Android..."
	_voice_bridge.start()

func _on_voice_recognized(text: String) -> void:
	_prompt_input.text = text
	_on_create_pressed()

func _on_voice_failed(message: String) -> void:
	_assistant_label.text = "Assistente: " + message

func _extract_material() -> void:
	_materials = mini(_materials + 2, 99)
	_update_materials()
	_status_label.text = "Extração concluída: +2 blocos."

func _update_materials() -> void:
	_materials_label.text = "BLOCOS DISPONÍVEIS: %d    |    WASD ou controles na tela para mover" % _materials

func _fire() -> void:
	if _fire_cooldown > 0.0:
		return
	_fire_cooldown = 0.22 if _current_spec.get("fire_mode", "semi") == "burst" else 0.34
	var projectile = ProjectileScript.new()
	projectile.direction = -_camera.global_transform.basis.z
	projectile.tint = _theme_color(str(_current_spec.get("theme", "energy")))
	projectile.effect = str(_current_spec.get("effect", "none"))
	add_child(projectile)
	projectile.global_position = _camera.global_position + projectile.direction * 0.85
	_status_label.text = "Disparo: %s | efeito: %s" % [
		str(_current_spec.get("projectile", "plasma")),
		str(_current_spec.get("effect", "none"))
	]

func _theme_color(theme: String) -> Color:
	match theme:
		"ice":
			return Color(0.42, 0.86, 1.0)
		"fire":
			return Color(1.0, 0.32, 0.08)
		"electric":
			return Color(0.72, 0.52, 1.0)
		"toxic":
			return Color(0.35, 0.95, 0.28)
		"laser":
			return Color(1.0, 0.78, 0.20)
		_:
			return Color(0.25, 0.72, 1.0)

func _add_static_box(position: Vector3, size: Vector3, color: Color, metallic: float) -> void:
	var body := StaticBody3D.new()
	body.position = position
	body.collision_layer = 1
	body.collision_mask = 0
	var shape := BoxShape3D.new()
	shape.size = size
	var collision := CollisionShape3D.new()
	collision.shape = shape
	body.add_child(collision)
	var mesh := BoxMesh.new()
	mesh.size = size
	var visual := MeshInstance3D.new()
	visual.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = 0.48
	visual.material_override = material
	body.add_child(visual)
	add_child(body)

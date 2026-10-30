extends Area3D

var direction := Vector3.FORWARD
var tint := Color(0.35, 0.78, 1.0)
var effect := "none"
var speed := 18.0
var damage := 22.0
var lifetime := 2.4

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	monitoring = true

	var shape := SphereShape3D.new()
	shape.radius = 0.12
	var collision := CollisionShape3D.new()
	collision.shape = shape
	add_child(collision)

	var mesh := SphereMesh.new()
	mesh.radius = 0.12
	mesh.height = 0.24
	var visual := MeshInstance3D.new()
	visual.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = tint
	material.emission_enabled = true
	material.emission = tint
	material.emission_energy_multiplier = 2.0
	visual.material_override = material
	add_child(visual)

	body_entered.connect(_on_body_entered)

func _physics_process(delta: float) -> void:
	global_position += direction.normalized() * speed * delta
	lifetime -= delta
	if lifetime <= 0.0:
		queue_free()

func _on_body_entered(body: Node3D) -> void:
	if body.has_method("apply_damage"):
		body.apply_damage(damage, effect)
	queue_free()

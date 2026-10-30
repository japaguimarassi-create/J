extends StaticBody3D

var health := 100.0
var _visual: MeshInstance3D
var _material: StandardMaterial3D

func _ready() -> void:
	collision_layer = 1
	collision_mask = 0

	var shape := CapsuleShape3D.new()
	shape.radius = 0.34
	shape.height = 1.35
	var collision := CollisionShape3D.new()
	collision.shape = shape
	add_child(collision)

	var mesh := CapsuleMesh.new()
	mesh.radius = 0.34
	mesh.height = 1.35
	_visual = MeshInstance3D.new()
	_visual.mesh = mesh
	_material = StandardMaterial3D.new()
	_material.albedo_color = Color(0.18, 0.28, 0.39)
	_material.metallic = 0.62
	_material.roughness = 0.34
	_visual.material_override = _material
	add_child(_visual)

func apply_damage(amount: float, effect: String) -> void:
	health -= amount
	if effect == "freeze":
		_material.albedo_color = Color(0.45, 0.83, 1.0)
	elif effect == "burn":
		_material.albedo_color = Color(1.0, 0.32, 0.12)
	elif effect == "shock":
		_material.albedo_color = Color(0.72, 0.54, 1.0)
	elif effect == "poison":
		_material.albedo_color = Color(0.35, 0.95, 0.28)
	else:
		_material.albedo_color = Color(0.95, 0.55, 0.25)

	if health <= 0.0:
		queue_free()

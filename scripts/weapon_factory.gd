extends RefCounted
class_name WeaponFactory

static func build_weapon(spec: Dictionary) -> Node3D:
	var root := Node3D.new()
	root.name = "GeneratedWeapon"

	var palette := _palette(str(spec.get("theme", "energy")))
	var metal := _material(Color(0.075, 0.095, 0.13), 0.82, Color(0.02, 0.03, 0.05))
	var dark := _material(Color(0.025, 0.035, 0.05), 0.45, Color.BLACK)
	var accent := _material(palette["accent"], 0.48, palette["glow"])
	var bright := _material(palette["bright"], 0.28, palette["glow"])

	var weapon_type := str(spec.get("weapon_type", "pistol"))
	var body_length := 0.84 if weapon_type in ["rifle", "sniper"] else 0.67
	var body_width := 0.52 if weapon_type == "rocket_launcher" else 0.44

	_box(root, "Receiver", Vector3(body_width, 0.19, body_length), Vector3(0, 0, 0.05), metal)
	_box(root, "Upper armor", Vector3(body_width * 0.82, 0.08, body_length * 0.82), Vector3(0, 0.13, 0.02), dark)
	_box(root, "Top rail", Vector3(0.19, 0.045, body_length * 0.58), Vector3(0, 0.19, -0.01), accent)
	_box(root, "Side panel left", Vector3(0.035, 0.105, body_length * 0.45), Vector3(-body_width * 0.51, 0.015, 0.08), accent)
	_box(root, "Side panel right", Vector3(0.035, 0.105, body_length * 0.45), Vector3(body_width * 0.51, 0.015, 0.08), accent)
	_box(root, "Grip", Vector3(0.20, 0.39, 0.24), Vector3(0, -0.27, 0.23), dark, Vector3(-12, 0, 0))
	_box(root, "Grip plate", Vector3(0.215, 0.045, 0.25), Vector3(0, -0.44, 0.23), accent, Vector3(-12, 0, 0))
	_box(root, "Trigger guard", Vector3(0.20, 0.035, 0.16), Vector3(0, -0.16, -0.04), metal)

	var barrel_count := clampi(int(spec.get("barrels", 1)), 1, 6)
	var barrel_radius := 0.075 if weapon_type == "rocket_launcher" else 0.052
	for index in range(barrel_count):
		var offset := (float(index) - float(barrel_count - 1) * 0.5) * 0.13
		_cylinder(root, "Barrel_%d" % index, barrel_radius, 0.64, Vector3(offset, 0.015, -0.60), metal)
		_cylinder(root, "Muzzle_%d" % index, barrel_radius * 1.22, 0.065, Vector3(offset, 0.015, -0.94), accent)
		_cylinder(root, "Bore_%d" % index, barrel_radius * 0.58, 0.068, Vector3(offset, 0.015, -0.978), dark)

	_cylinder(root, "Power cell", 0.085, 0.34, Vector3(body_width * 0.59, 0.015, 0.05), accent)
	_cylinder(root, "Power cell cap", 0.092, 0.045, Vector3(body_width * 0.59, 0.015, -0.14), bright)
	_box(root, "Rear sight", Vector3(0.12, 0.09, 0.09), Vector3(0, 0.25, 0.25), metal)
	_box(root, "Front sight", Vector3(0.09, 0.07, 0.07), Vector3(0, 0.23, -0.42), accent)
	_box(root, "Energy spine", Vector3(0.07, 0.025, body_length * 0.62), Vector3(0, 0.24, -0.01), bright)
	_box(root, "Rear cap", Vector3(body_width * 0.82, 0.15, 0.10), Vector3(0, 0.015, body_length * 0.52), metal)

	return root

static func _palette(theme: String) -> Dictionary:
	match theme:
		"ice":
			return {"accent": Color(0.20, 0.73, 0.98), "bright": Color(0.72, 0.95, 1.0), "glow": Color(0.12, 0.55, 1.0)}
		"fire":
			return {"accent": Color(0.98, 0.27, 0.08), "bright": Color(1.0, 0.70, 0.22), "glow": Color(1.0, 0.20, 0.03)}
		"electric":
			return {"accent": Color(0.55, 0.38, 1.0), "bright": Color(0.86, 0.80, 1.0), "glow": Color(0.48, 0.19, 1.0)}
		"toxic":
			return {"accent": Color(0.27, 0.92, 0.35), "bright": Color(0.75, 1.0, 0.42), "glow": Color(0.12, 0.82, 0.22)}
		"laser":
			return {"accent": Color(1.0, 0.70, 0.16), "bright": Color(1.0, 0.95, 0.62), "glow": Color(1.0, 0.58, 0.06)}
		_:
			return {"accent": Color(0.18, 0.67, 0.95), "bright": Color(0.67, 0.91, 1.0), "glow": Color(0.12, 0.44, 0.95)}

static func _material(color: Color, metalness: float, glow: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metalness
	material.roughness = 0.29
	if glow != Color.BLACK:
		material.emission_enabled = true
		material.emission = glow
		material.emission_energy_multiplier = 1.2
	return material

static func _box(parent: Node3D, part_name: String, size: Vector3, position: Vector3, material: Material, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var instance := MeshInstance3D.new()
	instance.name = part_name
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation_degrees = rotation
	parent.add_child(instance)
	return instance

static func _cylinder(parent: Node3D, part_name: String, radius: float, length: float, position: Vector3, material: Material) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = length
	mesh.radial_segments = 16
	var instance := MeshInstance3D.new()
	instance.name = part_name
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation_degrees = Vector3(90, 0, 0)
	parent.add_child(instance)
	return instance

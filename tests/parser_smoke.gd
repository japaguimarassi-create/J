extends SceneTree

const PromptAssistantScript = preload("res://scripts/prompt_assistant.gd")

func _initialize() -> void:
	var parser = PromptAssistantScript.new()

	var ice = parser.parse_request("Crie uma pistola de gelo com dois canos que dispara rajadas e congela os inimigos")
	assert(ice["valid"])
	assert(ice["weapon_type"] == "pistol")
	assert(ice["theme"] == "ice")
	assert(ice["barrels"] == 2)
	assert(ice["fire_mode"] == "burst")
	assert(ice["effect"] == "freeze")

	var rocket = parser.parse_request("Monte uma bazuca de fogo que dispara tres foguetes explosivos")
	assert(rocket["valid"])
	assert(rocket["weapon_type"] == "rocket_launcher")
	assert(rocket["theme"] == "fire")
	assert(rocket["projectile"] == "rocket")
	assert(rocket["effect"] == "explosion")
	assert(rocket["projectile_count"] == 3)

	var shotgun = parser.parse_request("Crie uma espingarda toxica com quatro canos")
	assert(shotgun["valid"])
	assert(shotgun["weapon_type"] == "shotgun")
	assert(shotgun["theme"] == "toxic")
	assert(shotgun["barrels"] == 4)

	print("PromptAssistant: 3 cenarios aprovados.")
	quit(0)

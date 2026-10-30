extends RefCounted
class_name PromptAssistant

const NUMBER_WORDS = {
	"um": 1,
	"uma": 1,
	"dois": 2,
	"duas": 2,
	"tres": 3,
	"quatro": 4,
	"cinco": 5,
	"seis": 6,
	"sete": 7,
	"oito": 8,
	"nove": 9,
	"dez": 10
}

func parse_request(raw_text: String) -> Dictionary:
	var text := _normalize(raw_text)
	var weapon_type := _weapon_type(text)
	var theme := _theme(text)
	var barrels := _quantity_before_component(text, ["cano", "canos", "boca", "bocas"])
	if barrels <= 0:
		barrels = 2 if weapon_type == "shotgun" else 1
	barrels = clampi(barrels, 1, 6)

	var projectile := _projectile(text, theme)
	var effect := _effect(text, theme)
	var fire_mode := "burst" if _has_any(text, ["rajada", "rajadas", "automatica", "automatico"]) else "spread" if weapon_type == "shotgun" else "semi"
	var projectile_count := _quantity_before_component(text, ["carga", "cargas", "foguete", "foguetes", "missil", "misseis", "tiro", "tiros"])
	if projectile_count <= 0:
		projectile_count = 1

	var target := "enemies" if _has_any(text, ["inimigo", "inimigos", "alvo", "alvos"]) else "world" if _has_any(text, ["bloco", "blocos", "parede", "paredes", "terreno"]) else "default"
	var valid := weapon_type != "unknown"

	return {
		"valid": valid,
		"action": "create",
		"weapon_type": weapon_type,
		"theme": theme,
		"barrels": barrels,
		"projectile": projectile,
		"projectile_count": clampi(projectile_count, 1, 10),
		"effect": effect,
		"fire_mode": fire_mode,
		"target": target,
		"source_text": raw_text.strip_edges(),
		"normalized_text": text
	}

func describe(spec: Dictionary) -> String:
	if not spec.get("valid", false):
		return "Assistente: não identifiquei o objeto principal. Tente especificar uma arma, como pistola, rifle, escopeta ou bazuca."

	var type_names := {
		"pistol": "pistola",
		"rifle": "rifle",
		"shotgun": "escopeta",
		"rocket_launcher": "lançador de foguetes",
		"sniper": "rifle de precisão",
		"cannon": "canhão",
		"blaster": "arma experimental"
	}
	var theme_names := {
		"ice": "gelo",
		"fire": "fogo",
		"electric": "eletricidade",
		"toxic": "energia tóxica",
		"laser": "laser",
		"energy": "energia"
	}
	var effect_names := {
		"freeze": "congelamento",
		"burn": "queimadura",
		"shock": "choque elétrico",
		"explosion": "explosão",
		"poison": "veneno",
		"none": "impacto"
	}
	var projectile_names := {
		"ice_shard": "fragmentos de gelo",
		"fireball": "projéteis de fogo",
		"plasma": "plasma",
		"pigeon": "pombos",
		"grenade": "granadas",
		"rocket": "foguetes",
		"energy_bolt": "raios de energia",
		"toxic_orb": "orbes tóxicos"
	}
	return "Assistente: entendi uma %s de %s, com %d cano(s), disparando %s. Efeito: %s. Vou montar o corpo, a empunhadura, os canos, os detalhes e o sistema de disparo." % [
		type_names.get(spec["weapon_type"], "arma"),
		theme_names.get(spec["theme"], "energia"),
		int(spec["barrels"]),
		projectile_names.get(spec["projectile"], "projéteis"),
		effect_names.get(spec["effect"], "impacto")
	]

func _weapon_type(text: String) -> String:
	if _has_any(text, ["escopeta", "espingarda", "shotgun"]):
		return "shotgun"
	if _has_any(text, ["bazuca", "lanca foguete", "lancador de foguete", "lancador", "rocket launcher"]):
		return "rocket_launcher"
	if _has_any(text, ["sniper", "franco atirador", "rifle de precisao"]):
		return "sniper"
	if _has_any(text, ["rifle", "fuzil", "carabina"]):
		return "rifle"
	if _has_any(text, ["pistola", "revolver", "arma curta"]):
		return "pistol"
	if _has_any(text, ["canhao"]):
		return "cannon"
	if _has_any(text, ["arma", "blaster"]):
		return "blaster"
	return "unknown"

func _theme(text: String) -> String:
	if _has_any(text, ["gelo", "congela", "congelar", "neve", "ice"]):
		return "ice"
	if _has_any(text, ["fogo", "chamas", "flame", "fire", "lava", "incendiar"]):
		return "fire"
	if _has_any(text, ["eletrica", "eletricidade", "raio", "choque", "thunder"]):
		return "electric"
	if _has_any(text, ["veneno", "toxico", "acido", "corrosivo"]):
		return "toxic"
	if _has_any(text, ["laser"]):
		return "laser"
	return "energy"

func _projectile(text: String, theme: String) -> String:
	if _has_any(text, ["pombo", "pombos", "pomba", "pombas"]):
		return "pigeon"
	if _has_any(text, ["granada", "granadas", "bomba", "bombas"]):
		return "grenade"
	if _has_any(text, ["foguete", "foguetes", "missil", "misseis", "rocket"]):
		return "rocket"
	match theme:
		"ice":
			return "ice_shard"
		"fire":
			return "fireball"
		"toxic":
			return "toxic_orb"
		"laser":
			return "energy_bolt"
		_:
			return "plasma"

func _effect(text: String, theme: String) -> String:
	if _has_any(text, ["congela", "congelar", "congelamento", "congelante"]):
		return "freeze"
	if _has_any(text, ["explosivo", "explosiva", "explodir", "explosao"]):
		return "explosion"
	if _has_any(text, ["queima", "queimar", "incendiar", "chamas"]):
		return "burn"
	if _has_any(text, ["eletrico", "eletrica", "choque", "eletrocutar"]):
		return "shock"
	if _has_any(text, ["veneno", "envenenar", "toxico"]):
		return "poison"
	if theme == "ice":
		return "freeze"
	if theme == "fire":
		return "burn"
	if theme == "electric":
		return "shock"
	if theme == "toxic":
		return "poison"
	return "none"

func _quantity_before_component(text: String, nouns: Array) -> int:
	var words := text.split(" ", false)
	for index in range(1, words.size()):
		var current := words[index].trim_suffix("s")
		if nouns.has(words[index]) or nouns.has(current):
			var previous := words[index - 1]
			if previous.is_valid_int():
				return int(previous)
			if NUMBER_WORDS.has(previous):
				return int(NUMBER_WORDS[previous])
	return 0

func _has_any(text: String, terms: Array) -> bool:
	for term in terms:
		if text.contains(str(term)):
			return true
	return false

func _normalize(value: String) -> String:
	var result := value.to_lower().strip_edges()
	var pairs := [
		["á", "a"], ["à", "a"], ["â", "a"], ["ã", "a"], ["ä", "a"],
		["é", "e"], ["ê", "e"], ["è", "e"], ["ë", "e"],
		["í", "i"], ["î", "i"], ["ì", "i"],
		["ó", "o"], ["ô", "o"], ["õ", "o"], ["ò", "o"],
		["ú", "u"], ["ü", "u"], ["ù", "u"], ["ç", "c"]
	]
	for pair in pairs:
		result = result.replace(pair[0], pair[1])
	var punctuation := RegEx.new()
	punctuation.compile("[^a-z0-9 ]")
	result = punctuation.sub(result, " ", true)
	var spaces := RegEx.new()
	spaces.compile("\\s+")
	result = spaces.sub(result, " ", true)
	return result.strip_edges()

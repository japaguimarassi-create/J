extends Node

signal recognized(text: String)
signal failed(message: String)

const PLUGIN_NAME := "VoiceInputAndroid"
var _plugin: Object

func _ready() -> void:
	if OS.get_name() == "Android" and Engine.has_singleton(PLUGIN_NAME):
		_plugin = Engine.get_singleton(PLUGIN_NAME)
		if _plugin.has_signal("speech_result"):
			_plugin.connect("speech_result", Callable(self, "_on_speech_result"))
		if _plugin.has_signal("speech_error"):
			_plugin.connect("speech_error", Callable(self, "_on_speech_error"))

func start() -> void:
	if _plugin == null:
		failed.emit("Reconhecimento nativo indisponível. Use o ditado por voz do teclado ou digite o pedido.")
		return
	_plugin.startRecognition()

func _on_speech_result(text: String) -> void:
	if text.strip_edges().is_empty():
		failed.emit("Nenhuma frase foi reconhecida.")
		return
	recognized.emit(text)

func _on_speech_error(code: int) -> void:
	failed.emit("O reconhecimento de voz não foi concluído (código %d)." % code)

@tool
extends EditorPlugin

var export_plugin: AndroidVoiceExportPlugin

func _enter_tree() -> void:
	export_plugin = AndroidVoiceExportPlugin.new()
	add_export_plugin(export_plugin)

func _exit_tree() -> void:
	if export_plugin != null:
		remove_export_plugin(export_plugin)
		export_plugin = null

class AndroidVoiceExportPlugin extends EditorExportPlugin:
	var plugin_name := "VoiceInputAndroid"

	func _supports_platform(platform: EditorExportPlatform) -> bool:
		return platform is EditorExportPlatformAndroid

	func _get_android_libraries(_platform: EditorExportPlatform, debug: bool) -> PackedStringArray:
		if debug:
			return PackedStringArray([plugin_name + "/bin/debug/" + plugin_name + "-debug.aar"])
		return PackedStringArray([plugin_name + "/bin/release/" + plugin_name + "-release.aar"])

	func _get_android_dependencies(_platform: EditorExportPlatform, _debug: bool) -> PackedStringArray:
		return PackedStringArray()

	func _get_name() -> String:
		return plugin_name

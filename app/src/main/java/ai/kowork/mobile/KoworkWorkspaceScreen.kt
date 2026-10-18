package ai.kowork.mobile

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.ByteArrayOutputStream
import java.io.File

private enum class WorkspaceMode(val label: String) {
    EDITOR("Código"),
    TERMINAL("Terminal"),
    SYSTEMS("Android + Linux + Windows")
}

private data class CodeTemplate(
    val label: String,
    val filePath: String,
    val source: String
)

private val workspaceTemplates = listOf(
    CodeTemplate(
        "Luau",
        "ServerScriptService/Main.server.lua",
        "local Players = game:GetService(\"Players\")\n\nPlayers.PlayerAdded:Connect(function(player)\n    print((\"Welcome, %s\"):format(player.Name))\nend)\n"
    ),
    CodeTemplate(
        "Python",
        "main.py",
        "def main():\n    print(\"Kowork workspace ready\")\n\n\nif __name__ == \"__main__\":\n    main()\n"
    ),
    CodeTemplate(
        "JavaScript",
        "main.js",
        "function main() {\n  console.log(\"Kowork workspace ready\");\n}\n\nmain();\n"
    ),
    CodeTemplate(
        "HTML",
        "index.html",
        "<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>Kowork project</title>\n</head>\n<body>\n  <main><h1>Kowork workspace ready</h1></main>\n</body>\n</html>\n"
    ),
    CodeTemplate(
        "Kotlin",
        "Main.kt",
        "fun main() {\n    println(\"Kowork workspace ready\")\n}\n"
    )
)

private const val TERMUX_BOOTSTRAP = "pkg update -y && pkg install -y proot-distro git python nodejs clang make cmake ninja rust && proot-distro install debian && proot-distro login debian -- bash -lc 'apt-get update && apt-get install -y python3 python3-pip python3-venv git nodejs npm build-essential cmake ninja-build pkg-config'"

@Composable
internal fun KoworkWorkspaceScreen(
    initialMode: String,
    onOpenBrowser: (String) -> Unit
) {
    val context = LocalContext.current
    val preferences = remember { context.getSharedPreferences("kowork_preferences", Context.MODE_PRIVATE) }
    var mode by remember(initialMode) {
        mutableStateOf(WorkspaceMode.values().firstOrNull { it.name == initialMode } ?: WorkspaceMode.EDITOR)
    }
    var projectName by remember { mutableStateOf("RobloxProject") }
    var filePath by remember { mutableStateOf(workspaceTemplates.first().filePath) }
    var source by remember { mutableStateOf(workspaceTemplates.first().source) }
    var status by remember { mutableStateOf("Projeto local; nenhum arquivo é executado automaticamente.") }
    var terminalCommand by remember { mutableStateOf("help") }
    var remoteUrl by remember { mutableStateOf(preferences.getString("windows_remote_url", "") ?: "") }
    var terminalOutput by remember {
        mutableStateOf(
            listOf(
                "Kowork Safe Terminal",
                "Os comandos daqui são diagnósticos; o shell Linux real fica no Termux após sua instalação e confirmação."
            )
        )
    }
    LaunchedEffect(mode) {
        preferences.edit().putString("workspace_mode", mode.name).apply()
    }
    var exportContents by remember { mutableStateOf("") }
    var exportName by remember { mutableStateOf("Main.server.lua") }

    val exportFile = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("text/plain")
    ) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.openOutputStream(uri)?.use {
                    it.write(exportContents.toByteArray(Charsets.UTF_8))
                } ?: throw IllegalStateException("Não foi possível gravar no destino escolhido.")
                status = "Arquivo exportado pelo seletor do Android."
            }.onFailure {
                status = "Falha ao exportar: " + (it.message ?: "erro desconhecido")
            }
        }
    }
    val importFile = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            runCatching {
                val bytes = context.contentResolver.openInputStream(uri)?.use { stream ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(8192)
                    var total = 0
                    while (true) {
                        val count = stream.read(buffer)
                        if (count < 0) break
                        total += count
                        if (total > 2 * 1024 * 1024) throw IllegalArgumentException("O arquivo excede 2 MiB.")
                        output.write(buffer, 0, count)
                    }
                    output.toByteArray()
                } ?: throw IllegalStateException("Não foi possível abrir o arquivo.")
                source = String(bytes, Charsets.UTF_8)
                filePath = uri.lastPathSegment?.substringAfterLast('/')?.substringAfterLast(':')
                    ?.replace(Regex("[^A-Za-z0-9._-]"), "_")
                    ?.ifBlank { "imported.txt" } ?: "imported.txt"
                status = "Conteúdo importado para o editor; salve no projeto para mantê-lo."
            }.onFailure {
                status = "Falha ao importar: " + (it.message ?: "erro desconhecido")
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("Workspace", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text(
            "Android é o host. Linux usa userland PRoot pelo Termux. Windows completo funciona remotamente; o app não finge que executa o Windows ou o Roblox Studio nativamente no Android.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
            WorkspaceMode.values().forEach { item ->
                val action: () -> Unit = { mode = item }
                if (mode == item) {
                    Button(onClick = action, modifier = Modifier.weight(1f)) {
                        Text(item.label, fontSize = 10.sp)
                    }
                } else {
                    OutlinedButton(onClick = action, modifier = Modifier.weight(1f)) {
                        Text(item.label, fontSize = 10.sp)
                    }
                }
            }
        }
        when (mode) {
            WorkspaceMode.EDITOR -> {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.fillMaxWidth()) {
                    workspaceTemplates.forEach { template ->
                        OutlinedButton(
                            onClick = {
                                filePath = template.filePath
                                source = template.source
                                status = "Modelo de " + template.label + " selecionado."
                            },
                            modifier = Modifier.weight(1f)
                        ) { Text(template.label, fontSize = 10.sp) }
                    }
                }
                BasicTextField(
                    value = projectName,
                    onValueChange = { projectName = it.take(48) },
                    modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface, RoundedCornerShape(8.dp)).padding(10.dp),
                    textStyle = TextStyle(color = MaterialTheme.colorScheme.onSurface, fontSize = 13.sp),
                    singleLine = true,
                    decorationBox = { inner ->
                        if (projectName.isEmpty()) Text("Nome do projeto", fontSize = 12.sp)
                        inner()
                    }
                )
                BasicTextField(
                    value = filePath,
                    onValueChange = { filePath = it.take(180) },
                    modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface, RoundedCornerShape(8.dp)).padding(10.dp),
                    textStyle = TextStyle(color = MaterialTheme.colorScheme.onSurface, fontSize = 12.sp),
                    singleLine = true,
                    decorationBox = { inner ->
                        if (filePath.isEmpty()) Text("Caminho do arquivo, ex. ServerScriptService/Main.server.lua", fontSize = 11.sp)
                        inner()
                    }
                )
                BasicTextField(
                    value = source,
                    onValueChange = { source = it },
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .background(ColorTokens.editorBackground, RoundedCornerShape(10.dp))
                        .padding(12.dp),
                    textStyle = TextStyle(
                        color = ColorTokens.editorText,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace
                    ),
                    decorationBox = { inner ->
                        Column {
                            Text("Editor de código", color = ColorTokens.editorAccent, fontSize = 10.sp)
                            Spacer(Modifier.height(6.dp))
                            inner()
                        }
                    }
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                    Button(
                        onClick = {
                            runCatching {
                                val saved = saveWorkspaceFile(context, projectName, filePath, source)
                                status = "Salvo localmente: " + saved.relativeTo(File(context.filesDir, "kowork-workspace")).path
                            }.onFailure {
                                status = "Falha ao salvar: " + (it.message ?: "caminho inválido")
                            }
                        },
                        modifier = Modifier.weight(1f)
                    ) { Text("Salvar local") }
                    OutlinedButton(
                        onClick = {
                            exportContents = source
                            exportName = filePath.substringAfterLast('/').ifBlank { "code.txt" }
                            exportFile.launch(exportName)
                        },
                        modifier = Modifier.weight(1f)
                    ) { Text("Exportar") }
                    OutlinedButton(
                        onClick = { importFile.launch(arrayOf("*/*")) },
                        modifier = Modifier.weight(1f)
                    ) { Text("Importar") }
                }
                Text(
                    "O editor guarda no diretório privado do app. Exportar usa o seletor Android para escolher onde salvar.",
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            WorkspaceMode.TERMINAL -> {
                Card(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = ColorTokens.editorBackground)
                ) {
                    Column(
                        modifier = Modifier.fillMaxSize().padding(10.dp).verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        terminalOutput.forEach { line ->
                            Text(line, fontSize = 11.sp, color = ColorTokens.terminalText, fontFamily = FontFamily.Monospace)
                        }
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    BasicTextField(
                        value = terminalCommand,
                        onValueChange = { terminalCommand = it },
                        modifier = Modifier.weight(1f).background(MaterialTheme.colorScheme.surface, RoundedCornerShape(8.dp)).padding(10.dp),
                        textStyle = TextStyle(color = MaterialTheme.colorScheme.onSurface, fontSize = 12.sp, fontFamily = FontFamily.Monospace),
                        singleLine = true
                    )
                    Button(onClick = {
                        val output = safeWorkspaceCommand(terminalCommand, context)
                        terminalOutput = (terminalOutput + listOf("$ " + terminalCommand, output)).takeLast(120)
                    }) { Text("Run") }
                }
                Button(
                    onClick = { openTermux(context, onStatus = { status = it }) },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Abrir Linux no Termux") }
            }
            WorkspaceMode.SYSTEMS -> {
                Column(
                    modifier = Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(9.dp)
                ) {
                    SystemCard(
                        "ANDROID · HOST",
                        "O aplicativo roda nativamente no Android. Os arquivos deste workspace ficam no armazenamento privado; a permissão de overlay e notificações é pedida explicitamente pelo sistema."
                    )
                    SystemCard(
                        "LINUX · LOCAL",
                        "Use Termux + PRoot para executar ferramentas Linux sem root. Isso é um userland Linux dentro do Android, não substitui o kernel Android e não equivale a um PC Linux com GPU."
                    )
                    Text("Bootstrap para Termux", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                    Text(
                        TERMUX_BOOTSTRAP,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(
                            onClick = {
                                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                clipboard.setPrimaryClip(ClipData.newPlainText("Kowork Linux bootstrap", TERMUX_BOOTSTRAP))
                                Toast.makeText(context, "Comando copiado. Confira antes de executar no Termux.", Toast.LENGTH_LONG).show()
                            },
                            modifier = Modifier.weight(1f)
                        ) { Text("Copiar comandos") }
                        OutlinedButton(
                            onClick = { openTermux(context, onStatus = { status = it }) },
                            modifier = Modifier.weight(1f)
                        ) { Text("Abrir Termux") }
                    }
                    SystemCard(
                        "WINDOWS · REMOTO",
                        "Windows completo e o Roblox Studio oficial precisam de um ambiente Windows/macOS compatível. O telefone pode controlá-lo por uma sessão remota; essa máquina precisa existir e estar ligada, local ou na nuvem. O app não instala nem simula uma máquina Windows rápida neste aparelho."
                    )
                    BasicTextField(
                        value = remoteUrl,
                        onValueChange = { remoteUrl = it.take(2048) },
                        modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface, RoundedCornerShape(8.dp)).padding(10.dp),
                        textStyle = TextStyle(color = MaterialTheme.colorScheme.onSurface, fontSize = 12.sp),
                        singleLine = true,
                        decorationBox = { inner ->
                            if (remoteUrl.isEmpty()) Text("URL do seu Windows remoto via navegador HTTPS", fontSize = 11.sp)
                            inner()
                        }
                    )
                    Button(
                        onClick = {
                            val normalized = KoworkBrowserPolicy.normalizeAddress(remoteUrl)
                            if (normalized == null || !KoworkBrowserPolicy.isHttpsUrl(normalized)) {
                                status = "Use a URL HTTPS do seu próprio serviço de desktop remoto."
                            } else {
                                preferences.edit().putString("windows_remote_url", normalized).apply()
                                onOpenBrowser(normalized)
                                status = "Abrindo o portal remoto; a conexão depende do serviço e das credenciais desse Windows."
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Abrir sessão Windows") }
                    OutlinedButton(
                        onClick = { onOpenBrowser("https://create.roblox.com/docs/studio/setup") },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Roblox Studio · requisitos oficiais") }
                    OutlinedButton(
                        onClick = { onOpenBrowser("https://create.roblox.com/docs/luau") },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Roblox Luau · documentação oficial") }
                    OutlinedButton(
                        onClick = { openExternal(context, "https://support.microsoft.com/pt-br/windows/experience/connectivity-networking/how-to-use-remote-desktop") },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Como conectar a um Windows remoto") }
                }
            }
        }
        Text(status, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SystemCard(title: String, description: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            Text(description, fontSize = 12.sp)
        }
    }
}

private object ColorTokens {
    val editorBackground = androidx.compose.ui.graphics.Color(0xFF080D12)
    val editorText = androidx.compose.ui.graphics.Color(0xFFD7E6F7)
    val editorAccent = androidx.compose.ui.graphics.Color(0xFF77C3FF)
    val terminalText = androidx.compose.ui.graphics.Color(0xFFB7E6C2)
}

private fun safeWorkspaceFile(
    context: Context,
    projectName: String,
    relativePath: String
): File {
    val safeProject = projectName.trim().replace(Regex("[^A-Za-z0-9._-]"), "_")
        .trim('.', '_')
        .take(48)
        .ifBlank { "Project" }
    val relative = relativePath.replace('\\', '/')
    require(relative.isNotBlank() && !relative.startsWith("/") && !relative.contains(":")) {
        "O caminho precisa ser relativo ao projeto."
    }
    val parts = relative.split('/').filter { it.isNotBlank() }
    require(parts.isNotEmpty() && parts.none { it == "." || it == ".." }) {
        "O caminho contém segmentos inválidos."
    }
    val sanitizedParts = parts.map { it.replace(Regex("[^A-Za-z0-9._-]"), "_") }
    val root = File(context.filesDir, "kowork-workspace").canonicalFile
    val project = File(root, safeProject).canonicalFile
    val file = File(project, sanitizedParts.joinToString(File.separator)).canonicalFile
    require(file.path.startsWith(project.path + File.separator)) { "O caminho saiu da pasta do projeto." }
    return file
}

private fun saveWorkspaceFile(
    context: Context,
    projectName: String,
    relativePath: String,
    source: String
): File {
    require(source.toByteArray(Charsets.UTF_8).size <= 2 * 1024 * 1024) { "Arquivo maior que 2 MiB." }
    val file = safeWorkspaceFile(context, projectName, relativePath)
    file.parentFile?.mkdirs()
    file.writeText(source, Charsets.UTF_8)
    return file
}

private fun safeWorkspaceCommand(command: String, context: Context): String {
    return when (command.trim().lowercase()) {
        "help" -> "Comandos: help, status, pwd, languages, projects, browser, studio, windows"
        "status" -> "Android: ativo | Workspace: " + File(context.filesDir, "kowork-workspace").absolutePath
        "pwd" -> File(context.filesDir, "kowork-workspace").absolutePath
        "languages" -> "Luau, Python, JavaScript, HTML, Kotlin. Adicione mais templates conforme o projeto crescer."
        "projects" -> {
            val root = File(context.filesDir, "kowork-workspace")
            root.listFiles()?.filter { it.isDirectory }?.joinToString("\n") { it.name }
                ?.ifBlank { "Nenhum projeto salvo ainda." } ?: "Nenhum projeto salvo ainda."
        }
        "browser" -> "Abra a aba Web para navegar com modo desktop."
        "studio" -> "O Roblox Studio oficial exige Windows ou macOS. Veja a aba Android + Linux + Windows para configurar acesso remoto."
        "windows" -> "O Windows precisa de um host remoto real; a aba de sistemas aceita uma URL HTTPS."
        else -> "Comando bloqueado: o terminal seguro não executa texto arbitrário como shell."
    }
}

private fun openTermux(context: Context, onStatus: (String) -> Unit) {
    val intent = context.packageManager.getLaunchIntentForPackage("com.termux")
    if (intent != null) {
        context.startActivity(intent)
        onStatus("Termux aberto. Revise e execute os comandos copiados manualmente.")
    } else {
        openExternal(context, "https://github.com/termux/termux-app/releases")
        onStatus("Termux não foi encontrado. Abrindo a página oficial de versões.")
    }
}

private fun openExternal(context: Context, url: String) {
    val uri = KoworkBrowserPolicy.normalizeAddress(url) ?: return
    runCatching {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(uri)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }.onFailure {
        Toast.makeText(context, "Não foi possível abrir o endereço.", Toast.LENGTH_SHORT).show()
    }
}

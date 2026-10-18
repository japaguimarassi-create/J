package ai.kowork.mobile

import android.Manifest
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.pm.PackageManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebStorage
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.core.content.ContextCompat
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import org.json.JSONObject
import org.json.JSONTokener
import java.io.File
import java.util.Locale

internal data class KoworkPageContext(
    val title: String,
    val url: String,
    val text: String
)

private data class BrowserViewState(val url: String, val desktopMode: Boolean)

private sealed class KoworkWebPermission {
    data class Media(val request: PermissionRequest, val permissions: List<String>) : KoworkWebPermission()
    data class Geolocation(val origin: String, val callback: GeolocationPermissions.Callback) : KoworkWebPermission()
}

@Composable
internal fun KoworkBrowserScreen(
    initialUrl: String,
    autoSendSearchResults: Boolean,
    onUrlChanged: (String) -> Unit,
    onSendPageContext: (KoworkPageContext) -> Unit
) {
    val context = LocalContext.current
    var address by remember(initialUrl) { mutableStateOf(initialUrl) }
    var targetUrl by remember(initialUrl) { mutableStateOf(initialUrl) }
    var autoHandoffDone by remember(targetUrl) { mutableStateOf(false) }
    var title by remember { mutableStateOf("Navegador Kowork") }
    val browserPrefs = remember { context.getSharedPreferences("kowork_preferences", Context.MODE_PRIVATE) }
    var desktopMode by remember { mutableStateOf(true) }
    var allowThirdPartyCookies by remember { mutableStateOf(browserPrefs.getBoolean("browser_third_party_cookies", false)) }
    var canGoBack by remember { mutableStateOf(false) }
    var canGoForward by remember { mutableStateOf(false) }
    var progressVisible by remember { mutableStateOf(false) }
    var loadError by remember { mutableStateOf("") }
    var originalUserAgent by remember { mutableStateOf<String?>(null) }
    var fileCallback by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    var pendingPermission by remember { mutableStateOf<KoworkWebPermission?>(null) }
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = RequestMultiplePermissions()
    ) { grants ->
        val pending = pendingPermission
        pendingPermission = null
        when (pending) {
            is KoworkWebPermission.Media -> {
                val granted = pending.permissions.all { permission ->
                    grants[permission] == true ||
                        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
                }
                runCatching {
                    if (granted) pending.request.grant(pending.request.resources) else pending.request.deny()
                }
            }
            is KoworkWebPermission.Geolocation -> {
                val fine = grants[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                val coarse = grants[Manifest.permission.ACCESS_COARSE_LOCATION] == true ||
                    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
                runCatching { pending.callback.invoke(pending.origin, fine || coarse, false) }
            }
            null -> Unit
        }
    }
    val latestPageContext by rememberUpdatedState(onSendPageContext)
    val latestUrlChanged by rememberUpdatedState(onUrlChanged)
    val webViewHolder = remember { arrayOfNulls<WebView>(1) }
    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        fileCallback?.onReceiveValue(uri?.let { arrayOf(it) })
        fileCallback = null
    }

    DisposableEffect(Unit) {
        onDispose {
            webViewHolder[0]?.let { view ->
                runCatching { view.stopLoading() }
                runCatching { view.destroy() }
            }
            webViewHolder[0] = null
        }
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("Navegador de desktop", fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Text(
            "A página abre pela internet real no WebView. Sites com bloqueio a navegadores embutidos podem exigir abrir no navegador externo.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            BasicTextField(
                value = address,
                onValueChange = { address = it },
                modifier = Modifier
                    .weight(1f)
                    .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(10.dp))
                    .padding(horizontal = 10.dp, vertical = 12.dp),
                textStyle = androidx.compose.ui.text.TextStyle(
                    color = MaterialTheme.colorScheme.onSurface,
                    fontSize = 12.sp
                ),
                singleLine = true,
                decorationBox = { inner ->
                    if (address.isEmpty()) Text("https://site.com", fontSize = 12.sp)
                    inner()
                }
            )
            Button(onClick = {
                val uri = KoworkBrowserPolicy.normalizeAddress(address)
                if (uri == null) {
                    loadError = "Endereço inválido. Use um endereço HTTP ou HTTPS."
                } else {
                    loadError = ""
                    targetUrl = uri
                    address = uri
                }
            }) { Text("Ir") }
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            OutlinedButton(
                enabled = canGoBack,
                onClick = { webViewHolder[0]?.goBack() }
            ) { Text("‹") }
            OutlinedButton(
                enabled = canGoForward,
                onClick = { webViewHolder[0]?.goForward() }
            ) { Text("›") }
            OutlinedButton(onClick = { webViewHolder[0]?.reload() }) { Text("Recarregar") }
            Spacer(Modifier.weight(1f))
            Text("PC", fontSize = 12.sp)
            Switch(
                checked = desktopMode,
                onCheckedChange = { desktopMode = it }
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Cookies de terceiros", fontSize = 12.sp, fontWeight = FontWeight.Medium)
                Text("Alguns sites precisam disso para entrar; fica desligado por padrão.", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(
                checked = allowThirdPartyCookies,
                onCheckedChange = {
                    allowThirdPartyCookies = it
                    browserPrefs.edit().putBoolean("browser_third_party_cookies", it).apply()
                    webViewHolder[0]?.let { view ->
                        CookieManager.getInstance().setAcceptThirdPartyCookies(view, it)
                    }
                }
            )
            OutlinedButton(onClick = {
                AlertDialog.Builder(context)
                    .setTitle("Limpar dados do navegador?")
                    .setMessage("Isso apaga cache, cookies e dados de sites do Kowork. Não apaga os arquivos do workspace nem o modelo local.")
                    .setPositiveButton("Limpar") { _, _ ->
                        webViewHolder[0]?.clearCache(true)
                        WebStorage.getInstance().deleteAllData()
                        CookieManager.getInstance().removeAllCookies {
                            CookieManager.getInstance().flush()
                            Toast.makeText(context, "Dados do navegador apagados.", Toast.LENGTH_SHORT).show()
                        }
                    }
                    .setNegativeButton("Cancelar", null)
                    .show()
            }) { Text("Limpar dados", fontSize = 10.sp) }
        }
        if (loadError.isNotBlank()) {
            Text(loadError, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
        }
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(Modifier.fillMaxWidth().padding(8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title.take(140), fontWeight = FontWeight.SemiBold, fontSize = 12.sp)
                Text(address.take(240), fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (progressVisible) Text("Carregando…", fontSize = 10.sp)
            }
        }
        AndroidView(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(12.dp)),
            factory = { ctx ->
                WebView(ctx).apply {
                    webViewHolder[0] = this
                    layoutParams = ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    )
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.loadsImagesAutomatically = true
                    settings.useWideViewPort = true
                    settings.loadWithOverviewMode = desktopMode
                    settings.setSupportZoom(true)
                    settings.builtInZoomControls = true
                    settings.displayZoomControls = false
                    settings.textZoom = 100
                    settings.allowFileAccess = false
                    settings.allowContentAccess = false
                    settings.allowFileAccessFromFileURLs = false
                    settings.allowUniversalAccessFromFileURLs = false
                    settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                    settings.javaScriptCanOpenWindowsAutomatically = false
                    settings.setSupportMultipleWindows(false)
                    settings.safeBrowsingEnabled = true
                    settings.mediaPlaybackRequiresUserGesture = true
                    originalUserAgent = settings.userAgentString
                    CookieManager.getInstance().setAcceptCookie(true)
                    CookieManager.getInstance().setAcceptThirdPartyCookies(this, allowThirdPartyCookies)
                    if (desktopMode) settings.userAgentString =
                        KoworkBrowserPolicy.desktopUserAgent(settings.userAgentString)
                    tag = BrowserViewState(targetUrl, desktopMode)
                    webViewClient = object : WebViewClient() {
                        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                            val uri = request.url
                            val scheme = uri.scheme?.lowercase(Locale.ROOT)
                            if (scheme == "https" || scheme == "http") return false
                            if ((scheme == "mailto" || scheme == "tel") && request.hasGesture()) {
                                runCatching {
                                    ctx.startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                                }
                            }
                            return true
                        }

                        override fun onPageStarted(view: WebView, url: String, favicon: android.graphics.Bitmap?) {
                            address = url
                            targetUrl = url
                            latestUrlChanged(url)
                            progressVisible = true
                            loadError = ""
                            val state = view.tag as? BrowserViewState
                            view.tag = BrowserViewState(url, state?.desktopMode ?: desktopMode)
                        }

                        override fun onPageFinished(view: WebView, url: String) {
                            address = url
                            canGoBack = view.canGoBack()
                            canGoForward = view.canGoForward()
                            title = view.title ?: url
                            progressVisible = false
                            latestUrlChanged(url)
                            val parsedUrl = runCatching { Uri.parse(url) }.getOrNull()
                            val isSearchResults = parsedUrl?.host == "html.duckduckgo.com" &&
                                parsedUrl.path?.startsWith("/html") == true
                            if (autoSendSearchResults && !autoHandoffDone && isSearchResults) {
                                autoHandoffDone = true
                                val script = "JSON.stringify({title:document.title||'Web search results',url:location.href,text:(Array.from(document.querySelectorAll('.result, .web-result')).slice(0,6).map(function(node){return node.innerText.trim()}).filter(Boolean).join('\\n\\n')||(document.body&&document.body.innerText||'')).slice(0,1800)})"
                                view.evaluateJavascript(script) { encoded ->
                                    val page = decodePageContext(encoded, view.title ?: "Resultados da Web", view.url ?: url)
                                    if (page != null) latestPageContext(page)
                                }
                            }
                        }

                        override fun onReceivedError(
                            view: WebView,
                            request: WebResourceRequest,
                            error: android.webkit.WebResourceError
                        ) {
                            if (request.isForMainFrame) {
                                progressVisible = false
                                loadError = "Não foi possível carregar a página: " + error.description
                            }
                        }
                    }
                    webChromeClient = object : WebChromeClient() {
                        override fun onReceivedTitle(view: WebView, receivedTitle: String?) {
                            if (!receivedTitle.isNullOrBlank()) title = receivedTitle
                        }

                        override fun onProgressChanged(view: WebView, newProgress: Int) {
                            progressVisible = newProgress < 100
                        }

                        override fun onShowFileChooser(
                            webView: WebView,
                            callback: ValueCallback<Array<Uri>>,
                            params: WebChromeClient.FileChooserParams
                        ): Boolean {
                            fileCallback?.onReceiveValue(null)
                            fileCallback = callback
                            return runCatching {
                                filePicker.launch(arrayOf("*/*"))
                                true
                            }.getOrElse {
                                fileCallback = null
                                false
                            }
                        }

                        override fun onPermissionRequest(request: PermissionRequest) {
                            val needed = mutableListOf<String>()
                            var unsupported = false
                            request.resources.forEach { resource ->
                                when (resource) {
                                    PermissionRequest.RESOURCE_AUDIO_CAPTURE -> needed.add(Manifest.permission.RECORD_AUDIO)
                                    PermissionRequest.RESOURCE_VIDEO_CAPTURE -> needed.add(Manifest.permission.CAMERA)
                                    else -> unsupported = true
                                }
                            }
                            if (unsupported || needed.isEmpty() || pendingPermission != null) {
                                request.deny()
                                return
                            }
                            val permissions = needed.distinct()
                            val resourcesText = request.resources.joinToString { resource ->
                                when (resource) {
                                    PermissionRequest.RESOURCE_AUDIO_CAPTURE -> "microfone"
                                    PermissionRequest.RESOURCE_VIDEO_CAPTURE -> "câmera"
                                    else -> "recurso protegido"
                                }
                            }
                            AlertDialog.Builder(ctx)
                                .setTitle("Permissão do site")
                                .setMessage("O site " + (request.origin.host ?: request.origin.toString()) +
                                    " quer usar " + resourcesText + ". Só será liberado após sua confirmação e a permissão do Android.")
                                .setPositiveButton("Continuar") { _, _ ->
                                    pendingPermission = KoworkWebPermission.Media(request, permissions)
                                    val missing = permissions.filter {
                                        ContextCompat.checkSelfPermission(ctx, it) != PackageManager.PERMISSION_GRANTED
                                    }
                                    if (missing.isEmpty()) {
                                        pendingPermission = null
                                        runCatching { request.grant(request.resources) }
                                    } else {
                                        runCatching { permissionLauncher.launch(missing.toTypedArray()) }
                                            .onFailure {
                                                pendingPermission = null
                                                request.deny()
                                            }
                                    }
                                }
                                .setNegativeButton("Bloquear") { _, _ -> request.deny() }
                                .setOnCancelListener { request.deny() }
                                .show()
                        }

                        override fun onGeolocationPermissionsShowPrompt(
                            origin: String,
                            callback: GeolocationPermissions.Callback
                        ) {
                            if (pendingPermission != null) {
                                callback.invoke(origin, false, false)
                                return
                            }
                            AlertDialog.Builder(ctx)
                                .setTitle("Localização do site")
                                .setMessage("O site " + (Uri.parse(origin).host ?: origin) +
                                    " pediu sua localização. Ela só será compartilhada após sua confirmação.")
                                .setPositiveButton("Continuar") { _, _ ->
                                    pendingPermission = KoworkWebPermission.Geolocation(origin, callback)
                                    val missing = listOf(
                                        Manifest.permission.ACCESS_COARSE_LOCATION,
                                        Manifest.permission.ACCESS_FINE_LOCATION
                                    ).filter {
                                        ContextCompat.checkSelfPermission(ctx, it) != PackageManager.PERMISSION_GRANTED
                                    }
                                    if (missing.isEmpty()) {
                                        pendingPermission = null
                                        callback.invoke(origin, true, false)
                                    } else {
                                        runCatching { permissionLauncher.launch(missing.toTypedArray()) }
                                            .onFailure {
                                                pendingPermission = null
                                                callback.invoke(origin, false, false)
                                            }
                                    }
                                }
                                .setNegativeButton("Bloquear") { _, _ -> callback.invoke(origin, false, false) }
                                .setOnCancelListener { callback.invoke(origin, false, false) }
                                .show()
                        }
                    }
                    setDownloadListener(DownloadListener { url, userAgent, contentDisposition, mimeType, contentLength ->
                        if (KoworkBrowserPolicy.isWebUrl(url)) {
                            val name = URLUtil.guessFileName(url, contentDisposition, mimeType)
                                .replace(Regex("[^A-Za-z0-9._-]"), "_")
                                .take(120)
                                .ifBlank { "kowork-download" }
                            runCatching {
                                val manager = ctx.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
                                val request = DownloadManager.Request(Uri.parse(url))
                                    .setTitle(name)
                                    .setMimeType(mimeType)
                                    .setDescription("Download solicitado no Navegador Kowork")
                                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
                                request.addRequestHeader("User-Agent", userAgent)
                                manager.enqueue(request)
                                Toast.makeText(ctx, "Download iniciado: " + name, Toast.LENGTH_SHORT).show()
                            }.onFailure {
                                Toast.makeText(ctx, "Falha ao iniciar o download.", Toast.LENGTH_SHORT).show()
                            }
                        }
                    })
                    loadUrl(targetUrl)
                }
            },
            update = { webView ->
                CookieManager.getInstance().setAcceptThirdPartyCookies(webView, allowThirdPartyCookies)
                val state = webView.tag as? BrowserViewState
                if (state == null || state.desktopMode != desktopMode) {
                    val liveUrl = webView.url ?: targetUrl
                    val baseAgent = originalUserAgent ?: webView.settings.userAgentString
                    webView.settings.userAgentString = if (desktopMode) {
                        KoworkBrowserPolicy.desktopUserAgent(baseAgent)
                    } else {
                        baseAgent
                    }
                    webView.settings.useWideViewPort = true
                    webView.settings.loadWithOverviewMode = desktopMode
                    webView.settings.setSupportZoom(true)
                    webView.settings.builtInZoomControls = true
                    webView.settings.displayZoomControls = false
                    webView.tag = BrowserViewState(liveUrl, desktopMode)
                    webView.reload()
                }
                val nextState = webView.tag as? BrowserViewState
                if (nextState?.url != targetUrl) {
                    webView.tag = BrowserViewState(targetUrl, desktopMode)
                    webView.loadUrl(targetUrl)
                }
            }
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                modifier = Modifier.weight(1f),
                onClick = {
                    val view = webViewHolder[0]
                    if (view == null) {
                        loadError = "O navegador ainda está iniciando."
                    } else {
                        val script = "JSON.stringify({title:document.title||'',url:location.href,text:(document.body&&document.body.innerText||'').slice(0,2200)})"
                        view.evaluateJavascript(script) { encoded ->
                            val page = decodePageContext(encoded, view.title ?: "Página web", view.url ?: targetUrl)
                            if (page == null) {
                                loadError = "Não consegui decodificar o texto desta página. Você ainda pode abrir o site no navegador externo."
                            } else {
                                latestPageContext(page)
                            }
                        }
                    }
                }
            ) { Text("Enviar página ao chat") }
            OutlinedButton(onClick = {
                val normalized = KoworkBrowserPolicy.normalizeAddress(address)
                if (normalized != null) runCatching {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(normalized)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }.onFailure {
                    Toast.makeText(context, "Nenhum navegador externo disponível.", Toast.LENGTH_SHORT).show()
                }
            }) { Text("Externo") }
        }
    }
}


private fun decodePageContext(encoded: String, fallbackTitle: String, fallbackUrl: String): KoworkPageContext? {
    val value = runCatching { JSONTokener(encoded).nextValue() }.getOrNull()
    val json = when (value) {
        is JSONObject -> value
        is String -> runCatching { JSONObject(value) }.getOrNull()
        else -> null
    } ?: return null
    val url = json.optString("url", fallbackUrl)
    if (!KoworkBrowserPolicy.isWebUrl(url)) return null
    return KoworkPageContext(
        title = json.optString("title", fallbackTitle).take(180),
        url = url.take(2048),
        text = json.optString("text", "").take(2200)
    )
}


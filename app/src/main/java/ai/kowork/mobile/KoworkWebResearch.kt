package ai.kowork.mobile

import android.net.Uri
import android.text.Html
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

internal data class WebResult(
    val title: String,
    val url: String,
    val snippet: String
)

internal data class WebPage(
    val title: String,
    val url: String,
    val text: String
)

internal object KoworkWebResearch {
    private const val MAX_PAGE_BYTES = 512 * 1024
    private const val MAX_REDIRECTS = 4

    fun search(query: String, limit: Int = 5): List<WebResult> {
        val normalized = query.trim().take(300)
        require(normalized.isNotEmpty()) { "Digite o que deseja pesquisar." }
        val encoded = URLEncoder.encode(normalized, StandardCharsets.UTF_8.name())
        val html = getText("https://html.duckduckgo.com/html/?q=$encoded", "text/html")
        return parseResults(html, limit)
    }

    fun readPage(url: String): WebPage {
        var current = validatePublicUrl(url)
        repeat(MAX_REDIRECTS + 1) { attempt ->
            val connection = URL(current).openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 12000
            connection.setRequestProperty("User-Agent", "KoworkAndroid/0.2 (public web research)")
            connection.setRequestProperty("Accept", "text/html,text/plain;q=0.9")
            try {
                val status = connection.responseCode
                if (status in 300..399) {
                    if (attempt >= MAX_REDIRECTS) throw IllegalStateException("A página excedeu o limite de redirecionamentos.")
                    val location = connection.getHeaderField("Location")
                        ?: throw IllegalStateException("O site retornou um redirecionamento sem destino.")
                    current = validatePublicUrl(URL(URL(current), location).toString())
                    return@repeat
                }
                if (status !in 200..299) throw IllegalStateException("A página respondeu HTTP $status.")
                val type = connection.contentType.orEmpty().lowercase()
                if (!type.contains("text/html") && !type.contains("text/plain") && !type.contains("application/xhtml")) {
                    throw IllegalStateException("O formato desta página não é texto ou HTML.")
                }
                val bytes = connection.inputStream.use { input ->
                    val output = java.io.ByteArrayOutputStream()
                    val buffer = ByteArray(8192)
                    var total = 0
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        if (total > MAX_PAGE_BYTES) throw IllegalStateException("A página excedeu o limite de leitura de 512 KiB.")
                        output.write(buffer, 0, count)
                    }
                    output.toByteArray()
                }
                val charset = Regex("charset=([^; ]+)", RegexOption.IGNORE_CASE)
                    .find(type)?.groupValues?.get(1)?.trim('"', '\'') ?: "utf-8"
                val raw = runCatching { String(bytes, java.nio.charset.Charset.forName(charset)) }
                    .getOrElse { String(bytes, Charsets.UTF_8) }
                val title = Regex("<title\\b[^>]*>(.*?)</title>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
                    .find(raw)?.groupValues?.get(1).orEmpty()
                val text = clean(
                    raw.replace(Regex("<(script|style|noscript|svg)\\b[^>]*>.*?</\\1\\s*>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)), " ")
                        .replace(Regex("<[^>]+>"), " ")
                ).take(12000)
                return WebPage(clean(title).take(180), current, text)
            } finally {
                connection.disconnect()
            }
        }
        throw IllegalStateException("Não foi possível abrir esta página.")
    }

    private fun getText(url: String, expectedType: String): String {
        var current = validatePublicUrl(url)
        repeat(MAX_REDIRECTS + 1) { attempt ->
            val connection = URL(current).openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 12000
            connection.readTimeout = 15000
            connection.setRequestProperty("User-Agent", "KoworkAndroid/0.2 (public web research)")
            connection.setRequestProperty("Accept", expectedType)
            try {
                val status = connection.responseCode
                if (status in 300..399) {
                    if (attempt >= MAX_REDIRECTS) throw IllegalStateException("O site excedeu o limite de redirecionamentos.")
                    val location = connection.getHeaderField("Location") ?: throw IllegalStateException("Redirecionamento sem destino.")
                    current = validatePublicUrl(URL(URL(current), location).toString())
                    return@repeat
                }
                if (status !in 200..299) throw IllegalStateException("A pesquisa respondeu HTTP $status.")
                return connection.inputStream.bufferedReader(Charsets.UTF_8).use { reader ->
                    val output = StringBuilder()
                    val buffer = CharArray(8192)
                    while (output.length < 1_200_000) {
                        val count = reader.read(buffer, 0, minOf(buffer.size, 1_200_000 - output.length))
                        if (count < 0) break
                        output.append(buffer, 0, count)
                    }
                    output.toString()
                }
            } finally {
                connection.disconnect()
            }
        }
        throw IllegalStateException("Não foi possível consultar o mecanismo de pesquisa.")
    }

    private fun validatePublicUrl(value: String): String {
        val target = java.net.URI(value).normalize()
        require(target.scheme.equals("https", true) && !target.host.isNullOrBlank()) { "Somente páginas HTTPS são aceitas." }
        require(target.rawUserInfo == null) { "URLs com credenciais não são aceitas." }
        val host = target.host.lowercase().trimEnd('.')
        require(host != "localhost" && !host.endsWith(".localhost") && !host.endsWith(".local")) {
            "Endereços locais não são aceitos."
        }
        val addresses = try {
            InetAddress.getAllByName(host)
        } catch (error: Exception) {
            throw IllegalStateException("Não foi possível resolver o endereço do site.", error)
        }
        require(addresses.isNotEmpty() && addresses.all { isGlobalAddress(it) }) {
            "O site aponta para uma rede local, reservada ou não pública."
        }
        return target.toASCIIString()
    }

    private fun isGlobalAddress(address: InetAddress): Boolean {
        if (address.isAnyLocalAddress || address.isLoopbackAddress || address.isLinkLocalAddress ||
            address.isSiteLocalAddress || address.isMulticastAddress) return false
        val bytes = address.address
        if (bytes.size == 4) {
            val a = bytes[0].toInt() and 255
            val b = bytes[1].toInt() and 255
            if (a == 0 || a == 10 || a == 127 || (a == 100 && b in 64..127) ||
                (a == 169 && b == 254) || (a == 172 && b in 16..31) ||
                (a == 192 && b == 168) || (a >= 224)) return false
        } else if (bytes.size == 16) {
            val first = bytes[0].toInt() and 255
            val second = bytes[1].toInt() and 255
            if ((first and 0xFE) == 0xFC || (first == 0xFE && (second and 0xC0) == 0x80)) return false
        }
        return true
    }

    internal fun parseResults(html: String, limit: Int = 5): List<WebResult> {
        val anchorPattern = Regex("<a\\b([^>]*class=[\\\"'][^\\\"']*result__a[^\\\"']*[\\\"'][^>]*)>(.*?)</a>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
        val snippetPattern = Regex("<(?:a|div|td)[^>]*class=[\\\"'][^\\\"']*result__snippet[^\\\"']*[\\\"'][^>]*>(.*?)</(?:a|div|td)>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
        val anchors = anchorPattern.findAll(html).toList()
        val snippets = snippetPattern.findAll(html).map { clean(it.groupValues[1]) }.toList()
        val output = ArrayList<WebResult>()
        for ((index, match) in anchors.withIndex()) {
            val attributes = match.groupValues[1]
            val href = Regex("href=[\\\"']([^\\\"']+)[\\\"']", RegexOption.IGNORE_CASE).find(attributes)?.groupValues?.get(1) ?: continue
            val url = normalizeResultUrl(href) ?: continue
            val title = clean(match.groupValues[2]).take(180)
            if (title.isBlank()) continue
            output.add(WebResult(title, url, snippets.getOrNull(index).orEmpty().take(600)))
            if (output.size >= limit.coerceIn(1, 10)) break
        }
        return output.distinctBy { it.url }
    }

    fun relevantExcerpt(text: String, query: String, maxChars: Int = 380): String {
        val terms = Regex("[\\p{L}\\p{N}_+#.-]{3,}")
            .findAll(query.lowercase())
            .map { it.value }
            .distinct()
            .take(12)
            .toList()
        val sentences = Regex("(?<=[.!?])\\s+|\\n+")
            .split(text)
            .map { it.trim() }
            .filter { it.isNotBlank() }
        val ranked = sentences.mapIndexed { index, sentence ->
            val lower = sentence.lowercase()
            val score = terms.sumOf { term -> Regex(Regex.escape(term)).findAll(lower).count() }
            Triple(index, sentence, score)
        }
        val best = ranked.filter { it.third > 0 }.sortedByDescending { it.third }.firstOrNull()
        val selected = if (best == null) text.take(maxChars) else {
            val before = ranked.getOrNull(best.first - 1)?.second.orEmpty()
            val after = ranked.getOrNull(best.first + 1)?.second.orEmpty()
            listOf(before, best.second, after).filter { it.isNotBlank() }.joinToString(" ")
        }
        return selected.take(maxChars).trim()
    }

    private fun normalizeResultUrl(value: String): String? {
        val full = if (value.startsWith("//")) "https:$value" else value
        val parsed = runCatching { Uri.parse(full) }.getOrNull() ?: return null
        val candidate = parsed.getQueryParameter("uddg") ?: full
        return runCatching { validatePublicUrl(candidate) }.getOrNull()
    }

    private fun clean(value: String): String =
        Html.fromHtml(value, Html.FROM_HTML_MODE_COMPACT)
            .toString()
            .replace(Regex("\\s+"), " ")
            .trim()
}
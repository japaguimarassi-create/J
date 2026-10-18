package ai.kowork.mobile

import java.net.URI
import java.util.Locale

internal object KoworkBrowserPolicy {
    fun normalizeAddress(input: String): String? {
        val raw = input.trim()
        if (raw.isEmpty() || raw.length > 4096) return null
        val schemeMatch = Regex("^([A-Za-z][A-Za-z0-9+.-]*):").find(raw)
        val explicitScheme = schemeMatch?.groupValues?.getOrNull(1)?.lowercase(Locale.ROOT)
        val hasHttpScheme = explicitScheme == "http" || explicitScheme == "https"
        if ((raw.contains("://") && !hasHttpScheme) ||
            explicitScheme in setOf("javascript", "file", "content", "data", "intent", "ftp", "about", "mailto", "tel", "blob", "chrome")
        ) return null
        val candidate = if (hasHttpScheme) raw else if (raw.startsWith("//")) "https:$raw" else "https://$raw"
        val uri = runCatching { URI(candidate) }.getOrNull() ?: return null
        val scheme = uri.scheme?.lowercase(Locale.ROOT) ?: return null
        val host = uri.host?.takeIf { it.isNotBlank() } ?: return null
        if (scheme != "http" && scheme != "https") return null
        if (uri.userInfo != null || host.contains(" ")) return null
        if (uri.port !in -1..65535) return null
        if (scheme == "https" && uri.port == 80) return null
        return uri.toASCIIString()
    }

    fun desktopUserAgent(currentUserAgent: String): String {
        val chromeVersion = Regex("Chrome/([0-9.]+)")
            .find(currentUserAgent)
            ?.groupValues
            ?.getOrNull(1)
            ?: "131.0.0.0"
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/" + chromeVersion + " Safari/537.36"
    }

    fun isWebUrl(url: String): Boolean {
        val normalized = normalizeAddress(url) ?: return false
        val scheme = runCatching { URI(normalized).scheme }.getOrNull()
        return scheme == "https" || scheme == "http"
    }

    fun isHttpsUrl(url: String): Boolean {
        val normalized = normalizeAddress(url) ?: return false
        return runCatching { URI(normalized).scheme == "https" }.getOrDefault(false)
    }
}

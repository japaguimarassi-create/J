package ai.kowork.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class KoworkBrowserPolicyTest {
    @Test
    fun addsHttpsToDomainWithoutScheme() {
        assertEquals("https://example.com", KoworkBrowserPolicy.normalizeAddress("example.com"))
        assertEquals("https://localhost:3000", KoworkBrowserPolicy.normalizeAddress("localhost:3000"))
    }

    @Test
    fun permitsHttpAndHttpsOnly() {
        assertNotNull(KoworkBrowserPolicy.normalizeAddress("https://example.com/path?q=1"))
        assertNotNull(KoworkBrowserPolicy.normalizeAddress("http://localhost:3000"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("javascript:alert(1)"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("file:///data/local/tmp/test.html"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("content://provider/file"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("ftp://example.com/file"))
    }

    @Test
    fun rejectsCredentialsAndInvalidPorts() {
        assertNull(KoworkBrowserPolicy.normalizeAddress("https://user:pass@example.com"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("https://example.com:70000"))
        assertNull(KoworkBrowserPolicy.normalizeAddress("   "))
        assertNull(KoworkBrowserPolicy.normalizeAddress("x".repeat(5000)))
    }

    @Test
    fun desktopUserAgentIdentifiesWindowsDesktop() {
        val agent = KoworkBrowserPolicy.desktopUserAgent("Mozilla/5.0 Android Chrome/135.0.0.0 Mobile")
        assertTrue(agent.contains("Windows NT 10.0"))
        assertTrue(agent.contains("Chrome/135.0.0.0"))
        assertFalse(agent.contains("Android"))
        assertFalse(agent.contains("Mobile"))
    }

    @Test
    fun browserUrlsAreValidatedBeforeNavigation() {
        assertTrue(KoworkBrowserPolicy.isWebUrl("https://create.roblox.com/docs/luau"))
        assertFalse(KoworkBrowserPolicy.isWebUrl("intent://evil"))
        assertFalse(KoworkBrowserPolicy.isWebUrl("javascript:alert(1)"))
        assertTrue(KoworkBrowserPolicy.isHttpsUrl("https://example.com"))
        assertFalse(KoworkBrowserPolicy.isHttpsUrl("http://example.com"))
    }
}

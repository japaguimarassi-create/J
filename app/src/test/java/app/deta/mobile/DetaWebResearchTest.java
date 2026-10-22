package app.deta.mobile;

import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class DetaWebResearchTest {
    @Test
    public void parsesPublicSearchTitlesSnippetsAndSafeLinks() {
        String html = "<div class=\"result\">"
                + "<a class=\"result__a\" href=\"https://example.org/docs\">Docs &amp; guide</a>"
                + "<a class=\"result__snippet\">A useful public documentation excerpt.</a>"
                + "</div>";
        List<DetaWebResearch.Result> results = DetaWebResearch.parseResults(html);
        assertEquals(1, results.size());
        assertEquals("Docs & guide", results.get(0).title);
        assertEquals("https://example.org/docs", results.get(0).url);
        assertEquals("A useful public documentation excerpt.", results.get(0).snippet);
    }

    @Test
    public void rejectsHttpLocalAndSearchEngineLinks() {
        String html = "<a class=\"result__a\" href=\"http://example.org/insecure\">HTTP</a>"
                + "<a class=\"result__a\" href=\"https://localhost/private\">Local</a>"
                + "<a class=\"result__a\" href=\"https://duckduckgo.com/l/?uddg=x\">Search redirect</a>";
        assertTrue(DetaWebResearch.parseResults(html).isEmpty());
    }

    @Test
    public void decodesDuckDuckGoEncodedPublicHttpsResult() {
        String html = "<a class=\"result__a\" href=\"https://duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.example.org%2Fapi\">API docs</a>"
                + "<div class=\"result__snippet\">Public API documentation for developers.</div>";
        List<DetaWebResearch.Result> results = DetaWebResearch.parseResults(html);
        assertEquals(1, results.size());
        assertEquals("https://docs.example.org/api", results.get(0).url);
    }

    @Test
    public void rejectsBlankSearchQueryBeforeNetworkAccess() throws Exception {
        try {
            DetaWebResearch.research("pesquise na web");
            throw new AssertionError("Empty search query must be rejected.");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("assunto"));
        }
    }
}

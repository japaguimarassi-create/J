package app.deta.mobile;

import org.junit.Test;
import java.util.List;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class WebSearchTest {
    @Test
    public void parsesDuckDuckGoResultsAndUnescapesContent() {
        String document = "<div class=\"result\">"
                + "<a class=\"result__a\" href=\"//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fguide\">"
                + "Guide &amp; more</a>"
                + "<a class=\"result__snippet\">Learn <b>useful</b> things&nbsp;here.</a>"
                + "</div>";
        List<WebSearch.Result> results = WebSearch.parseResults(document);
        assertEquals(1, results.size());
        assertEquals("Guide & more", results.get(0).title);
        assertEquals("https://example.com/guide", results.get(0).url);
        assertEquals("Learn useful things here.", results.get(0).snippet);
    }

    @Test
    public void helpIsAvailableWithoutNetwork() {
        String answer = WebSearch.answer("/ajuda");
        assertTrue(answer.contains("Pesquisar na web pública"));
        assertTrue(answer.contains("não executa o modelo neural"));
    }

    @Test
    public void greetingHasAUsefulLocalResponse() {
        String answer = WebSearch.answer("Olá");
        assertTrue(answer.contains("Sou a Deta"));
        assertTrue(answer.contains("web pública"));
    }

    @Test
    public void rejectsUnsafeOrNonHttpsSearchResultDestinations() {
        String document = "<a class=\"result__a\" href=\"http://example.com/insecure\">No HTTPS</a>"
                + "<a class=\"result__a\" href=\"//duckduckgo.com/l/?uddg=https%3A%2F%2Flocalhost%2Fadmin\">Local</a>";
        assertTrue(WebSearch.parseResults(document).isEmpty());
    }

    @Test
    public void sourceUrlsAreExtractedForResults() {
        String document = "<a class=\"result__a\" href=\"https://example.com/page\">Sample page</a>"
                + "<div class=\"result__snippet\">A sufficiently helpful summary.</div>";
        List<WebSearch.Result> results = WebSearch.parseResults(document);
        assertFalse(results.isEmpty());
        assertEquals("https://example.com/page", results.get(0).url);
        assertEquals("A sufficiently helpful summary.", results.get(0).snippet);
    }
}

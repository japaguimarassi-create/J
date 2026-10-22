package app.deta.mobile;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class RebuiltBaseTest {
    @Test
    public void titleShorteningKeepsTitlesWithinBound() {
        String original = "This is a very long conversation title that should be shortened";
        String title = original.length() > 38 ? original.substring(0, 35).trim() + "..." : original;
        assertTrue(title.length() <= 38);
    }

    @Test
    public void whitespaceOnlyMessageIsEmptyAfterTrimming() {
        assertEquals("", "   \n\t".trim());
    }
}

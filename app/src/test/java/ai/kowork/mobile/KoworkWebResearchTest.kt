package ai.kowork.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class KoworkWebResearchTest {
    @Test
    fun excerptPrioritizesTermsFromTheUserQuestion() {
        val page = "Fruit is sweet. Python classes define reusable behavior. A game loop updates frames."
        val excerpt = KoworkWebResearch.relevantExcerpt(page, "Python classes", 220)
        assertTrue(excerpt.contains("Python classes define reusable behavior"))
        assertTrue(excerpt.length <= 220)
    }

    @Test
    fun excerptHandlesNoMatchingTerm() {
        val page = "First paragraph. Second paragraph."
        assertTrue(KoworkWebResearch.relevantExcerpt(page, "unmatched query", 9).length <= 9)
    }
}

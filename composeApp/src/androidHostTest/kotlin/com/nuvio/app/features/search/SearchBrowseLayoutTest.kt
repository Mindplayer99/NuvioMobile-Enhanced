package com.nuvio.app.features.search

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.StateRestorationTester
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioTheme
import com.nuvio.app.core.ui.NuvioScreen
import com.nuvio.app.core.ui.LocalNuvioBottomNavigationOverlayPadding
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class SearchBrowseLayoutTest {
    @get:Rule val compose = createComposeRule()
    private val history = mutableStateOf((1..10).map { "Query $it" })
    private var selected: String? = null

    @Composable
    private fun Browse(fontScale: Float = 1f) {
        NuvioTheme {
            CompositionLocalProvider(
                LocalDensity provides Density(LocalDensity.current.density, fontScale),
                LocalNuvioBottomNavigationOverlayPadding provides 80.dp,
            ) {
                NuvioScreen(
                    modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).testTag("browse"),
                    horizontalPadding = 0.dp,
                    topPadding = 0.dp,
                ) {
                    searchBrowseHeader(
                        recentSearches = history.value,
                        onSearchPress = { selected = it },
                        onRemoveSearch = { query -> history.value = history.value.filterNot { it == query } },
                    ) {
                        Box(Modifier.fillMaxWidth().height(56.dp).testTag("filters")) {
                            Text("Series · Popular · All Genres", Modifier.padding(16.dp))
                        }
                    }
                    item(key = "first_result") {
                        Text("First result", Modifier.fillMaxWidth().height(160.dp).testTag("first_result"))
                    }
                    items(12) { index ->
                        Text("Result $index", Modifier.fillMaxWidth().height(80.dp))
                    }
                    item(key = "last_result") {
                        Text("Last result", Modifier.fillMaxWidth().height(80.dp).testTag("last_result"))
                    }
                }
            }
        }
    }

    @Test fun historyStartsCompactAndFiltersAreAdjacentToResults() {
        compose.setContent { Browse() }
        compose.onNodeWithText("Query 3").assertIsDisplayed()
        compose.onNodeWithText("Query 4").assertDoesNotExist()
        compose.onNodeWithText("Show all (10)").assertIsDisplayed()
        val historyBottom = compose.onNodeWithText("Query 3").fetchSemanticsNode().boundsInRoot.bottom
        val heading = compose.onNodeWithText("Discover").fetchSemanticsNode().boundsInRoot
        val filters = compose.onNodeWithTag("filters").fetchSemanticsNode().boundsInRoot
        val result = compose.onNodeWithTag("first_result").fetchSemanticsNode().boundsInRoot
        assertTrue(historyBottom < heading.top)
        assertTrue(heading.bottom <= filters.top)
        assertTrue(result.top >= filters.bottom && result.top - filters.bottom <= 24f)
        screenshot("portrait-compact")
    }

    @Test fun allHistoryCanBeExpandedAndCollapsedWithoutDeletingEntries() {
        compose.setContent { Browse() }
        compose.onNodeWithText("Show all (10)").performClick()
        compose.onNodeWithText("Query 10").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Show less").performScrollTo().performClick()
        compose.onNodeWithTag("browse").performScrollToIndex(0)
        compose.onNodeWithText("Query 4").assertDoesNotExist()
        assertEquals(10, history.value.size)
    }

    @Test fun deletingHistoryDoesNotRunSearchAndRevealsNextEntry() {
        compose.setContent { Browse() }
        compose.onAllNodesWithContentDescription("Remove recent search")[0].performClick()
        compose.onNodeWithText("Query 1").assertDoesNotExist()
        compose.onNodeWithText("Query 4").assertIsDisplayed()
        assertEquals(null, selected)
        assertEquals(9, history.value.size)
        compose.onNodeWithText("Query 2").performClick()
        assertEquals("Query 2", selected)
    }

    @Test fun emptyHistoryHasNoBlankSectionAndDiscoverStillWorks() {
        history.value = emptyList()
        compose.setContent { Browse() }
        compose.onNodeWithText("Recent Searches").assertDoesNotExist()
        compose.onNodeWithText("Discover").assertIsDisplayed()
        compose.onNodeWithTag("first_result").assertIsDisplayed()
    }

    @Test fun shortHistoryHasNoExpansionButton() {
        history.value = history.value.take(3)
        compose.setContent { Browse() }
        compose.onNodeWithText("Show all", substring = true).assertDoesNotExist()
        compose.onNodeWithText("Query 3").assertIsDisplayed()
    }

    @Test fun expandedHistorySurvivesSavedStateRestoration() {
        val restoration = StateRestorationTester(compose)
        restoration.setContent { Browse() }
        compose.onNodeWithText("Show all (10)").performClick()
        restoration.emulateSavedInstanceStateRestore()
        compose.onNodeWithText("Query 10").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Show less").performScrollTo().assertIsDisplayed()
    }

    @Test
    @Config(qualifiers = "w891dp-h411dp-mdpi")
    fun landscapeCanReachLastResultAboveBottomOverlaySpace() {
        compose.setContent { Browse() }
        compose.onNodeWithTag("browse").performScrollToNode(hasTestTag("last_result"))
        compose.onNodeWithTag("browse").performScrollToIndex(16)
        compose.onNodeWithTag("last_result").assertIsDisplayed()
        compose.onNodeWithTag("filters").assertIsDisplayed()
        val viewport = compose.onNodeWithTag("browse").fetchSemanticsNode().boundsInRoot
        val last = compose.onNodeWithTag("last_result").fetchSemanticsNode().boundsInRoot
        assertTrue(last.bottom <= viewport.bottom - 80f)
        screenshot("landscape-scrolled")
    }

    @Test fun largeTextKeepsHistoryActionsReachable() {
        compose.setContent { Browse(fontScale = 1.5f) }
        compose.onNodeWithText("Show all (10)").performScrollTo().performClick()
        compose.onNodeWithText("Query 10").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Show less").performScrollTo().performClick()
        compose.onNodeWithTag("browse").performScrollToIndex(0)
        compose.onNodeWithText("Query 3").assertIsDisplayed()
        screenshot("large-text")
    }

    private fun screenshot(name: String) {
        val destination = File("build/reports/ui-polish/$name.png")
        destination.parentFile.mkdirs()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        destination.outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }
    }
}

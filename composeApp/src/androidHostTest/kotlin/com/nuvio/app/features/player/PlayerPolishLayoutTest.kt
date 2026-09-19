package com.nuvio.app.features.player

import android.graphics.Bitmap
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.SwapHoriz
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.StateRestorationTester
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.NuvioTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class PlayerPolishLayoutTest {
    @get:Rule val compose = createComposeRule()
    private val visible = mutableStateOf(true)
    private val selected = mutableStateOf(35)
    private val tracks = (0..38).map { SubtitleTrack(it, "$it", "English track $it", "en") } +
        SubtitleTrack(39, "hi", "Hindi track", "hi") +
        SubtitleTrack(40, "pt-BR", "Portuguese Brazil", "pt-br")

    @Composable private fun Subtitles(fontScale: Float = 1f) {
        NuvioTheme {
            CompositionLocalProvider(LocalDensity provides Density(LocalDensity.current.density, fontScale)) {
                SubtitleModal(
                    visible = visible.value, subtitleTracks = tracks, selectedSubtitleIndex = selected.value,
                    addonSubtitles = emptyList(), selectedAddonSubtitleId = null,
                    isLoadingAddonSubtitles = false, preferredSubtitleLanguage = "en",
                    secondaryPreferredSubtitleLanguage = "hi", subtitleStyle = SubtitleStyleState.DEFAULT,
                    subtitleDelayMs = 0, selectedAddonSubtitle = null,
                    subtitleAutoSyncState = SubtitleAutoSyncUiState(),
                    onBuiltInTrackSelected = { selected.value = it }, onAddonSubtitleSelected = {},
                    onFetchAddonSubtitles = {}, onStyleChanged = {}, onSubtitleDelayChanged = {},
                    onSubtitleDelayReset = {}, onAutoSyncCapture = {}, onAutoSyncCueSelected = {},
                    onAutoSyncReload = {}, onDismiss = { visible.value = false },
                )
            }
        }
    }

    @Test fun languageAndOffHaveEqualWidthAndTabsExposeSelection() {
        compose.setContent { Subtitles() }
        val language = compose.onNodeWithTag("subtitle-language-picker").fetchSemanticsNode().boundsInRoot
        val off = compose.onNodeWithTag("subtitle-off").fetchSemanticsNode().boundsInRoot
        assertTrue(kotlin.math.abs(language.width - off.width) < 1f)
        compose.onNodeWithTag("subtitle-tracks-tab").assertIsSelected()
        compose.onNodeWithTag("subtitle-style-tab").performClick().assertIsSelected()
        compose.onNodeWithTag("subtitle-tracks-tab").assertIsNotSelected()
        screenshot("portrait-tabs-selected")
    }

    @Test fun turningOffDoesNotMoveTheSheetHeader() {
        compose.setContent { Subtitles() }
        val before = compose.onNodeWithContentDescription("Close").fetchSemanticsNode().boundsInRoot
        compose.onNodeWithTag("subtitle-off").performClick().assertIsSelected()
        val after = compose.onNodeWithContentDescription("Close").fetchSemanticsNode().boundsInRoot
        assertEquals(before, after)
        compose.onNodeWithTag("subtitle-language-picker").assertIsDisplayed()
        screenshot("portrait-stable-off")
    }

    @Test fun styleAndOffStayReachableWithThirtyNineTracks() {
        compose.setContent { Subtitles() }
        compose.onNodeWithTag("subtitle-style-tab").assertIsDisplayed().performClick()
        compose.onNodeWithTag("subtitle-style").assertIsDisplayed()
        compose.onNodeWithTag("subtitle-options").assertDoesNotExist()
        compose.onNodeWithTag("subtitle-off").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(-1, selected.value) }
        screenshot("portrait-subtitle-off")
    }

    @Test fun openingAndReopeningScrollToSelectedTrack() {
        compose.setContent { Subtitles() }
        compose.onNodeWithText("English track 35").assertIsDisplayed()
        compose.onNodeWithTag("subtitle-options").performScrollToIndex(0)
        compose.onNodeWithContentDescription("Close").performClick()
        compose.runOnIdle { visible.value = true }
        compose.onNodeWithText("English track 35").assertIsDisplayed()
        screenshot("portrait-selected-track")
    }

    @Test fun languagePickerLeadsDirectlyToItsTracks() {
        compose.setContent { Subtitles() }
        compose.onNodeWithTag("subtitle-language-picker").performClick()
        compose.onNodeWithTag("subtitle-languages").performScrollToNode(hasText("Hindi"))
        compose.onNodeWithText("Hindi").performClick()
        compose.onNodeWithTag("subtitle-languages").assertDoesNotExist()
        compose.onNodeWithText("Hindi track").assertIsDisplayed().performClick()
        compose.runOnIdle { assertEquals(39, selected.value) }
    }

    @Test fun stylePageSurvivesStateRestoration() {
        val restoration = StateRestorationTester(compose)
        restoration.setContent { Subtitles() }
        compose.onNodeWithTag("subtitle-style-tab").performClick()
        restoration.emulateSavedInstanceStateRestore()
        compose.onNodeWithTag("subtitle-style").assertIsDisplayed()
        compose.onNodeWithTag("subtitle-tracks-tab").performClick()
        compose.onNodeWithTag("subtitle-options").assertIsDisplayed()
    }

    @Test fun largeTextKeepsNavigationAndCloseAccessible() {
        compose.setContent { Subtitles(1.5f) }
        compose.onNodeWithTag("subtitle-style-tab").assertIsDisplayed().performClick()
        compose.onNodeWithTag("subtitle-off").assertIsDisplayed()
        compose.onNodeWithContentDescription("Close").assertIsDisplayed()
        screenshot("portrait-subtitle-large-text")
    }

    @Test @Config(qualifiers = "w891dp-h411dp-mdpi")
    fun landscapeStillShowsTrackRailsAndSelectedTrack() {
        compose.setContent { Subtitles() }
        compose.onNodeWithTag("subtitle-tracks-tab").assertDoesNotExist()
        compose.onNodeWithText("English track 35").assertIsDisplayed()
        screenshot("landscape-subtitle-rails")
    }

    @Test fun longAudioLabelWrapsWithoutLosingCodecOrRole() {
        val label = "English Original commentary with director and cinematographer DTS-HD Master Audio 7.1"
        compose.setContent {
            NuvioTheme {
                AudioTrackModal(true, listOf(AudioTrack(0, "long", label, "en")), 0, {}, {})
            }
        }
        val layouts = mutableListOf<TextLayoutResult>()
        compose.onNodeWithText(label).assertIsDisplayed().performSemanticsAction(SemanticsActions.GetTextLayoutResult) { it(layouts) }
        assertTrue(layouts.single().lineCount > 1)
        assertFalse(layouts.single().hasVisualOverflow)
        screenshot("portrait-audio-label")
    }

    @Test fun speedFeedbackClearsTallHeader() {
        compose.setContent {
            NuvioTheme {
                Box(Modifier.fillMaxSize()) {
                    val feedback = GestureFeedbackState(message = "1.25×")
                    PlayerGestureFeedbackOverlay(feedback, feedback, 0.dp, 180.dp)
                }
            }
        }
        val pill = compose.onNodeWithText("1.25×").assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        assertTrue(pill.top >= 188f)
        screenshot("portrait-speed-feedback")
    }

    @Test @Config(qualifiers = "w320dp-h800dp-mdpi")
    fun languageLabelNeverBreaksWordsOnNarrowScreens() {
        selected.value = -1
        val fontScale = mutableStateOf(1f)
        var longLanguageLabel = ""
        compose.setContent { longLanguageLabel = languageLabelForCode("pt-br"); Subtitles(fontScale.value) }
        fun assertSingleLine(label: String, fullyVisible: Boolean = false) {
            val layouts = mutableListOf<TextLayoutResult>()
            compose.onNode(hasText(label) and hasAnyAncestor(hasTestTag("subtitle-language-picker")), useUnmergedTree = true)
                .assertIsDisplayed().performSemanticsAction(SemanticsActions.GetTextLayoutResult) { it(layouts) }
            assertEquals(1, layouts.single().lineCount)
            if (fullyVisible) assertFalse(layouts.single().isLineEllipsized(0))
        }
        assertSingleLine("Languages", fullyVisible = true)
        screenshot("narrow-languages-single-line")
        compose.runOnIdle { fontScale.value = 1.5f }
        assertSingleLine("Languages")
        compose.runOnIdle { selected.value = 40 }
        assertSingleLine(longLanguageLabel)
        compose.onNodeWithTag("subtitle-language-picker").performClick()
        compose.onNodeWithTag("subtitle-languages").assertIsDisplayed()
        screenshot("narrow-long-language-large-text")
    }

    @Test fun qualityLabelAlignsWithIconButtonsInPortrait() = checkQualityAlignment()

    @Test @Config(qualifiers = "w891dp-h411dp-mdpi")
    fun qualityLabelAlignsWithIconButtonsInLandscape() = checkQualityAlignment()

    @OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
    private fun checkQualityAlignment() {
        var clicks = 0
        val fontScale = mutableStateOf(1f)
        compose.setContent {
            NuvioTheme {
                CompositionLocalProvider(LocalDensity provides Density(LocalDensity.current.density, fontScale.value)) {
                    FlowRow {
                        PlayerActionPillButton("Sources", {}, icon = Icons.Rounded.SwapHoriz)
                        PlayerActionPillButton("4K UHD", { clicks++ })
                    }
                }
            }
        }
        fun assertAligned() {
            val source = compose.onNodeWithText("Sources", useUnmergedTree = true).fetchSemanticsNode().boundsInRoot
            val quality = compose.onNodeWithText("4K UHD", useUnmergedTree = true).fetchSemanticsNode().boundsInRoot
            assertTrue(kotlin.math.abs(source.center.y - quality.center.y) < 1f)
            compose.onNodeWithText("4K UHD").performClick()
        }
        assertAligned()
        screenshot("quality-aligned")
        compose.runOnIdle { fontScale.value = 1.5f }
        assertAligned()
        compose.runOnIdle { assertEquals(2, clicks) }
    }

    private fun screenshot(name: String) {
        val path = File("build/reports/ui-polish/$name.png")
        path.parentFile.mkdirs()
        path.outputStream().use { compose.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
}

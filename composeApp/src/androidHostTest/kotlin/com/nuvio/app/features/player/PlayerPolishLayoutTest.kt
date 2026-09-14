package com.nuvio.app.features.player

import android.graphics.Bitmap
import androidx.compose.foundation.layout.Box
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
        SubtitleTrack(39, "hi", "Hindi track", "hi")

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

    private fun screenshot(name: String) {
        val path = File("build/reports/ui-polish/$name.png")
        path.parentFile.mkdirs()
        path.outputStream().use { compose.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
}

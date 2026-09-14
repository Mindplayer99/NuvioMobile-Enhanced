package com.nuvio.app.features.player

import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.media3.ui.PlayerView
import androidx.media3.ui.R
import androidx.test.core.app.ApplicationProvider
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import kotlin.test.assertEquals

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class PortraitSubtitleViewportTest {
    @Test fun captionsFollowVideoBoundsAndRestoreLandscapeWithoutRecreatingView() {
        val view = PlayerView(ApplicationProvider.getApplicationContext())
        view.installPortraitSubtitleViewport()
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        view.layout(0, 0, 400, 900)
        frame.layout(0, 337, 400, 562)
        val portrait = view.subtitleView!!.layoutParams as FrameLayout.LayoutParams
        assertEquals(337, portrait.topMargin)
        assertEquals(225, portrait.height)
        view.layout(0, 0, 900, 400)
        frame.layout(94, 0, 805, 400)
        val landscape = view.subtitleView!!.layoutParams as FrameLayout.LayoutParams
        assertEquals(0, landscape.topMargin)
        assertEquals(ViewGroup.LayoutParams.MATCH_PARENT, landscape.height)
    }

    @Test fun croppedAndUnknownVideoBoundsNeverCreateNegativeCaptionHeight() {
        val view = PlayerView(ApplicationProvider.getApplicationContext())
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        view.layout(0, 0, 400, 900)
        frame.layout(0, -100, 400, 1000)
        view.alignPortraitSubtitleViewport()
        val params = view.subtitleView!!.layoutParams as FrameLayout.LayoutParams
        assertEquals(0, params.topMargin)
        assertEquals(900, params.height)
        frame.layout(0, 0, 0, 0)
        view.alignPortraitSubtitleViewport()
        assertEquals(ViewGroup.LayoutParams.MATCH_PARENT, params.height)
    }
}

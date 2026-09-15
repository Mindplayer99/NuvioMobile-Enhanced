package com.nuvio.app.features.player

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.media3.common.text.Cue
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import androidx.media3.ui.R
import androidx.test.core.app.ApplicationProvider
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class PortraitSubtitleViewportTest {
    private fun player(nested: Boolean = false): PlayerView {
        val view = PlayerView(ApplicationProvider.getApplicationContext())
        view.useController = false
        view.setBackgroundColor(Color.BLACK)
        view.findViewById<AspectRatioFrameLayout>(R.id.exo_content_frame).setAspectRatio(2.4f)
        val captions = view.subtitleView!!
        if (nested) {
            (captions.parent as ViewGroup).removeView(captions)
            view.findViewById<FrameLayout>(R.id.exo_content_frame).addView(captions)
        }
        view.installPortraitSubtitleViewport()
        captions.setApplyEmbeddedStyles(false)
        captions.setFixedTextSize(android.util.TypedValue.COMPLEX_UNIT_PX, 24f)
        return view
    }

    private fun layout(view: PlayerView, width: Int, height: Int) {
        // Run complete measurement/layout/pre-draw traversals, not manual child.layout calls.
        var stable = false
        repeat(8) {
            view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY))
            view.layout(0, 0, width, height)
            val changed = view.alignPortraitSubtitleViewport()
            if (!changed) stable = true
        }
        assertTrue(stable, "Caption layout must converge without a redraw loop")
    }

    private fun text(view: PlayerView, explicitPosition: Boolean = false) {
        val builder = Cue.Builder().setText("Readable portrait subtitle")
        if (explicitPosition) builder.setLine(0.94f, Cue.LINE_TYPE_FRACTION).setLineAnchor(Cue.ANCHOR_TYPE_END)
        view.subtitleView!!.setCues(listOf(builder.build()))
    }

    private fun assertDrawnInside(view: PlayerView, top: Int, bottom: Int, name: String) {
        val bitmap = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
        view.draw(Canvas(bitmap))
        var pixels = 0
        var first = view.height
        var last = -1
        for (y in 0 until bitmap.height) for (x in 0 until bitmap.width) {
            val c = bitmap.getPixel(x, y)
            if (Color.green(c) > 180 && Color.alpha(c) > 200) {
                pixels++; first = minOf(first, y); last = maxOf(last, y)
            }
        }
        assertTrue(pixels > 30, "Actual subtitle pixels must be visible ($name)")
        assertTrue(first >= top && last < bottom, "$name pixels $first..$last outside $top..$bottom")
        val file = File("build/reports/ui-polish/$name.png"); file.parentFile.mkdirs()
        file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun fittedTextActuallyDrawsInsideVideo() {
        val view = player(); text(view); layout(view, 400, 900)
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        assertDrawnInside(view, frame.top, frame.bottom, "caption-fit-text")
    }

    @Test fun nestedSubtitleViewDoesNotDoubleApplyVideoTopOffset() {
        val view = player(nested = true); text(view); layout(view, 400, 900)
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        assertTrue(view.subtitleView!!.parent === view)
        assertEquals(frame.top, view.subtitleView!!.top)
        assertDrawnInside(view, frame.top, frame.bottom, "caption-nested-fit")
    }

    @Test fun explicitTextCuesStayVisibleThroughFitZoomAndRotation() {
        val view = player(); text(view, true)
        layout(view, 400, 900)
        view.updatePortraitCaptionBottomInset(180)
        view.resizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM
        layout(view, 400, 900)
        assertDrawnInside(view, 0, 720, "caption-zoom-controls")
        layout(view, 900, 400)
        assertEquals(0, view.subtitleView!!.top)
        assertDrawnInside(view, 0, 400, "caption-landscape")
        view.resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
        layout(view, 400, 900)
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        assertDrawnInside(view, frame.top, frame.bottom, "caption-return-fit")
    }

    @Test fun bitmapCuesRenderInsidePortraitVideo() {
        val view = player()
        val image = Bitmap.createBitmap(140, 25, Bitmap.Config.ARGB_8888).apply { eraseColor(Color.GREEN) }
        view.subtitleView!!.setCues(listOf(Cue.Builder().setBitmap(image).setPosition(0.5f)
            .setPositionAnchor(Cue.ANCHOR_TYPE_MIDDLE).setLine(0.95f, Cue.LINE_TYPE_FRACTION)
            .setLineAnchor(Cue.ANCHOR_TYPE_END).setSize(0.7f).setBitmapHeight(0.15f).build()))
        layout(view, 400, 900)
        val frame = view.findViewById<View>(R.id.exo_content_frame)
        assertDrawnInside(view, frame.top, frame.bottom, "caption-fit-bitmap")
        view.resizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM
        view.updatePortraitCaptionBottomInset(180)
        layout(view, 400, 900)
        assertDrawnInside(view, 0, 720, "caption-zoom-bitmap")
    }

    @Test fun fillAndShortWindowHaveUsableCaptionBounds() {
        val view = player(); text(view)
        view.resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FILL
        view.updatePortraitCaptionBottomInset(400)
        layout(view, 320, 480)
        assertTrue(view.subtitleView!!.height > 0)
        assertDrawnInside(view, 0, 240, "caption-short-fill")
    }
}

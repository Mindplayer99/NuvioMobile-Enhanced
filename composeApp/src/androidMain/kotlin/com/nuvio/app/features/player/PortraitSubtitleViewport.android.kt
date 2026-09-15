package com.nuvio.app.features.player

import android.graphics.Rect
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.widget.FrameLayout
import androidx.media3.ui.PlayerView
import androidx.media3.ui.R

/** Captions use one coordinate space even when a dependency places them inside the video frame. */
internal fun PlayerView.installPortraitSubtitleViewport(bottomInsetPx: Int = 0) {
    if (getTag(R.id.exo_subtitles) is PortraitCaptionViewport) return
    val captions = subtitleView ?: return
    val content = findViewById<View>(R.id.exo_content_frame) ?: return
    // Never apply a PlayerView-relative top margin to a child of the already-offset video frame.
    if (captions.parent !== this) {
        (captions.parent as? ViewGroup)?.removeView(captions)
        val overlayIndex = indexOfChild(findViewById(R.id.exo_ad_overlay)).takeIf { it >= 0 } ?: childCount
        addView(captions, overlayIndex, FrameLayout.LayoutParams(-1, -1))
    }
    val viewport = PortraitCaptionViewport(this, content, captions, bottomInsetPx)
    setTag(R.id.exo_subtitles, viewport)
    viewport.install()
}

internal fun PlayerView.updatePortraitCaptionBottomInset(bottomInsetPx: Int) {
    val viewport = getTag(R.id.exo_subtitles) as? PortraitCaptionViewport ?: return
    if (viewport.bottomInsetPx != bottomInsetPx) {
        viewport.bottomInsetPx = bottomInsetPx
        requestLayout()
    }
}

internal fun PlayerView.alignPortraitSubtitleViewport(): Boolean =
    (getTag(R.id.exo_subtitles) as? PortraitCaptionViewport)?.align() ?: false

private class PortraitCaptionViewport(
    val player: PlayerView,
    val content: View,
    val captions: View,
    var bottomInsetPx: Int,
) : ViewTreeObserver.OnPreDrawListener, View.OnAttachStateChangeListener {
    private val bounds = Rect()

    fun install() {
        player.addOnAttachStateChangeListener(this)
        player.viewTreeObserver.addOnPreDrawListener(this)
        player.requestLayout()
    }

    override fun onViewAttachedToWindow(v: View) {
        v.viewTreeObserver.removeOnPreDrawListener(this)
        v.viewTreeObserver.addOnPreDrawListener(this)
    }

    override fun onViewDetachedFromWindow(v: View) {
        if (v.viewTreeObserver.isAlive) v.viewTreeObserver.removeOnPreDrawListener(this)
    }

    // A layout callback can run before its siblings are measured. Check after the whole traversal,
    // and postpone drawing once when new geometry requires measurement. Never draw stale bounds.
    override fun onPreDraw(): Boolean = !align()

    fun align(): Boolean {
        if (player.width <= 0 || player.height <= 0) return false
        val portrait = player.height > player.width && content.width > 0 && content.height > 0
        bounds.set(0, 0, player.width, player.height)
        if (portrait) {
            bounds.set(0, 0, content.width, content.height)
            player.offsetDescendantRectToMyCoords(content, bounds)
            if (!bounds.intersect(0, 0, player.width, player.height)) {
                bounds.set(0, 0, player.width, player.height)
            }
            // Keep room for measured controls in Zoom/Fill. Preserve a usable viewport on short screens.
            val safeBottom = player.height - bottomInsetPx.coerceIn(0, player.height / 2)
            bounds.bottom = minOf(bounds.bottom, maxOf(bounds.top + 1, safeBottom))
        }
        val params = captions.layoutParams as FrameLayout.LayoutParams
        val targetWidth = if (portrait) bounds.width() else ViewGroup.LayoutParams.MATCH_PARENT
        val targetHeight = if (portrait) bounds.height() else ViewGroup.LayoutParams.MATCH_PARENT
        if (params.leftMargin == bounds.left && params.topMargin == bounds.top &&
            params.width == targetWidth && params.height == targetHeight &&
            params.gravity == (Gravity.TOP or Gravity.START)) return false
        params.gravity = Gravity.TOP or Gravity.START
        params.leftMargin = bounds.left
        params.topMargin = bounds.top
        params.rightMargin = 0
        params.bottomMargin = 0
        params.width = targetWidth
        params.height = targetHeight
        captions.layoutParams = params
        return true
    }
}

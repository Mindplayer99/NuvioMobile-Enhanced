package com.nuvio.app.features.player

import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.media3.ui.PlayerView
import androidx.media3.ui.R

/** Follow the actual fitted/cropped picture, including rotation without Activity recreation. */
internal fun PlayerView.installPortraitSubtitleViewport() {
    val content = findViewById<View>(R.id.exo_content_frame) ?: return
    val listener = View.OnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
        alignPortraitSubtitleViewport()
    }
    content.addOnLayoutChangeListener(listener)
    addOnLayoutChangeListener(listener)
}

internal fun PlayerView.alignPortraitSubtitleViewport() {
    val captions = subtitleView ?: return
    val content = findViewById<View>(R.id.exo_content_frame) ?: return
    val params = captions.layoutParams as? FrameLayout.LayoutParams ?: return
    val portrait = height > width && width > 0 && content.height > 0
    val top = if (portrait) content.top.coerceIn(0, height) else 0
    val bottom = if (portrait) content.bottom.coerceIn(top, height) else height
    val targetHeight = if (portrait && bottom > top) bottom - top else ViewGroup.LayoutParams.MATCH_PARENT
    if (params.topMargin != top || params.height != targetHeight) {
        params.topMargin = top
        params.height = targetHeight
        captions.layoutParams = params
    }
}

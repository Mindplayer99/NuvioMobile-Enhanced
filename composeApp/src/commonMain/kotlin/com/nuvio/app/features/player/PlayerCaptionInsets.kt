package com.nuvio.app.features.player

import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.unit.dp

/** Retain measured portrait controls clearance while controls fade, avoiding caption jumps. */
internal val LocalPlayerCaptionBottomInset = compositionLocalOf { 0.dp }

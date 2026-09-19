package com.nuvio.app.features.player

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.ActivityInfo
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import kotlin.test.assertEquals

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-mdpi")
class PlayerOrientationExitTest {
    @get:Rule val compose = createComposeRule()

    @Test fun portraitRemainsUntilAnimatedDestinationExitsThenOriginalPolicyReturns() {
        val host = mutableStateOf(true)
        val child = mutableStateOf(true)
        lateinit var activity: Activity
        var original: Int? = null
        compose.setContent {
            var context: Context = LocalContext.current
            while (context !is Activity) context = (context as ContextWrapper).baseContext
            activity = context
            if (original == null) original = activity.requestedOrientation
            val settings = PlayerSettingsUiState(orientationPreference = PlayerOrientationPreference.AlwaysPortrait)
            if (host.value) KeepPlayerOrientationUntilExit(settings)
            if (child.value) rememberPlayerOrientationControl("movie", settings)
        }
        compose.runOnIdle { assertEquals(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, activity.requestedOrientation); child.value = false }
        compose.runOnIdle { assertEquals(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, activity.requestedOrientation); host.value = false }
        compose.runOnIdle { assertEquals(original, activity.requestedOrientation) }
    }

    @Test fun hostAndChildCanDisposeTogetherWithoutLeavingPortraitLocked() {
        val visible = mutableStateOf(true)
        lateinit var activity: Activity
        var original: Int? = null
        compose.setContent {
            var context: Context = LocalContext.current
            while (context !is Activity) context = (context as ContextWrapper).baseContext
            activity = context
            if (original == null) original = activity.requestedOrientation
            if (visible.value) {
                val settings = PlayerSettingsUiState(orientationPreference = PlayerOrientationPreference.AlwaysPortrait)
                KeepPlayerOrientationUntilExit(settings)
                rememberPlayerOrientationControl("movie", settings)
            }
        }
        compose.runOnIdle { visible.value = false }
        compose.runOnIdle { assertEquals(original, activity.requestedOrientation) }
    }
}

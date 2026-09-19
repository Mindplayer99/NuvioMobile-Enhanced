package com.nuvio.app.features.player

import android.content.pm.ActivityInfo
import kotlin.test.Test
import kotlin.test.assertEquals

class PlayerOrientationAndroidTest {
    @Test
    fun explicitModesUsePhoneOrientationsAndFollowDeviceHonorsTheUserPolicy() {
        assertEquals(
            ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE,
            PlayerOrientation.Landscape.toAndroidRequestedOrientation(),
        )
        assertEquals(
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT,
            PlayerOrientation.Portrait.toAndroidRequestedOrientation(),
        )
        assertEquals(ActivityInfo.SCREEN_ORIENTATION_USER, null.toAndroidRequestedOrientation())
    }
}

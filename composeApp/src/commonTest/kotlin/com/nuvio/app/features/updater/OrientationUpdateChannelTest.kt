package com.nuvio.app.features.updater

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class OrientationUpdateChannelTest {
    @Test fun `only orientation release tags qualify`() {
        assertTrue(OrientationUpdateChannel.matchesTag("0.4.16-orientation"))
        listOf(null, "0.4.16", "enhanced", "0.4.16-orientation-beta", "0.4.14-orientation-final")
            .forEach { assertFalse(OrientationUpdateChannel.matchesTag(it)) }
    }

    @Test fun `suffix does not interfere with numeric comparison`() {
        assertTrue(VersionUtils.isRemoteNewer("0.4.16-orientation", "0.4.15"))
        assertTrue(VersionUtils.isRemoteNewer("0.4.100-orientation", "0.4.99"))
        assertFalse(VersionUtils.isRemoteNewer("0.4.15-orientation", "0.4.15"))
        assertFalse(VersionUtils.isRemoteNewer("0.4.14-orientation", "0.4.15"))
    }

    @Test fun `asset must be the matching Full ARM64 orientation build`() {
        assertEquals("Nuvio-Enhanced-0.4.16-Orientation-Full-arm64-v8a.apk",
            OrientationUpdateChannel.assetName("0.4.16-orientation"))
        assertNull(OrientationUpdateChannel.assetName("0.4.16"))
    }
}

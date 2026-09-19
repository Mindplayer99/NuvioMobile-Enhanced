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
    @Test fun `production selector ignores upstream beta draft and wrong assets`() {
        val response = """[
          {"tag_name":"0.4.24-beta","assets":[{"name":"app-arm64-v8a.apk","browser_download_url":"wrong"}]},
          {"tag_name":"0.4.23-orientation","prerelease":true,"assets":[{"name":"Nuvio-Enhanced-0.4.23-Orientation-Full-arm64-v8a.apk","browser_download_url":"beta"}]},
          {"tag_name":"0.4.25-orientation","draft":true,"assets":[{"name":"Nuvio-Enhanced-0.4.25-Orientation-Full-arm64-v8a.apk","browser_download_url":"draft"}]},
          {"tag_name":"0.4.26-orientation","assets":[{"name":"app-arm64-v8a.apk","browser_download_url":"wrong-asset"}]},
          {"tag_name":"0.4.22-orientation","assets":[{"name":"Nuvio-Enhanced-0.4.22-Orientation-Full-arm64-v8a.apk","browser_download_url":"verified"}]},
          {"tag_name":"0.4.17-orientation-ui.3","assets":[{"name":"app.apk","browser_download_url":"ui"}]}
        ]"""
        assertEquals("verified", AppUpdaterRepository.selectOrientationUpdate(response, listOf("arm64-v8a"))?.assetUrl)
        assertNull(AppUpdaterRepository.selectOrientationUpdate(response, listOf("x86_64")))
        assertNull(AppUpdaterRepository.selectOrientationUpdate("[]", listOf("arm64-v8a")))
    }

    @Test fun `duplicate exact assets are ambiguous and cannot update`() {
        val asset = """{"name":"Nuvio-Enhanced-0.4.22-Orientation-Full-arm64-v8a.apk","browser_download_url":"url"}"""
        assertNull(AppUpdaterRepository.selectOrientationUpdate(
            """[{"tag_name":"0.4.22-orientation","assets":[$asset,$asset]}]""", listOf("arm64-v8a")))
    }
}

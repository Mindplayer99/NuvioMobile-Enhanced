package com.nuvio.app.features.player

import androidx.compose.ui.unit.dp
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class PlayerOrientationTest {
    @Test
    fun freshInstallStartsLandscapeAndRemembersByDefault() {
        val session = PlayerOrientationSession(
            PlayerOrientationPreference.fromStored(null),
            PlayerOrientation.fromStored(null),
        )
        assertEquals(PlayerOrientationPreference.RememberLastUsed, session.preference)
        assertEquals(PlayerOrientation.Landscape, session.requested)
        assertNull(session.orientationToRemember)
    }

    @Test
    fun rememberedChoiceRoundTripsThroughStorageIntoANewSession() {
        var storedOrientation: String? = null
        for (expected in listOf(PlayerOrientation.Portrait, PlayerOrientation.Landscape)) {
            val session = PlayerOrientationSession(
                PlayerOrientationPreference.RememberLastUsed,
                PlayerOrientation.fromStored(storedOrientation),
            ).rotate(PlayerOrientation.Landscape)
            storedOrientation = session.orientationToRemember?.name
            val reopened = PlayerOrientationSession(
                PlayerOrientationPreference.fromStored(session.preference.name),
                PlayerOrientation.fromStored(storedOrientation),
            )
            assertEquals(expected, reopened.requested)
            assertNull(reopened.sessionOverride)
        }
    }

    @Test
    fun alwaysModesAllowTemporaryRotationWithoutChangingNextVideoOrMemory() {
        for ((preference, initial) in listOf(
            PlayerOrientationPreference.AlwaysLandscape to PlayerOrientation.Landscape,
            PlayerOrientationPreference.AlwaysPortrait to PlayerOrientation.Portrait,
        )) {
            val session = PlayerOrientationSession(preference, initial.opposite())
            assertEquals(initial, session.requested)
            val rotated = session.rotate(initial)
            assertEquals(initial.opposite(), rotated.requested)
            assertEquals(preference, rotated.preference)
            assertNull(rotated.orientationToRemember)
            assertEquals(initial, PlayerOrientationSession(preference, rotated.lastUsed).requested)
        }
    }

    @Test
    fun followDeviceDelegatesUntilRotatedAndResumesForTheNextVideo() {
        for (device in PlayerOrientation.entries) {
            val session = PlayerOrientationSession(
                PlayerOrientationPreference.FollowDevice,
                PlayerOrientation.Portrait,
            )
            assertNull(session.requested)
            val rotated = session.rotate(device)
            assertEquals(device.opposite(), rotated.requested)
            assertNull(rotated.orientationToRemember)
            assertNull(PlayerOrientationSession(rotated.preference, rotated.lastUsed).requested)
        }
    }

    @Test
    fun rapidSecondTapTogglesThePendingRequestBeforeConfigurationCatchesUp() {
        val session = PlayerOrientationSession(
            PlayerOrientationPreference.AlwaysLandscape,
            PlayerOrientation.Landscape,
        )
        val portrait = session.rotate(PlayerOrientation.Landscape)
        val landscape = portrait.rotate(PlayerOrientation.Landscape)
        assertEquals(PlayerOrientation.Portrait, portrait.requested)
        assertEquals(PlayerOrientation.Landscape, landscape.requested)
    }

    @Test
    fun publishingTheSavedChoiceDoesNotToggleTheCurrentSessionAgain() {
        val rotated = PlayerOrientationSession(
            PlayerOrientationPreference.RememberLastUsed,
            PlayerOrientation.Landscape,
        ).rotate(PlayerOrientation.Landscape)
        assertEquals(
            PlayerOrientation.Portrait,
            rotated.copy(lastUsed = PlayerOrientation.Portrait).requested,
        )
    }

    @Test
    fun invalidStoredValuesFallBackSafely() {
        for (stored in listOf("", "future-option", "portrait")) {
            assertEquals(PlayerOrientationPreference.RememberLastUsed, PlayerOrientationPreference.fromStored(stored))
            assertEquals(PlayerOrientation.Landscape, PlayerOrientation.fromStored(stored))
        }
        PlayerOrientationPreference.entries.forEach {
            assertEquals(it, PlayerOrientationPreference.fromStored(it.name))
        }
    }

    @Test
    fun normalPortraitPhonesUseCompactControlsAndLandscapeKeepsExistingMetrics() {
        for (width in listOf(360, 393, 430)) {
            assertTrue(PlayerLayoutMetrics.fromWidth(width.dp).compactControls)
        }
        assertFalse(PlayerLayoutMetrics.fromWidth(800.dp).compactControls)
    }
}

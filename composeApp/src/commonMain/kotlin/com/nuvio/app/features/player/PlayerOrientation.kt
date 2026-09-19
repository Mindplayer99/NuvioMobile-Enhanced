package com.nuvio.app.features.player

enum class PlayerOrientationPreference {
    RememberLastUsed,
    AlwaysLandscape,
    AlwaysPortrait,
    FollowDevice;

    companion object {
        fun fromStored(value: String?): PlayerOrientationPreference =
            entries.firstOrNull { it.name == value } ?: RememberLastUsed
    }
}

enum class PlayerOrientation {
    Landscape,
    Portrait;

    fun opposite(): PlayerOrientation = if (this == Portrait) Landscape else Portrait

    companion object {
        fun fromStored(value: String?): PlayerOrientation =
            entries.firstOrNull { it.name == value } ?: Landscape
    }
}

/** A content session, independent of the player engine, stream URL, and window size. */
internal data class PlayerOrientationSession(
    val preference: PlayerOrientationPreference,
    val lastUsed: PlayerOrientation,
    val sessionOverride: PlayerOrientation? = null,
) {
    // null delegates orientation to Android, including the user's auto-rotate setting.
    val requested: PlayerOrientation?
        get() = sessionOverride ?: when (preference) {
            PlayerOrientationPreference.RememberLastUsed -> lastUsed
            PlayerOrientationPreference.AlwaysLandscape -> PlayerOrientation.Landscape
            PlayerOrientationPreference.AlwaysPortrait -> PlayerOrientation.Portrait
            PlayerOrientationPreference.FollowDevice -> null
        }

    fun rotate(deviceOrientation: PlayerOrientation): PlayerOrientationSession =
        copy(sessionOverride = (requested ?: deviceOrientation).opposite())

    val orientationToRemember: PlayerOrientation?
        get() = sessionOverride.takeIf { preference == PlayerOrientationPreference.RememberLastUsed }
}

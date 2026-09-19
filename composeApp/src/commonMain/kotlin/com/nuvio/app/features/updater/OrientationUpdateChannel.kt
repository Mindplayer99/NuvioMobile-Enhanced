package com.nuvio.app.features.updater

internal object OrientationUpdateChannel {
    private val tagPattern = Regex("[0-9]+\\.[0-9]+\\.[0-9]+-orientation")

    fun matchesTag(tag: String?): Boolean = tag != null && tagPattern.matches(tag)

    fun assetName(tag: String): String? = if (matchesTag(tag)) {
        "Nuvio-Enhanced-${tag.removeSuffix("-orientation")}-Orientation-Full-arm64-v8a.apk"
    } else null
}

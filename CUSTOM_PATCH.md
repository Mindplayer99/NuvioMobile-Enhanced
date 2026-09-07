# Android player orientation

Base: Enhanced stable tag **0.4.14**, commit
`012d663a3b85847c0ae6c25f3c92e727818bac4d` (5 September 2026).
This tag contains official Nuvio 0.4.14 with no missing upstream commits.
Branch: `feature/android-player-orientation`.

## Behaviour

- **Remember last used** defaults to Landscape and persists button selections
  per profile on this device across videos and restarts.
- **Always Landscape / Always Portrait** reset to that orientation for each
  newly opened video or episode. Rotation temporarily overrides the current session.
- **Follow Device** uses Android `SCREEN_ORIENTATION_USER` (system auto-rotate).
  The button overrides it for the current video only.
- Quality/source changes for the same content keep the session's orientation.
- Tablets retain their existing policy. Split-screen releases the phone lock;
  PiP receives no orientation requests. Closing restores the previous app request.
- Narrow controls wrap using the existing styling and safe insets, with 48dp
  header buttons. Playback engines, source loading, tracks and downloads are unchanged.

Orientation is device-local, not cloud-synced. iOS retains its existing landscape
notifications; only its shared storage contract is extended. The existing Android
manifest already handles orientation, screenSize, smallestScreenSize and
screenLayout changes without recreating the activity.

## Main files

Within `composeApp/src/`, the patch affects:

- `PlayerOrientation.kt` and Android `PlayerPlatformEffects`: session policy,
  Android orientation requests, PiP/window handling and restoration.
- `PlayerSettingsRepository` and common/Android/iOS `PlayerSettingsStorage`:
  existing persistence and profile-loading architecture.
- `PlayerScreenContent`, `PlayerScreenRuntimeUi`, `PlayerControls`, `PlayerLayout`:
  button wiring and responsive layout.
- `PlaybackSettingsPage` and `values/player_orientation.xml`: four-choice picker.
- `PlayerOrientationTest` / `PlayerOrientationAndroidTest`: focused policy tests.

`androidApp/build.gradle.kts` adds optional ABI and debug application-ID settings;
normal upstream build defaults are unchanged. No download files or permissions
were changed: Downloads → gear → Download Location still uses the existing SAF picker.

## Build and carry forward

With JDK 17, the pinned Android SDK and ignored `local.properties` configuration:

```sh
./gradlew :androidApp:assembleFullDebug \
  -Pnuvio.android.abis=arm64-v8a -Pnuvio.android.keepApplicationId=true
./gradlew :composeApp:testAndroidHostTest -Pnuvio.android.distribution=full \
  --tests 'com.nuvio.app.features.player.PlayerOrientation*'
```

The original orientation APK uses `com.nuvio.media` and standard debug signing. Retain its signing
keystore securely for future updates; never commit it or private API credentials.
A fork does not inherit upstream integration credentials.

For a newer release, branch from its verified stable Enhanced tag and cherry-pick
this patch. Resolve only these integration points; adopt a complete upstream
orientation implementation if one appears. Recheck both playback engines and
activity configuration handling, run the tests and rebuild ARM64 Full. Verify
active playback rotation, track/position/resize retention, next episode, cold
restart, system rotation lock, PiP/back and SAF folder selection on a real phone.

## Incremental portrait track polish

Starting from `f3b64f85fcbb294cfef36917273e7760df4db1c6`, the orientation
implementation remains unchanged. AudioTrackModal and SubtitleModal use a
shared CompactPlayerTrackSheet below 600dp: an opaque, rounded card at 92% of
safe available width, bounded to 90% of safe height. Subtitle languages/options
share one vertical lazy list; the existing Style panel retains delay, styling
and auto-sync, with wrapping color swatches. Wide rails retain their layout.
PlayerScreenRuntimeUi hides normal controls only for these compact track modals
and restores controls on dismissal without changing playback.

Two small performance changes accompany this polish: HomeHeroSection reads
per-pixel scroll transforms in graphicsLayer instead of composition, and
SettingsScreen builds its search index only when a nonblank root query needs it.
No on-device frame-time improvement has been measured in the build environment.

For this update, use the existing optimized Full release build with the SAME
original keystore. Put NUVIO_RELEASE_STORE_FILE, NUVIO_RELEASE_STORE_PASSWORD,
NUVIO_RELEASE_KEY_ALIAS and NUVIO_RELEASE_KEY_PASSWORD in ignored local.properties.
Do not generate a replacement key. Expected signing certificate SHA-256:
`99e3d93e7600c178e71bf80ded2b1d97664e3ef14058c473c4617cb27fd04e35`.

```sh
./gradlew :androidApp:assembleFullRelease \
  -Pnuvio.android.distribution=full -Pnuvio.android.abis=arm64-v8a
```

The optional ABI flag now uses either release splits or debug ndk.abiFilters,
so the two mechanisms do not conflict. Dependency versions are unchanged.
After carrying forward, recheck compact/landscape audio and subtitle lists,
empty/fetch/loading states, Style/auto-sync, selection retention and modal
reopening after rotation. Keep Sources, Quality and the orientation policy intact.

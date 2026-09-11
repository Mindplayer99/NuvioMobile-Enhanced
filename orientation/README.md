# Orientation release channel

The installed Full ARM64 app uses only published stable `Mindplayer99/NuvioMobile-Enhanced`
releases named `X.Y.Z-orientation` with the exact asset name
`Nuvio-Enhanced-X.Y.Z-Orientation-Full-arm64-v8a.apk`. Upstream APKs, prereleases,
drafts, and the preserved `0.4.14-orientation-final` backup are excluded from update offers.
Android still asks the user to approve APK installation; publishing does not silently install it.

## Canonical source

`manifest.json` pins exact upstream 0.4.15 and the reviewed Orientation candidate.
`canonical.patch` is the complete squashed Git delta between those commits, including
portrait track sheets, persistent orientation, responsive controls, original performance
changes, the private update channel, and regression tests. It contains no signing material.
The migration is preserved in the original feature branches and immutable release tags.

## Automatic integration

The default-branch workflow runs hourly at minute 23 (GitHub may delay scheduled jobs).
It considers only published stable numeric releases in `luqmanfadlli/NuvioMobile-Enhanced`,
selecting the next release newer than the latest verified Orientation release. It fetches
that exact tag, requires ancestry from the canonical upstream baseline, and applies the
canonical delta on a fresh worktree. The candidate's single parent is the exact upstream
commit. No upstream application files outside the canonical delta are overwritten.

A clean textual merge alone is insufficient. Changes in the player, updater, profile
integration, canonical files, Android manifest/activity, native dependencies, Gradle,
scripts, or workflows stop automatic publication for review. Version metadata may change
only its version name/code; the code must increase. This deliberately preserves the last
working release when automatic compatibility cannot be established. New feature changes
outside these protected areas can proceed through compilation and regression tests.

The pipeline runs player, downloads, updater, home, and settings host tests, builds Full
ARM64, and checks the exact source, package, version, versionCode, non-debuggable status,
Full native libraries, and installed signing certificate. It uploads a draft, downloads
and verifies the actual remote bytes, then publishes. Existing public releases and tags
are never overwritten. `orientation-current` advances only after successful publication;
immutable release tags retain all previous versions. A failed scheduled/publish run opens
one review issue and retains test reports. It cannot replace a working APK with a failed build.

## Manual checks and maintenance

The workflow supports `dry-run` (next upstream through tests/build/verification, no publish),
`baseline` (reproduce the canonical source tree and test/build it, no publish), and `publish`.
Only scheduled runs or explicit publish runs on the default branch can publish. Pushes to
`ops/orientation-automation` run a baseline check. All runs share a non-cancelling concurrency
group with the initial pinned-release pipeline.

When a future change is blocked, review it against the existing Orientation behavior, retain
all upstream features, and run tests/build plus device checks where behavior changes.
Update the canonical manifest and patch only after a reviewed integration is verified.
Never resolve conflicts by restoring entire old player files over newer upstream code.
Never retag or replace a published APK. Automated host tests do not constitute physical
phone/PiP/playback smoke testing.

Signing uses only the two repository Actions secrets:
`NUVIO_RELEASE_KEYSTORE_BASE64` and `NUVIO_LOCAL_PROPERTIES_BASE64`.
The keystore path is generated in the runner, and private files are removed at job end.
Required app identity: `com.nuvio.media`.
Required signer SHA-256:
`99e3d93e7600c178e71bf80ded2b1d97664e3ef14058c473c4617cb27fd04e35`.

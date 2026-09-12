# Orientation release channel

The installed Full ARM64 app checks only published stable `Mindplayer99/NuvioMobile-Enhanced`
releases named `X.Y.Z-orientation`, selecting exactly
`Nuvio-Enhanced-X.Y.Z-Orientation-Full-arm64-v8a.apk`. Drafts, prereleases, upstream APKs and
`0.4.14-orientation-final` are excluded. Android installation still requires user approval.

## Canonical source

The baseline is exact upstream **0.4.16**, `fdc8d77a6594d4eeb5c2129b379dab85c2d2d8ac`.
`manifest.json` pins the reviewed Orientation commit and SHA-256 of `canonical.patch`.
The 23-file delta contains Orientation state/persistence, Android effects, responsive player
controls and compact track sheets, the private updater channel, their tests and necessary
Kotlin multiplatform declarations. The only Gradle customization is an optional ABI list
using the supported Android splits DSL. Production passes `-Pnuvio.android.abis=arm64-v8a`.
No AGP internals or debug application-ID override are used. Upstream CVR no-compression and
configurable release minification remain intact.

Upstream now supplies lazy Settings search indexing. That downstream change is removed.
The unrelated Home Hero optimization and its custom test expectations are also removed;
Home Hero remains exact upstream. Historical patch notes are kept out of the app delta.

## Automatic integration and risk

The default-branch workflow checks hourly at minute 23 (GitHub scheduling may be delayed).
It selects the next published stable numeric upstream release, fetches the exact tag and
requires descent from the canonical baseline. It applies the patch with Git three-way
integration in an isolated index and creates a single-parent candidate on the COMPLETE
upstream tree. Before verification/publication it independently reproduces the entire
candidate tree; matching filenames alone is insufficient.

Preflight examines changed lines, Orientation/platform symbols, player session/lifecycle
references, updater channel/asset logic, package/signing declarations and intersections
with actual canonical patch hunks:

* **Hard review:** actual contract changes, competing Orientation APIs, meaningful canonical
  hunk overlap, unresolved three-way conflicts, package/signing or updater changes, or
  ambiguous/moved source/tag/version identity. Reports retain files, reasons and changed hunks.
* **Soft risk:** otherwise valid Gradle/dependency/build/workflow changes, navigation, themes,
  ordinary Settings/profile/player UI and other application changes proceed to objective gates.
* **Low risk:** orthogonal translations, documentation, artwork, metadata, baseline profile
  data and unrelated tests proceed. Canonical hunk conflicts still take precedence.

A clean textual merge is not proof of behavioral compatibility. A changed Gradle/workflow
pathname is not itself a compatibility failure. This classifier is deliberately bounded,
not a claim to understand arbitrary future code: compilation, tests and APK verification
remain mandatory.

## Test/build gates and inherited failures

Cheap Python integration/publication tests run first. Orientation/release-critical Android
host suites (player, updater and downloads) must all pass, with mandatory Orientation suites
present and no critical skips. Then one Gradle invocation runs the COMPLETE host suite and
Full ARM64 assembly with `--continue --parallel --max-workers=2`, reusing the daemon and common
compilation/configuration work. `--continue` permits assembly to finish after assertion
failures; it does not authorize publication. Existing setup-gradle caching is the only cache
system. Public task-outcome recording plus fresh XML distinguishes assertion failures from
compilation, assembly, missing-suite or infrastructure failure. Configuration cache is disabled
because the public task listener is incompatible with it.

When the candidate has noncritical failures, the exact untouched upstream commit is measured
under the same JDK/runtime configuration. For the first 0.4.16 migration only, the already-run,
pinned upstream Actions artifact can be reused. Every failing candidate test ID must match
upstream's exception type, assertion message (including numerical values) and relevant stack
frames. Only source line numbers, execution paths and object identities are normalized.
Missing upstream tests, new skips, additional failures, differing signatures or ANY critical
failure block release. There is no persistent list of exempt tests; later upstream versions
must establish their own equivalence. Full test evidence is tied to both source commits.

## Publication safety

All release pipelines share non-cancelling `orientation-releases` concurrency. Verification
requires exact source, package/version/versionCode, ARM64 only, Full native libraries,
non-debuggable APK and exact installed-app certificate. Tests/build evidence is mandatory.
Publication is draft-first: upload, download remote bytes, compare SHA-256, repeat APK
verification, then publish. Existing published tags/assets are never overwritten.
`orientation-current` advances only afterward with force-with-lease race protection. Failed
integration preserves every previous working release and records Actions summaries and
artifacts; Issues are also used if enabled (currently disabled).

Modes: `dry-run` performs candidate gates without publication; `baseline` only reproduces the
reviewed canonical tree; `publish` permits publication on the default branch. A no-newer-tag
run reports `up-to-date` without signing/building or duplicate publication. A reviewed one-time
maintenance workflow is restricted to its exact version/upstream/candidate, and is not part
of the default future updater workflow.

On a genuine review exception, inspect retained plan, semantic risk hunks and differential
test evidence. Integrate against the complete upstream tree, retain its features, and update
the canonical baseline only after the reviewed release succeeds. Never force ours/theirs or
restore entire older source files over upstream changes. Host tests cannot prove physical
phone rotation, PiP or playback behavior; the existing phone-verified Orientation code is
preserved, and device checks remain appropriate whenever that behavior changes.

Signing uses the existing `NUVIO_RELEASE_KEYSTORE_BASE64` and
`NUVIO_LOCAL_PROPERTIES_BASE64` Actions secrets. Private configuration is generated only in
the runner and removed at job end. Package: `com.nuvio.media`. Certificate SHA-256:
`99e3d93e7600c178e71bf80ded2b1d97664e3ef14058c473c4617cb27fd04e35`.

# Orientation UI update 2

Base: exact published 0.4.17 Orientation, 530f4cb483f8d211ddd7c5365ca7c516a9b69ad0.

Implemented: compact expandable recent searches before Discover; adjacent filters/results;
consistent Search/Discover hierarchy; Hero and Hero catalogs labels and Settings search terms.
Portrait subtitle navigation now separates languages, tracks and style, with a fixed Off action.
The selected track is scrolled into view on reopen. Audio names wrap without truncation.
Audio/subtitle menus suppress playback controls in both orientations. Feedback clears the measured
header. Media3 captions follow the actual portrait video content bounds and restore landscape layout
without Activity recreation; mpv plain-text subtitles avoid portrait black margins, preserving
landscape defaults and authored ASS styles. Tracking-unavailable messages explain the build limitation.

Not changed: orientation policy/persistence, requested-orientation effects, decoding options,
profile/account storage, downloads, addon networking, package, signer and production updater channel.

Metadata investigation confirms TMDB enrichment returns unchanged addon metadata when disabled or
missing an API key. No response from the user's configured addon/profile is available here; there is
no proven cast-rendering defect to fix. Settings use NuvioScreen's shared bottom-overlay inset;
the custom settings-search list adds the overlay padding explicitly. Existing scrolling header and
optional theme decorations are retained. These are not established defects.

Verification gate: focused Search/player UI and all orientation/updater/download tests, full suite
against the exact installed-release source, zero new failure signatures, signed Full ARM64 APK checks.
Missing tests, critical failures, compile failures and verification mismatches block delivery. Runtime
credential availability is reported as booleans only. Actual OAuth login and phone playback/frame-time
smoothness remain unverified. Experimental libass overlays require device validation separately.

Version 0.4.17-ui.2 / 122 is a manual-install prerelease, so later numeric upstream updates remain
installable. This branch does not advance orientation-current or replace existing releases. Canonical
carry-forward must be verified independently before automation activation.

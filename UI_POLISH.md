# Orientation UI update 3

Based on exact UI2 source c9d91d761ad49f3d482bde3e42de8eab2470bbaf.
Correct portrait caption coordinate handling for both nested and sibling SubtitleView layouts;
check complete layout before drawing, avoid double mapping bitmap cues, and retain clearance
above the measured portrait controls. Existing mpv behavior is retained.
Subtitle sheet keeps its height, uses equal-width language/Off actions and selected tabs.
Restore Search to Discover contextual heading with a short crossfade, respecting search focus/query.
Keep UI2 history grouping, Hero labels, audio wrapping and orientation policy/storage.

Verification includes real native SubtitleView drawing of text/bitmap cues in Fit, Zoom, Fill,
rotation and short windows, Compose interactions and screenshots, full regression comparison
with UI2, and signed Full ARM64 APK/package/version/remote-byte verification.
No physical phone is attached; real playback/device performance smoke testing remains outstanding.
VC-1 black-screen behavior is reported in both forks and is outside this UI correction.
Recordings did not establish a general loading-speed regression; no caching/network rewrite.
Trakt/Simkl credentials and matched metadata configuration remain external follow-up items.

Version 0.4.17-ui.3 / 122; manual-install prerelease. Canonical automation must carry the same
runtime, preserving all release gates. Previous releases and orientation-current stay unchanged.

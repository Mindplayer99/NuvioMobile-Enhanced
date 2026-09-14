# Orientation UI update 1

Based on the installed 0.4.17 Orientation source, `530f4cb483f8d211ddd7c5365ca7c516a9b69ad0`.

## Changes

- Search history comes before Discover. Three recent entries are initially visible; Show all/Show less
  changes presentation only. Existing history persistence, recording and deletion are retained.
- Discover filters stay adjacent to catalog results. Its section heading matches Recent Searches.
- Search remains the page title while scrolling; Discover no longer replaces it based on item index.
- Hero catalogs replaces Catalogs Source; the section is Hero; Settings search uses the setting name.
- Existing expanded/scrolled settings headers, decoration preferences and navigation padding stay intact.

No changes to rotation, playback, subtitles, sources, downloads, accounts, profiles, networking,
dependencies, signing identity, or the automatic release channel. This does not claim to repair
the separately identified player-overlay or integration-credential issues.

## Verification

The branch workflow renders and interacts with the actual shared browse header in the app's scrolling
container, checks collapsed/expanded/deleted history, saved state, large text and short landscape,
then runs every Android host test against both the exact baseline and candidate. Existing failures
must have identical signatures; missing tests, new failures and critical failures stop verification.
The Full ARM64 release is checked for package, version, original signing certificate, non-debuggable
status and Full native engines. Screenshots and reports are retained alongside the APK.

Real phone checks remain necessary: update in place, profile/library retention, search/filter/loading,
landscape scrolling, active playback rotation with retained position/tracks, subtitle and audio panels,
PiP/back, and custom download folder. Host UI tests cannot establish device frame-time smoothness.

Version name is `0.4.17-ui.1`; version code remains 122 to avoid blocking the next upstream update.
The UI changes are isolated on `feature/orientation-ui-polish`. They must be carried into the canonical
orientation patch before promoting a future automatic upstream integration; this branch does not
silently alter the existing release automation.

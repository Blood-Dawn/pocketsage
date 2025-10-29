# PocketSage Design Asset Guidance

The PocketSage repository intentionally avoids storing large binary screenshots. Annotated explorations for the UI live in our
design tools (e.g., Figma). Reference links and written callouts are documented in `../ui_inspiration.md` so contributors know
which visuals to inspect without bloating git history.

When new inspiration artifacts are gathered:
1. Add or update links + callout notes in `../ui_inspiration.md`.
2. Keep raw captures in the shared design workspace rather than exporting them into the repo.
3. If lightweight vector or text-based assets are required for documentation, prefer SVG or Markdown over raster PNGs.

This keeps the repo lean and makes future diffs easier to review.

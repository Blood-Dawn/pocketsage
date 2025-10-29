# PocketSage UI Inspiration Brief

This brief compiles observations from contemporary personal finance products so the PocketSage team can anchor typography,
color, density, and interaction decisions in well-tested patterns. Each product section below notes a public reference link and
describes the annotated callouts that should be recreated in Figma rather than storing large binaries in the repo.

## Comparative Insights

| Product | Typography | Color & Contrast | Data Density | Interaction Patterns |
|---------|------------|-----------------|--------------|----------------------|
| Mint (legacy dashboard) | Bold geometric sans hero numerals with lighter supporting labels to foreground balances. | Teal-to-navy gradient hero anchoring bright aqua CTA while cards stay neutral. | Snapshot cards surface three top categories plus alert ribbon without crowding. | Primary CTA + secondary text link, persistent top navigation, alert ribbon for notifications. |
| Monarch Money | High-contrast sans body paired with serif hero headline for a premium tone. | Deep purple gradient hero with gold accent CTA and muted neutrals. | Alternating content blocks keep large imagery balanced with concise copy. | Sticky trial CTA, inline testimonials, floating chat bubble for support. |
| Lunch Money | Friendly rounded sans with compact tabular font for ledgers. | Pastel pinks and creams with emerald accent CTAs. | Dense transaction table maintains legibility through thin dividers and generous padding. | Icon-led navigation rail, prominent “Try Lunch Money” button, hover reveals for category actions. |
| Tiller | Crisp geometric sans across hero and supporting copy. | White canvas with green accent band; product screenshots leverage spreadsheet neutrals. | Highlights detailed sheet preview while keeping hero copy focused. | Dual CTA stack (“Start Free Trial” + integration chips), resources mega-menu in nav. |

## Screenshot & Annotation References

Because the design team will produce annotated mocks directly in Figma, the repo tracks links and written callouts instead of
binary image exports. Use the following references when building the annotated deck:

### Mint (legacy pattern recreation)
- Reference: https://web.archive.org/web/20230501003736/https://www.mint.com/
- Capture hero balance card and alert ribbon.
- Annotate: large balance typography, gradient hero treatment, quick CTA row, alert banner styling.

### Monarch Money
- Reference: https://monarchmoney.com/
- Capture hero gradient, stacked CTAs, testimonial carousel.
- Annotate: serif/sans pairing, gold accent usage, sticky navigation behavior.

### Lunch Money
- Reference: https://lunchmoney.app/
- Capture transaction ledger and navigation rail.
- Annotate: spacing in dense tables, rounded iconography, hover affordances for category actions.

### Tiller
- Reference: https://www.tillerhq.com/
- Capture spreadsheet preview and dual CTA stack.
- Annotate: integration badges, white space strategy, CTA hierarchy.

## PocketSage Design Principles

1. **Information hierarchy first.** Use large, confident typography for top-line numbers and surround them with whitespace,
   mirroring Mint and Monarch Money. Secondary details should appear in lighter weights just below the primary figure.
2. **Color as structure, not decoration.** Adopt a restrained palette with one accent color for CTAs and alerts (Mint/Tiller),
   keeping data visualizations in harmonious, desaturated tones (Monarch Money’s cards, Lunch Money’s tables).
3. **Card-based summaries with drill-down paths.** Each dashboard tile should preview key trends (spending categories, cash flow)
   similar to Mint’s snapshot or Tiller’s sheet preview. Provide hover states or contextual links for deeper exploration.
4. **Sticky, inviting calls to action.** Position the main action (e.g., “Connect Accounts”) consistently in the hero or navigation,
   backed by a secondary textual link for users wanting more info, inspired by Monarch Money’s trial CTA and Lunch Money’s onboarding prompts.
5. **Trust through transparency.** Surface contextual cues like integration badges (Tiller), small print or alerts (Mint), and user
   proof points/testimonials (Monarch). This builds the credibility needed for financial tooling.

Use these references while drafting PocketSage layouts, adapting typography, spacing, and motion to maintain a cohesive, modern
experience that feels at home within the personal finance ecosystem. Document the final annotated screens in the design tool and
link them here once approved so future contributors can review the latest direction without navigating binary assets in git.

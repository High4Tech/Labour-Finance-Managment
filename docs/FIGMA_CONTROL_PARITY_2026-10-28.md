# Figma control correction — 28 October 2026

The earlier shared-control implementation was an approximation. Native bold classes, supplementary-help conversion and competing PLUS POINT styles meant even that approximation did not consistently reach the displayed controls. This correction uses the actual Figma component renders and measured geometry.

## Shared ownership

`ui_components.js` decorates the original Frappe input, not a second form or value store. `ui_components.css` owns the company-app control contract. All native field groups call this owner through `enhance_inputs` / `enhance_selectors`. Contextual new-category fields use the same owner. Plain creation checkboxes and textareas use the same visual variants.

| Component | Figma reference | Contract |
| --- | --- | --- |
| Input | 3531:403016, 3531:403052, 3531:403070 | 40px desktop, 8px radius, 16/24 value, 14/20 label and hint, 6px spacing, #cbd5e1 border |
| Textarea | 1238:358 | 128px initial body, 12/14 padding, native resizing, 12px original resize asset |
| Select / menu | 7953:158048, 7953:158255 | Original native value, 16px chevron, 42px menu rows, 6px menu padding, selected mark and keyboard highlight |
| Checkbox / radio | 1100:328, 1100:1424, 1100:334 | 20px control, 12px text gap, 16/24 label, 2px supporting-text gap; no invented outlined chips |
| Number / date | 11360:182469, 11363:183060 | Original 20px increment/decrement and calendar assets; stepper respects declared limits and native value parsing |

On mobile, form controls and choice labels retain a documented 44px touch variant. Teal replaces the source library's orange focus/selected accent to preserve the approved PLUS POINT brand. Original SVG dimensions remain unchanged. The menu's original orange tick is kept as supplied.

**Typography exception:** Neue Haas Grotesk Text Pro is named in Figma but is neither bundled with the project nor installed on this machine. The component font stack names it first and uses Arial as the local fallback. A licensed webfont is required for an exact typography match; no proprietary font was obtained or redistributed.

## Behavior preserved

- Native parsing, permissions, read-only/disabled fields, errors and form save methods.
- Native Link lookup, pagination, authorized contextual creation, calendar navigation and advanced list filters.
- Single open select menu, keyboard navigation/selection/Escape, focus restoration, route and dialog cleanup.
- Inline field corrections, associated accessible descriptions and required markers.
- Frappe/ERPNext/HRMS infrastructure and all business records. No schema or accounting changes.

Hints remain under inputs. Only contextual help appears in the help slot. Errors replace the hint in the same slot and highlight the real input. Older presentation overrides were removed or bypassed at their owners; no new observer, polling loop or package was added.

## Verification

- `browser-figma-parity.cjs`: eight real native control variants, Figma geometry, original image dimensions, numeric limits, read-only choice updates, keyboard values and six viewport/theme combinations.
- Shared controls and rate-card workflow: 8 checks passed.
- Agreement / event creation and client portal: 19 checks passed.
- Native filtering, lookup, contextual creation, imports and calendars: 11 checks passed.
- Inventory / vehicle reservation: 7 checks passed, with exact QA-fixture restoration.
- Stability / responsive editor: 5 checks passed; repeated visits bounded; 30 typed characters caused zero footer mutations, one enhancement pass, about 488ms.
- Automated AA scans in both themes returned no violations on the tested surfaces. This is not a claim of a complete manual WCAG audit. The exact light Figma border is retained; a `prefers-contrast: more` variant strengthens it.

The original 310 backend regression checks were not rerun for this frontend-only correction. Actual browser workflows exercise their save and validation interfaces. QA fixtures were cleaned; working-company controls were inspected without saving business records.

Visual evidence is generated locally under `.local/qa/figma-parity/`, including source renders, before/after control captures, geometry, original-asset measurements, responsive screenshots and a side-by-side comparison. Source screenshots are evidence only and are not used as UI assets.

Startup still requests 69 JS/CSS resources. PLUS POINT JS/CSS increased from 817,285 to approximately 830,006 uncompressed bytes during measurement (about 12.7KB); most additions are shared component CSS and native-control decoration. No performance speedup is claimed.

The help tooltip also follows Figma node 1052:587. Escape dismisses the tooltip and preserves the parent form. Source backup tag: `backup/pre-figma-parity-20261028` at `56a1464`. Private company backup completed with files at `20261028_131327`.

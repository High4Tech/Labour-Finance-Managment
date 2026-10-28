# Commercial flow and record navigation — 29 October 2026

## Changes

- Agreement deletion blockers now link to the same PLUS POINT event/agreement profiles used elsewhere. Event commercial snapshots resolve to their owning event. Blocker links use underlined teal text. Native forms and authorized advanced functionality remain available.
- Record status choices and the original native advanced filtering/sorting controls share one Filters panel. The shared owner moves existing controls rather than cloning their handlers. Exclusive All/Draft/Created choices use labeled native radios.
- Essential agreement commercial panels stay expanded: billing, resource commitments, sites/crew, vehicles and milestones. Conditions can still collapse. Event work details, spending controls and notes stay expanded.
- Form milestone actions use the important form-button treatment in section headings. Unsaved fixed milestones support Edit and Remove. Fixed-price completion payment fills the agreement end date and remaining contract value; values remain editable. Excess amounts highlight the amount field before saving. Focus returns to the Add milestone action rather than outlining the entire table.
- Daily billing supports **Pay after completion**, creating one bounded attendance period through the end date, plus the selected payment-days allowance. Daily, weekly, biweekly, monthly and quarterly schedules remain available. Existing invoice/attendance guards and invoice documents are retained.
- Customer completion actions require a payment milestone/schedule for dated agreements and events. Draft work remains editable. Dated events under an ongoing master agreement can define their own payment terms; a dated governing agreement continues to own its schedule. Missing governing terms have a direct, correctly routed action and are explained in review.
- Shared email controls wrap CC fields across available width, retaining comfortable input sizes. Add CC stays below the main recipient on the left; each CC remains a separate validated email input serialized through the existing delivery API. Delivery-off hides only the address grid and keeps its enabling checkbox visible. The regression also removed an obsolete rule that hid the whole checkbox section.
- Shared inline errors/toasts use a straight accent. Native dialog-show events apply the shared dialog treatment immediately, including single-section surfaces without nested card shadows. No new observer or polling loop was added.
- Event spending-budget inputs show the fixed client price or a clearly labeled estimate from client rates, crew quantities and dates. New-event and saved-event editors use the same helper.
- Each crew requirement has a labeled auto-select icon. Main and per-role auto-selection share a role/pay table and a read-only worker/cost preview. Daily pay can use individual profile rates or a common custom role rate. Monthly pay comes from each selected worker profile. Cost warnings require confirmation. Assignment rechecks availability and pay under the existing locks, rejects stale previews, and preserves partial assignment, missing-role guidance and Undo.

## Preservation and limits

No framework modules, DocTypes, database fields, accounting controls or native permissions were removed. No new package or schema migration was needed. Payment schedules plan invoices; they do not themselves approve attendance or post cash. Automatic selection does not change existing assignments. Recorded attendance and posted financial history retain their existing protection. Tests did not send real email or transfer money.

## Verification

**172 distinct backend cases have passing results.** The full 170-case regression passed with no failures/errors. The final 93-case targeted rerun covers workflow repairs, agreement architecture and hierarchy, including the ongoing-master payment and snapshot-blocker routing cases.

**41 browser scenario checks passed:** 11 commercial-flow checks, 11 native control checks, 12 responsive workflow checks, and 7 read-only company checks. Light/dark desktop/mobile AA scans and overflow checks cover the new pay and delivery dialogs; the broader workflow suite checks all event tabs in six viewport/theme combinations.

Changed Python sources parsed; changed JavaScript/browser scripts passed syntax checks; whitespace checks passed. Browser QA used disposable companies and verified cleanup. Backend business tests rolled back. Automated accessibility checks cover the affected controls and profile tabs, not a claim of a complete manual accessibility audit.

The read-only company smoke test kept before/after counts identical: 11 agreements, 5 events, 50 workers, 1 sales invoice, 1 worker loan, 6 agreement shares, and 0 planning drafts. No browser runtime errors occurred in the final company check.

### Performance sample against `cde3a4a`

| Measure | Before, two runs | After, two runs |
| --- | --- | --- |
| Dashboard readiness, ms | 7086 / 3257 | 3437 / 3449 |
| Period interaction, ms | 438 / 335 | 342 / 248 |
| Measured JS/CSS resources | 72 / 72 | 72 / 72 |
| Encoded asset bytes | 9,550,127 | 9,562,773 |
| DOM nodes | 13,126 | 13,126 |

Two dashboard charts were active and disposed on route departure. Asset size grew by 12,646 bytes for the added controls. The small timing sample shows no clear material regression; it is not a statistical speed guarantee. No business capability was removed to produce these measurements.

## Release and backup

Release assets: `20261029-commercial-flow-3`, including versioned lazy builder assets. Source backup tag: `backup/pre-commercial-flow-20261029`, at `cde3a4a`.

Private company database/config/public/private-file backup prefix:
`/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261029_002239-high4tech-events-fd166a217c_localhost-`.

Detailed local evidence is intentionally not published: `.local/qa/commercial-browser.json`, `commercial-unit-final.log`, `commercial-unit-targeted.log`, `commercial-responsive.log`, `commercial-native-controls.log`, `commercial-performance.json`, and `commercial-company-readonly.log`.

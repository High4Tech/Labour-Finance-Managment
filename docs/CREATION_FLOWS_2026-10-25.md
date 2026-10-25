# Agreement and event creation layouts

The supplied references are implemented as one shared editor scaffold in `flow_builder.js` and `flow_builder.css`: a vertical step rail, original form controls grouped into cards, comments/activity to the right, and a sticky Previous/Next footer. On small screens the rail becomes a scrollable row and the activity panel follows the editor. Existing teal action colors, typography and native fields are retained; the reference's unsupported DocuSign integration is not presented as a feature.

## Agreement

Five steps remain: client, agreement details, pricing/milestones, sites/crew, and send/sign. Date, scope, conditions and billing cards move the original controls instead of copying their values or replacing validation. A live final summary links back to the relevant steps. Draft status appears with the top actions. Creating the agreement and private signing link is the last-step action; creating a link does not send email. Fixed milestones and daily payment schedules retain their existing business rules.

## Event

New events and full edits share four steps: information, venues/crew, transport/equipment, and timeline. A new draft reviews the selected agreement's requirements before the existing create/schedule dialog creates the event. Individual assignments require that saved event; the interface states this explicitly. Draft dates inherit and are constrained by the agreement. Saved event fields retain the original project save and budget enforcement. There is one Save event control: at the top during editing and in the footer on the last step. It is moved only when changing steps, so an input change cannot interrupt a click.

Workers and Event pay are separate columns on profiles and full event editors. Up to three worker avatars plus the remaining count are shown. Either the avatar stack or pay value opens the original individual worker/pay/move controls. Mixed rates remain available without showing redundant worker-count captions.

## Timeline and loading

The staffing component opens in Timeline view, with a month axis and one bar per actual venue/category/phase. Bars show assigned/agreed daily crew; dates, venue and phase remain readable beside them. Week, Month and Year views retain the original attendance drill-down. Date navigation stays bounded to the saved periods. The timeline is a read-only presentation of requirements/coverage, not a second scheduling store.

When a hidden step is revealed or its width changes, the timeline brings the first scheduled bar into view. Its initial calculation is not reused from the wider, ungrouped editor. Manual scrolling is preserved while the width stays the same; no polling is used.

The initial Desk splash uses the existing Freddy thinking asset instead of the framework logo. Its gentle animation stops after three cycles and is disabled for reduced motion. Loading feedback also uses the existing bounded Freddy animation controller. No additional animation library, polling or external service is introduced. One ResizeObserver aligns the collaboration rail, and is disconnected when rebuilding the editor.

## Validation

- `scripts/browser-builders.cjs`: isolated QA agreement edits/conditions/review, invalid event date correction, four-step event creation, budget persistence, final Save placement; all nine editor steps at 1600px/390px in light/dark themes with automated WCAG A/AA and viewport overflow checks.
- `scripts/browser-event-layout.cjs`: real assignment/pay changes, resource dialogs, comments, private upload, agreement replacement/deletion review and six responsive/theme profile scans.
- `scripts/browser-profiles.cjs`: section saves, daily payment cadence, nested crew editors, draft comments, real creation/signing link without sending email, responsive profiles and popup scan.
- `scripts/browser-event-calendar.cjs`: real working timeline, retained attendance links, leap year/week/year boundaries, eight mobile theme/view scans, empty state and zero business-data writes.
- `scripts/browser-calendar.cjs`: native pointer month navigation/day selection in agreement, vehicle and worker fields, including dark mobile.
- Read-only working account smoke: saved profiles, full editor, signing controls and responsive header bounds.
- Delayed actual startup inspection: Freddy asset replaces the native logo, animation has three cycles and reduced motion disables it.

Initial checks found a timeline accessible-name mismatch, selected-step text contrast, a dark shortage badge contrast issue, and a Save button movement race. Repeated invalid-date correction also exposed shared blur validation reading the previous model value while native parsing was still updating. Date validation now reads the visible, correctly formatted date and moves focus only on explicit submission, preserving both typed edits and calendar clicks. These were corrected before final passing runs. Automated accessibility scans supplement the keyboard/visual checks; they do not certify all possible accessibility conditions. Exact QA companies and generated records are restored after each workflow test. Working company records are preserved.

Backup: `backup/pre-creation-flow-20261025` preserves the previous version at `df03881`.

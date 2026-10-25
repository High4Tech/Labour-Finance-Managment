# Event creation and staffing controls

The new-event wizard previously displayed agreement requirements as read-only previews in steps 2–4. Its actual creation action was on the final step, so the user reached Venues and crew without worker, pay or venue controls.

## Repair

- The initial **Create event and continue** action validates dates and details, saves the draft, creates the event through the existing business API and opens its full editor at **Venues and crew**. Choosing a later step in the rail uses the same handoff. Subsequent steps are the real staffing, resource and timeline components.
- **Choose workers**, individual daily/monthly pay, **Auto-select available crew**, **Add venue**, **Add crew category**, vehicle assignment and equipment reservation retain their existing validation and permission checks.
- The existing one-event-per-agreement/project rule is preserved. An agreement that already has an event shows an explicit explanation and **Open event and manage crew**. New-event fields are hidden in that case; existing names, notes, budgets and allocations are not overwritten. Completed-draft retries return the same event.
- Spending budget and budget enforcement are available before creation. Budgets use the agreement currency and are converted through its stored accounting rate. Invalid, negative or non-finite budgets are refused. Draft comments move to the created event.
- Scheduling remains optional. Its popup preserves values not shown there, including budget settings; closing it restores the same editable draft. Scheduled creation also preserves budget and comments.
- Editor observers are disconnected before replacing the content or leaving the route. No new polling, animation library or background loop is added. Covered staffing badges now use the theme's accessible success color.

## Verification

- `scripts/audit-workflows.py qa.localhost --event-start`: **28 tests passed**, including event creation, budget/currency, comment handoff, existing-event preservation, retry idempotency, scheduling, draft permissions, list states and related invoice regressions.
- `scripts/browser-event-start.cjs`: **8 checks passed**. The actual Events-list Create event button opens the creator; an invalid date is blocked; editing/cancelling the scheduling popup retains the draft and budget; continuing creates the event and opens live staffing; a worker is assigned at a chosen daily rate and that pay is edited; venue/category/resource dialogs and timeline remain available; an existing event is reused without overwrites. Desktop/mobile light/dark automated WCAG A/AA scans and viewport checks pass. No browser runtime errors.
- Updated `scripts/browser-builders.cjs`: **12 checks passed**, covering agreement save/conditions/review, the repaired event handoff, project budget persistence, all nine agreement/event editor steps at desktop/mobile sizes in light/dark themes, and final Save placement. No browser runtime errors.
- Both browser suites restore their exact isolated QA fixtures. Working company agreement/event records are preserved. Automated accessibility scans supplement visual and interaction checks; they are not a blanket certification of every possible state.
- Read-only working-account check: four Choose workers controls on the saved event, explicit existing-event guidance on New event, current asset versions, unchanged agreement/event catalogue, and no browser errors.

The working app asset versions are `20261026-event-controls-2`. This change requires no database migration.

Backup: `backup/pre-event-controls-20261026` preserves `3d74f10`.

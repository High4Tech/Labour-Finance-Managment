# Saved event layout

The supplied reference is used for hierarchy, spacing and action placement. The app retains its existing teal palette, typeface, native buttons, dialogs, tables, status colors and Freddy feedback. No new UI framework or external service is added.

## Information and behavior

- A compact header shows the event name, stable reference, date-derived state, Edit event and Daily attendance. More contains the existing agreement-replacement and guarded deletion actions.
- The context strip keeps dates/duration, client, linked agreement reference and every venue name visible.
- Event information keeps name/reference, client/venue, start/end, duration, spending budget, its enforcement setting and full notes. The native section popup remains available; the full editor is still an explicit action.
- Five keyboard-accessible tabs provide Overview, Crew and staffing, Transport and equipment, Timeline and Documents. Overview contains the operational sections together. Focused tabs move the original components, retaining their handlers and saved state. Actual inventory reservations stay with equipment instead of becoming a duplicate tab.
- Crew rows retain dates/phases, agreed and assigned daily coverage, fixed/daily client pricing and shortage/extra status. Compact avatars show counts and uniform/mixed pay context. Their popup exposes every worker, each daily/monthly rate, Edit pay and Move/unassign. Choose workers, automatic selection, venue creation and adding a category remain native operations.
- Agreed vehicle requirements remain separate from individual vehicle/equipment bookings. The original reservation component retains quantities, purpose, dates, status and edit/cancel actions.
- The original event timeline and finance link remain available.
- Documents combine event attachments with the agreement's attachments and identify their origin. Upload uses the native private FileUploader against the event. The plan read API adds permission-scoped file metadata; financial writes and business rules are unchanged.
- The right sidebar shows phase progress, comments and recent activity. Preparation/Event/Pack-down/Other phases derive from saved requirements. Missing phases say Not scheduled; their dates and completion are never invented. Shared collaboration components preserve comment validation, actual text and native activity data.

Updates happen after existing actions. There are no new polling loops, observers, packages or permanent page caches. Tab restoration is limited to the immediate save/upload refresh. Normal opening starts at Overview. Older Desk include lists recover the needed profile script and stylesheet before rendering.

## Verification

- `scripts/browser-event-layout.cjs`: **15 checks passed** with an exact disposable QA company. Covers popup saves, actual crew assignment/pay editing, move/venue dialogs, resource dialogs, comment errors/posting, private file upload, keyboard tabs, agreement replacement and deletion review. Six automated A/AA scans cover light/dark at 1536, 1024 and 390 pixels, with explicit title/action bounds and overflow assertions. All QA records and the uploaded file are removed afterward.
- `scripts/browser-profiles.cjs`: **15 existing regression checks passed**, covering agreement edits, payment cadence, nested crew popups, event/full editors, draft comments, creation-to-signing and accessibility. Both profile types retain their workflows.
- Working-site smoke: **8 read-only checks passed**, including the saved agreement/event views, section/signing controls, full editor, responsive header bounds and browser errors. The sample account's business data was not edited.
- Visual review covered desktop and mobile, including the populated working event. Contrast and accessible-name issues found during testing were corrected. Automated checks supplement visual/keyboard review and are not a complete WCAG certification.

Local evidence: `.local/qa/event-layout-20261025.json`, `event-layout-regression.log`, `event-layout-working.log` and light/dark viewport screenshots. Code backup: `backup/pre-event-layout-20261025` at `37ae977`.

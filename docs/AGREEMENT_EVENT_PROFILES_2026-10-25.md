# Agreement and event profiles

Saved agreements now open as a document profile. Saved events open as an operational profile with their crew board, resources and timeline visible together. Both have an explicit full editor. Agreement imports from the new-agreement editor still open the imported record in edit mode (`edit=1`).

Agreement sections support popup edits for client details, agreement details, conditions, pricing, site/crew requirements and vehicle requirements. They reuse the existing controls, tables, capacity checks and server save rules. Crew popup saves preserve the site's location. Unsigned links are revoked when agreement details change; signed snapshots and financial history remain protected.

Creation and editing include a comments/activity rail. New-agreement comments belong to its persisted planning draft and move to the agreement when it is created. The rail loads at most 50 comments and 20 recorded updates; it does not poll continuously. The final creation step has a **Create agreement and signing link** action. It saves the agreement, keeps the event draft, and opens copy/preview/email controls without sending email automatically. If outgoing email is unconfigured, the interface explains this and keeps link sharing available.

## Dates and recurring payments

- The editor no longer has a manual agreement status selector. Drafts remain drafts. Created agreements are Active through their end date and Closed after that date. An hourly job closes up to 200 expired agreements. Saving changed agreement dates recalculates the status.
- Daily pricing offers daily, weekly, every-two-weeks, monthly and quarterly payments. The user selects frequency and payment terms (0–90 days), not another pair of dates. Periods derive from the agreement start, retain their original day-of-month anchor, and truncate at its end. There are at most 400 periods.
- A scheduled job runs every 15 minutes, rotating through at most 25 agreements and creating at most 50 invoice drafts per run. It uses approved, unbilled attendance only. Empty periods create no invoices. Late-approved attendance can create a supplemental draft without rebilling earlier sources.
- Invoice posting dates use the attendance period end, and due dates follow the selected payment terms. The job does not submit invoices, post ledger entries, or send email. Native accounting validations still apply.
- Existing invoiced periods, invoice references and approved work remain protected. Uninvoiced schedules rebase when agreement dates change. Completed agreements can still invoice their approved work, and their existing events remain editable without reopening the agreement.

## UI and verification

The profiles use the existing Frappe component system and app tokens. Excess section dividers are removed. Shared scrolling tables are keyboard focusable and labeled; signing requests use the shared table renderer. Timeline date text has readable contrast and its visible labels remain in its accessible names. Nested action popups mount beside their parent dialog so saving the child cannot remove the parent mid-close.

Verification evidence is kept locally under `.local/qa/`:

- `profiles-backend.log`: **85 tests passed**, no failures or errors. Includes recurrence boundaries/leap years, limits, automatic closure, partial edits, draft comment transfer, exactly-once invoice sources, late approvals, draft invoice deletion, financial history, scheduling and field-validation regressions. Database fixtures were rolled back.
- `profiles-browser-20261025.json`: **15 browser checks passed**, including real saves for agreement and event profiles, section and nested crew popups, cadence setup, explicit editors, draft collaboration and creation-to-signing. Uses an exact disposable QA company and restores it after the run. No real email is sent.
- `agreement-import-handoff-20261025.json`: **10 import regression checks passed**, including automatic editor handoff, duplicate replay, batch choices, preservation of the earlier draft and two automated AA scans. Its exact QA company was restored.
- `profiles-working-smoke.json`: **5 read-only working-site checks passed** for the saved agreement document, section popup, operational event, explicit full editor and browser errors.
- Desktop/mobile automated WCAG A/AA scans cover both profiles; a section edit dialog is scanned separately. These checks are not a full WCAG certification.

Before installing scheduled jobs on the working site, its private native database/configuration backup was saved with timestamp `20261025_114850`. Code backup tag: `backup/pre-agreement-event-profiles-20261025`. Backups and screenshots are not added to Git.

The working, QA and demo sites have both jobs registered and enabled. The working site's first closure pass closed one expired agreement; the demo pass closed five. Installation created no financial postings. The working site's outgoing email account is not configured, so link sharing works while email sending is disabled with an explanation.

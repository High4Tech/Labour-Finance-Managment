# Agreement and event controls — verification, 26 October 2026

Implemented on the existing Frappe company app. This release completes the agreement sharing/document work and applies the same editing controls to events; it does not change the application architecture.

## Resulting behaviour

- Page save/commit actions use green; draft actions use amber; primary form actions use black; supporting actions use grey; destructive actions use red. Saving and Draft saved are quiet status indicators without an avatar.
- Small fixed-choice fields use accessible radio groups. Phase uses four checkboxes and persists combined phases without multiplying the crew requirement. Existing single-phase records remain readable.
- New events offer only active agreements without an existing event. Stale links or drafts for an allocated agreement open its existing event. Agreement dates populate the event and remain editable within the agreement period. Date edits preserve assigned workers and update inherited staffing spans safely.
- Event editing supports draft save/resume and the same live staffing, worker pay, transport, equipment and timeline controls as the creation flow.
- Add crew is ordered by site, category, workers per day, phase and client rate. Agreement crew and vehicle dates inherit the agreement. Site location belongs to Add site. Categories can be created from their selector. Availability accounts for requirements already entered in the current agreement.
- Review and share includes an optional explicit email checklist with validated recipient/CC. Creating a link does not send mail. A private client preview supports acceptance of a frozen agreement version.
- Agreement and invoice PDFs use A4 templates and private native File storage. Documents includes generated agreements, signed versions and related invoices, including invoices awaiting their first PDF render. Milestone invoice actions retain approval checks and reuse existing documents.
- Routine messages do not animate. Only one important Freddy message animates at a time, with pause/play and reduced-motion support.
- General icons use 50 locally stored Tabler symbols. Appearance uses locally stored Meteocons assets. Source versions, licenses and asset hashes are retained; runtime CDN access is unnecessary.

## Verification performed

| Check | Result |
| --- | --- |
| Backend regression suites | 137 unique tests passed, no failures/errors |
| Browser workflow checks | 32 checks passed, no runtime errors; exact QA fixtures restored |
| Final icon asset check | All 50 external symbols parse and render in the working browser |
| Static validation | Changed Python/JavaScript/JSON/SVG files validated; Git whitespace check passed |
| PDF inspection | Agreement and invoice are readable A4; signed agreement acceptance remains readable on its second page |
| Working account smoke check | 2 agreements, 1 event, 50 workers and 2 planning drafts retained |
| Working client preview | Opened anonymously and displayed agreement and signing fields; no email sent |

Backend coverage includes agreement/event creation, multi-phase requirements, date validation, worker assignments, payroll and billing flows, drafts, list integration, deletion, private document access, recipient/CC validation, frozen signing snapshots, invoice approval and PDF reuse. Browser coverage includes actual editing and creation controls, draft resume, worker pay, resource steps, signing, invoice PDF generation, document tabs, selection reset, typing stability and error handling.

Automated axe checks passed for the tested new/profile/dialog surfaces at desktop and mobile sizes in light and dark themes, using WCAG A/AA rule tags through 2.2. This is scoped automated evidence, not certification of every app screen or PDF accessibility.

Issues caught and corrected during verification included hidden email fields blocking creation when email was unchecked, reused form/dialog timing, old event drafts reopening the wrong view, missing invoice entries before PDF generation, private PDF delivery returning an empty response in this environment, and malformed nested SVG tags. PDFs now use authenticated base64 delivery and browser Blob previews/downloads; temporary URLs are revoked. The final SVG check explicitly verifies every symbol renders.

No real test email was sent. Mutation tests ran on the isolated QA site. Private signing tokens, rendered PDFs/screenshots and database backups are excluded from Git.

## Deployment and recovery

- Source backup tag: `backup/pre-agreement-sharing-20261026`, at `dc47d56`.
- Working-site database backup completed at 17:05 Asia/Karachi on 26 October 2026: `/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261026_170455-high4tech-events-fd166a217c_localhost-database.sql.gz` (1.3 MiB), with matching site configuration backup. Keep configuration backups private.
- Existing phase columns remain text-compatible; the PP Agreement Staffing and PP Event Staffing metadata were reloaded on QA and the working site. No new business tables were required. Existing records and financial history were retained.
- Cache versions were updated for the new controls and icon assets. Reload an already-open browser page once after deployment.

## Repeatable checks

From the repository root, with Docker services running:

```text
docker compose exec -T -w /home/frappe/frappe-bench/sites frappe /home/frappe/frappe-bench/env/bin/python /workspace/scripts/audit-workflows.py qa.localhost --release-controls
```

The release suite contains the final added sharing test too. Browser scripts: `scripts/browser-agreement-sharing.cjs`, `scripts/browser-event-start.cjs`, and `scripts/browser-ui-stability.cjs`. Run mutation suites serially against QA. They require the configured local Playwright runtime, admin credentials and axe installation. Private evidence stays in `.local/qa/`.

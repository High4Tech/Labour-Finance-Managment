# Event creation, review and document repairs — 29 October 2026

Fresh event creation, site reuse and the shared creation/review layout have been repaired. The existing Frappe/ERPNext/HRMS foundation, native permissions, advanced controls and posted financial history remain intact.

## Changes

- Removed a saved-event-only reference from the new-event screen. Both From agreement and Standalone now reach editable workforce controls. Dependency readiness checks match the calendar component version.
- Previous sites come from the client's source agreements, excluding duplicate event-only terms. Suggestions remain newest first and duplicate site names are consolidated. Selection applies atomically and clears field validation on the first click. Copying uses the new agreement's dates. The explanatory copy is attached to the information icon beside the checkbox.
- Setup, Event and Pack-down remain visible phase choices. An optional custom phase requires a description. Existing native Other values remain supported.
- The shared builder fills the viewport; the sticky footer aligns with the form column. Review summaries show useful client, scope, pricing, crew quantities and worker-days rather than only counts of requirement rows.
- Event review separates planned crew cost, recorded spend, projected total and budget remaining. Projected total is `max(booked crew cost, approved wages) + recorded purchases + recorded expense claims`; wages are not counted twice. Unassigned crew and unpriced resources are explicitly excluded from the projection.
- Selection cells use identical header/body insets. Selection-column widths are subtracted from the remaining table columns. Auto-pay date separators are valid UTF-8 and currency values use at most two decimals.
- Event overview starts with the staffing calendar. Crew coverage belongs inside Crew and venues. Event crew and resource sections stay open, and the duplicate shortage card is removed.
- The calendar centers the date selection, groups view/venue controls separately, and uses filled coverage badges. Selecting a day shows its attendance register or unmarked roster and the existing attendance/crew actions. Future dates cannot open attendance marking. Reading the calendar creates no attendance or financial records; requests are user-triggered and stale responses are ignored.
- Event and agreement Documents use the same file-list component: left file icon, descriptive filename, preview and download action. Generated titles include agreement/event context, reference and client. Existing file URLs and signed evidence are retained. Native filenames stay within the 140-character limit; internal deduplication hashes are hidden in displayed/download names. Event PDFs retain private File and company-scope checks.

## Verification

| Check | Result |
| --- | --- |
| Broader business regression suite | 183 passed, 0 failures/errors |
| Final focused business suite | 104 passed, 0 failures/errors; overlaps the broader suite |
| Disposable-company browser acceptance | 19 checks passed; no runtime errors |
| Existing company read-only review | Record counts unchanged; no runtime errors |
| Accessibility and responsive checks | Creation, site/custom-phase/pay/deletion dialogs and event profile checked at 1600px and 390px, in light and dark themes; automated WCAG A/AA scans passed |
| PDF behavior | Early estimated invoice generated, previewed and listed in Documents without creating a Sales Invoice; existing company private PDF content read successfully |
| Static verification | Changed JavaScript syntax, Python parsing and diff whitespace checks passed |

The browser checks cover a genuinely new event, inherited dates, standalone creation, worker assignment/pay, selected requirement edits, final save, attendance-by-date, inherited documents, PDF preview, first-click site reuse, custom-phase validation and agreement final confirmation. Test records belong to disposable QA companies and are removed afterwards. No client email or real payment was sent.

### Performance sampling

Compared with backup commit `a265136`, the dashboard still requests 72 JS/CSS assets. Transfer size increased from 9,585,705 to 9,588,626 bytes (2,921 bytes, about 0.03%). With the regression runner idle, two before/after samples showed readiness at 3.36–3.91s before and 2.83–3.14s after; period changes took 276–456ms before and 327–342ms after. These small samples demonstrate no observed material regression, not a guaranteed speed improvement. Dashboard chart instances still dispose on navigation. No new observer, polling loop or third-party package was added. Attendance is fetched when a calendar is rendered or a date/venue is selected; document lists load on demand.

### Backup and limits

- Code backup tag: `backup/pre-event-review-20261029`, pointing to `a265136`.
- Full company database/public/private-file backup completed before edits: `20261029_151409` in the site's private backup directory.
- This release needs no database migration.
- Automated AA scans supplement the layout and keyboard checks; they are not a claim of whole-product accessibility certification.
- Budget projections cover priced, booked crew and recorded costs; remaining staffing and unpriced reservations require administrator review.

Local detailed evidence is in `.local/qa/event-review-*.json`, logs and screenshots. These QA artifacts and site backups are not published to GitHub.

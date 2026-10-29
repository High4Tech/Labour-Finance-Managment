# Calendar navigation and supplied upload assets

Completed on 29 October 2026 for the company app. The earlier event creation and review work is retained.

## Delivered behavior

- One staffing calendar serves saved event profiles and the creation Review and create step. Timeline/Week/Month/Year controls sit on the left, the selected date is centered, and the venue filter sits on the right when present. Narrow containers stack these controls without overflow.
- The calendar initially selects today, including when today is outside the event period. Its visible date uses a short weekday, ordinal day, month and year. There is no duplicate range underneath it. Navigation and the native date picker remain available.
- Selecting a day exposes a link to the existing Attendance register, filtered by the event project, date and venue. The calendar no longer embeds a second worker roster. Reading the calendar and following this link create no registers or wage records.
- Completed event progress shows a checkmark. Upcoming and unscheduled rows have a muted grey surface.
- Owned tables keep action buttons in a horizontal row and pin the Actions column while data scrolls. This applies to dynamically refreshed crew rows as well as initial tables. Header selection and bulk controls remain available.
- The sticky creation footer spans the full main workspace beside the app sidebar, including the step-navigation column.

## Supplied design kit

The user-provided `Downloads.zip` contains 1,488 SVGs and 15 reference JPGs. The implementation imports only matching variants: 27 file-type icons, 239 country flags, the upload symbol and the existing Google Drive integration icon. There are 268 unique installed vectors totaling 333,878 bytes.

The upload reference is implemented using real HTML controls, native file selection and drag/drop. File rows show the supplied type icon, name, size, removal control and actual reading/upload status. The original CSV/XLSX limits, server preview, consent, atomic import and private attachment checks remain in place. A locally selected file is labelled ready for review, not uploaded or saved.

The same presentation adapter wraps Frappe's native uploader for agreement/event attachments, worker photos and company branding. Library access, image cropping, permission checks, authorized privacy controls and configured integrations remain native. General navigation/action icons retain the existing Tabler system. Unused social/payment/cursor assets do not imply new integrations or alter standard input cursors.

Country flags decorate native Country suggestions and selected fields; names, search, paging and keyboard selection remain native. Agreement and event document lists use the same file-type mapping and preview/download actions.

An additional issue found during acceptance was fixed: reopening an import could leave its hidden Company link temporarily empty. A fixed company supplied by the calling screen now remains authoritative for review and template downloads; server authorization is unchanged.

## Verification

| Check | Result |
| --- | --- |
| Import, planning and attendance backend suite | 83 tests; 0 failures, 0 errors, 0 skipped |
| Event/agreement creation and calendar browser suite | 20 checks passed |
| Upload and supplied asset browser suite | 10 checks passed |
| CSV | Real dummy row reviewed, approved and saved; replacing a file resets approval |
| Excel | Real XLSX workbook reviewed successfully with the supplied XLSX icon |
| File validation | Unsupported extensions, multiple-file drops and files over 2 MB rejected inline |
| Native attachment | Dummy text attachment uploaded privately; Library control retained |
| Attendance navigation | Native list opened with the selected project/date filters; register count unchanged |
| Tables/footer | Horizontal pinned crew actions and full-workspace sticky creation footer verified |
| Accessibility/layout | Automated WCAG A/AA scans in light/dark desktop and 390px layouts; keyboard upload and country selection verified |
| SVG safety/integrity | 268 hashes verified; no active SVG content or external references; country aliases resolve |
| Company read-only verification | 15 agreements, 7 events, 50 workers, 1 invoice, 1 loan, 8 signing shares and 0 planning drafts before and after; no browser runtime errors |

Dummy browser records and files were created only in a disposable QA company and removed afterward. Existing company data, financial postings and emails were not changed. Automated accessibility scans do not constitute a full accessibility certification.

## Performance and preservation

The change adds no package dependencies, global observers or polling. Native upload progress uses one subscription per open uploader, disposed when the dialog closes. Icons are local images fetched only when rendered; dashboard startup made zero requests for the supplied SVG set.

Compared with the preceding commit, total JS/CSS source grows from 1,631,068 to 1,657,113 bytes, an increase of 26,045 bytes. This is source size, not compressed transfer size. The asset library is not bundled into startup JavaScript.

Four alternating read-only local dashboard probes compared prior source with current source in the browser. Mean dashboard readiness was 4.95s before and 5.16s after, with individual samples spanning 3.71–6.62s. Shared number-layout work averaged 0.35ms in both versions; DOM size was identical at 13,348 nodes. The short settled mutation sample had the same mean in both versions. These development measurements show no clear regression within the observed variation; they are not production latency guarantees.

Frappe/ERPNext/HRMS modules, backend controllers, database fields, permissions, native filtering, accounting and stock functionality are preserved. No schema migration is required for this update.

## Recovery and reproducibility

The previous code is retained under `backup/pre-calendar-navigation-20261029` at `4c59e53`. Asset provenance and SHA-256 values are recorded in `public/images/design-system/manifest.json`; `scripts/check-design-assets.py` verifies installed SVGs. Browser acceptance scripts are `browser-calendar-navigation.cjs`, `browser-design-assets.cjs` and `browser-event-profile-readonly.cjs`. The performance probe is `browser-calendar-assets-performance.cjs`.

# Consistent record headers and staffing calendar

The new reference informs the event header, calendar summary and coverage presentation. Agreements and events now use the same dark teal `pp-record-hero` surface, with white text and the existing teal actions. A separate clipped decorative layer contains the curves while allowing the event's More menu to open normally.

The event header spans the record width and keeps dates/duration, client, agreement link, venues and total planned worker-days. Crew confirmation derives from daily coverage. Scheduled preparation/event/pack-down dates remain the source of phase progress; no confirmation dates or preparation dates are invented.

Overview places the staffing calendar at full width below the operations sections. The Timeline tab moves that same component into view. The existing finance link sits beside its section title. The calendar summary includes the event name, dates, duration, venues and planned worker-days. Scheduled cells explicitly show assigned and agreed crew; selecting one shows approved worker-days and the original attendance link when the work date is eligible. Future and unscheduled dates explain why attendance is unavailable.

Week and Month views use a Sunday-first grid with correctly positioned adjacent dates. Navigation is bounded to periods in the event data, including dates unique to another venue. Year views use actual week columns for both heatmap cells and month labels, including 54-column leap years. The component keeps only its local period/index and adds no polling, network request per day, package or persistent form cache. Older native event includes retain a fallback but cannot overwrite the new shared calendar.

All amounts, staffing coverage and attendance remain read from existing APIs. No schema, financial calculation, posting or account data changed.

## Verification

- **15 calendar checks** in `scripts/browser-event-calendar.cjs`: actual populated header, unclipped menu, worker-day summary, attendance link, leap February, visual weekday/date positions, week/month navigation bounds, leap-year heatmap alignment, December/January boundaries, multi-venue periods, empty data and six light/dark mobile AA scans. Boundary data is temporary browser-only data; no business records are created.
- **15 event layout checks**: crew/pay edits, venue and move dialogs, resource actions, comments, private uploads, agreement replacement/deletion review and six light/dark desktop/tablet/mobile scans. Exact disposable QA records/files are removed afterward.
- **15 existing profile regressions**: agreement editing, billing cadence, nested crew dialog, full event/agreement editors, draft collaboration, creation/signing and profile/dialog accessibility. One nested-dialog timeout passed on a clean repeat; there is no remaining reproduced failure.
- **8 read-only working-site smoke checks** verify that the populated event/agreement profiles and their editors still open without changing sample data.

Visual review identified an inherited worker-calendar `grid-column:1` rule and legacy 104px cell sizing that ordinary accessibility scans did not detect. Event weekday names and cell geometry are now scoped separately. Tests assert real element coordinates as well as date order.

Local evidence: `.local/qa/event-calendar-20261025.json`, `header-calendar-event.log`, `header-calendar-profiles.log`, `header-calendar-working.log`, `event-dark-header-working.png` and `event-calendar-working.png`. Automated checks supplement visual review and are not a complete WCAG certification.

Code backup: `backup/pre-event-header-calendar-20261025` at `1605cc2`.

# Event layout and staffing-flow fixes — 27 October 2026

## Delivered

- Moved the grey surface to the profile page canvas. Agreement/event content cards stay white; their faint heading bands reach both card edges. Supporting heading actions use a darker grey surface with a visible border.
- Event summary facts now use equally sized cards outside the shared dark header, matching the agreement profile hierarchy. Event notes align at the left edge with their icon. The More label is replaced by a named, keyboard-accessible three-dot menu.
- Shared tables use 14px column headings and 15px body text. Crew and payment tables have component-owned column proportions, reserving room for dates and amounts while limiting the action column. Narrow layouts retain a contained scroll area or the existing compact crew cards.
- Event venue dialogs use a consistent grid: venue/location, category and count, phase, prices, then From/Through together. Fields paint after their controls are ready. Dates default from the saved event and the calendar/input validation limits them to that event period.
- Changing event dates and leaving Event information now saves and refreshes the dependent staffing data first, including when clicking a step directly. New venue dialogs therefore use the updated dates rather than stale values.
- Invalid popup dates turn the corresponding inputs red, show the correction under those inputs, and stop before a save request. The server independently validates dates before creating a site and returns field-level errors. Radio/checkbox groups also receive error styling when invalid. Important modal error feedback can use the full available width.
- Auto-select crew stays hidden until a venue has an actual crew requirement. It appears inside the staffing card, assigns matching available workers, and disables once all requirements are covered. Add venue is the primary form action; auto-selection supports it.
- Renamed the event step/tab to Staffing schedule. Both timeline bars and calendar dates open a staffing review with Choose workers actions and the applicable full requirement date range. Worker selection shows venue, dates, count and client pricing. Attendance links become available on the work date; a future date explains when attendance opens. Approved worker-day details remain visible.
- Closing an action popup during its opening transition now completes without leaving a blocking overlay.

## Verification

| Checks run for this update | Result |
| --- | --- |
| Architecture, profiles/billing, event start, drafts, agreement sharing and currency backend regression | 71 passed |
| Focused event/layout/field-error/schedule browser regression | 11 passed |
| Full event creation, assignment, pay, transport and final-save browser journey | 9 passed |
| Working-site read-only calendar, leap-year, year-boundary, navigation and accessibility checks | 17 passed |

Total: **71 backend tests and 37 browser checks passed**, with no browser runtime errors. Tests include scoped automated WCAG AA checks in light/dark themes and desktop/mobile sizes, exact full-width heading measurements, column widths/font sizes, alignment of event fact cards, date persistence, early validation and rapid modal closing. This is automated coverage of the tested views, not an accessibility certification of every screen.

All mutation tests ran on exact disposable QA fixtures and restored them. Working-site calendar checks read records and exercise only browser state. No business data reset, financial posting, schema migration or outgoing email was performed.

## Recovery and delivery

Previous source version is retained by recovery tag `backup/pre-event-layout-20261027` (commit `182cc14`).

A full private working-site backup (database, public/private files and configuration) completed under:
`/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261027_122357-high4tech-events-fd166a217c_localhost-*`

Changed script/style URLs use `20261027-event-layout-1`; working-site and QA caches were refreshed together. Private backups, screenshots and QA logs remain outside Git. Evidence is in `.local/qa/event-repair-20261027.json`, `event-repair-backend-20261027.log`, `event-start-repair-20261027.log` and `event-calendar-repair-20261027.log`.

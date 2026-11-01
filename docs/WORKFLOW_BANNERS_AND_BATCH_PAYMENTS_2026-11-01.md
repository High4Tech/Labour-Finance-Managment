# Workflow banners, compact navigation and multi-event wage payments

## Changes

The side-road world has moved into four large banners at the end of Overview. They cover the client office/agreement, worker house/transport, warehouse/inventory, and event site. Each has a magnified roofless scene, a short popup-style text overlay and an orange contextual action. Frontages face a straight road; side-on vehicles travel horizontally along it. The office includes two people seated at the agreement desk. Vehicles and workers move slowly along roads contained inside the scenes, with alternating work poses. There is no perimeter road or reserved space beside dashboard content.

The banner component owns its markup, responsive layout, visibility observer and cleanup. Its 2048×1536 local atlas is 122,268 bytes and is requested only when the banners approach the viewport. No WebGL engine or 3D model loader runs on the dashboard. Scenes stay grey and frozen by default. Hover or keyboard focus enables colour and motion only in that banner. Motion also pauses off screen or when the page is hidden; reduced motion keeps it static. On mobile the text overlay sits below the model, within the same scene.

Collapsed navigation is now a 64px icon rail: full 22px icons, 44px link targets, icon-only search, no section-heading gaps, and an Expand navigation button. Expanded and mobile navigation retain their native structure and capabilities. Navigation SVG bounds are normalized for consistent optical size, using grey artwork and white selected icons.

Company list rows no longer show modification ages, comment counts, assignment/social metadata or hearts. The header heart is hidden too. Record history, comments, native filtering and permissions remain available inside the appropriate authorized views.

Loan amount and remaining balance both use the loan's accounting currency. The loan amount field is explicitly bound to its currency in the native DocType, and the loan list formatter uses that same record currency. A reporting-currency choice does not relabel or convert just one side of a loan balance.

## Charts, shortcuts and worker portraits

The existing ECharts curves and real-data calculations remain, with a stronger gradient area fill for the summary cards and attendance chart.

| Letter | Ctrl / Command: create | Alt: search |
| --- | --- | --- |
| A | Agreement screen | Agreements |
| E | Event screen | Events |
| L | Worker popup | Workers |
| W | Warehouse popup | Warehouses |
| V | Vehicle popup | Vehicles |
| C | Client popup | Clients |
| I | Equipment popup | Equipment |

Shortcuts use the existing shared creation forms. Editable inputs preserve native typing, copy, paste and select-all; selected page text can still be copied. Opening a tool is bounded against repeated in-flight requests, and closed resource/worker forms release their controls and DOM. Client search uses native Customer permissions and a 20-result bound.

A locally rendered PNG from the existing worker model supplies a passport-size fallback on worker detail pages only. Uploaded photos take priority. Tables and compact identities continue using initials when there is no photo, including first/last name initials for longer names.

## Multi-event payment batches

Record selected payments now accepts selected worker balances across events in the same company. One dialog reviews the workers, event names, each outstanding amount and the total, followed by the paying account, actual payment date, reference and confirmation that money was actually paid.

The server bounds the batch to 200 balances, rejects duplicate worker/event pairs and checks access to every event. It acquires project and worker locks in stable order, rechecks balances and uses the existing native Payment Entry / wage settlement workflow. Every selected event posts together, or all new postings roll back. Retrying the same confirmed batch returns its existing payments instead of posting duplicates. A worker may have separate earned balances in different events; those allocations remain separate.

No live wages were marked paid during browser testing. Financial posting and rollback tests used the QA database and rolled back.

## Frontend architecture

The PLUS POINT frontend is not React. It currently uses native Frappe with HTML, CSS and JavaScript, including shared design-system components and reusable form, table, dialog and flow helpers. It therefore already has a component system, but not React components. This update does not begin a React migration.

## Validation

- 68 rollback-only backend tests passed, including real multi-event posting, all-or-nothing rollback after a stale balance, duplicate retry protection, selection bounds, approved wage calculations, permissions, drafts, bookings and dashboard data.
- 49 dashboard/browser checks passed, covering the four banners, lazy art, reduced motion, collapsed icon boundaries and spacing, multi-event review, loan currency, hidden table metadata, popup behavior, Ctrl/Cmd creation shortcuts, Alt scoped searches, portrait isolation, filled charts and cleanup.
- 36 shared-header/navigation checks passed across primary routes, keyboard, mobile, light/dark and responsive states.
- 23 existing dashboard regression checks passed after replacing obsolete perimeter-road assertions with banner assertions.
- 19 interactive event-scene checks passed, including frozen preview, explicit lazy opening, pause/resume, failure recovery and renderer disposal. Main company record counts remained unchanged.
- Automated WCAG AA checks passed on tested dashboard and shell regions. This is not a claim of a complete manual accessibility certification.

The same-transport comparison used two isolated browser contexts per version at 1440×1100, baseline `4e33701`. The later baseline sample loaded 9,687,073 script/style bytes in 79 requests; the final version loaded 9,694,932 bytes in 79 requests (+7,859 bytes, about 0.08%). Both versions issued two dashboard API requests and mounted four charts. Route readiness varied from 5.0–12.6 seconds before and 5.3–6.4 seconds after; period interactions varied from 365–891 ms before and 533–758 ms after. These local samples do not establish a reliable speed improvement. Cleanup checks found zero active charts and no idle header updates or further requests after leaving the dashboard. The atlas and 40,158-byte profile portrait load only where used.

Both test and main sites migrated successfully for the loan field's display binding. No financial values or historical records were changed by that migration.

## Backup

Database and public/private file backup completed before the main migration:

`sites/high4tech-events-fd166a217c.localhost/private/backups/20261101_205352-high4tech-events-fd166a217c_localhost-database.sql.gz`

Public/private file archives share that timestamp. Git rollback point: `backup/pre-workflow-banners-20261101` at `4e33701`.

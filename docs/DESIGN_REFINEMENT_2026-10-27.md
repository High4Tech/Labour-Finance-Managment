# Shared design refinement and safe loading — 27 October 2026

This release follows the supplied design/performance guide and its Frappe preservation supplement. The application shell, teal brand and native business infrastructure remain in place. No database migration or business-data rewrite is required.

## Visible changes

- Agreement and event creation use the same fluid builder. The progress rail is 248–320px; the collaboration rail is 288–400px. Above 1600px, the heading and footer span both form and collaboration columns. At narrower desktop/tablet widths collaboration stacks below the form; mobile uses the existing horizontal step navigation. Page gutters scale from 16–40px.
- The empty native section wrapper labelled **Agreed work** is removed after its controls have been moved into owned panels. The scope itself remains editable in **Scope and deliverables**, is saved with the agreement, and remains part of client/document output. No scope field or value is deleted.
- Creation panels, agreement detail cards and record profile sections use `ui.heading`; creation cards use `ui.panel`. Light grey-green canvas, white panels, faint integrated heading bands, teal focus treatment and restrained depth remain consistent with the existing foundation.
- Page and card titles use responsive type tokens. Tables keep appropriate reading sizes and tabular numerals; financial columns in the shared table renderer align to the end. Mixed content and native report layouts retain their own semantics.
- Native list filters and sorting sit in a keyboard-operable **More filters** disclosure. The original controls, references, callbacks, operators and permissions are preserved. Quick search, record status and native applied-filter controls remain available.
- Large native Link pickers fetch one server page on demand. Search is debounced, stale results are rejected, superseded requests are canceled, and further results remain accessible through **Load more results**. Commands sit above the native results to avoid overlap. Supported, authorized entity pickers can open the existing creation dialog and select the saved record; canceling preserves the previous value. Administrative vocabulary such as Country/Currency is not given an arbitrary create action.

## Authoritative component contract

`public/js/ui_components.js` and `public/css/ui_components.css` own recurring surface and feedback presentation. The following adapters intentionally retain native behavior rather than replacing framework widgets.

| Component | Owner and consumers | Contract |
| --- | --- | --- |
| Section header/panel | `ui.heading`, `ui.panel`; builder, agreement cards, worker/resource profile sections | Shared card title scale, 1.4 title line height, 14px supporting copy, full-width soft heading band, 24px icon in 36px tint, 8px radius, subtle elevation. Actions wrap without overlap. |
| Metrics | `ui.metric`; agreement/event profiles | 44px centered icon area, 15px value, 14px label/note, wrapping text, tabular numbers, shared surface and focus. Dashboard money summaries use the larger metric token. |
| Buttons | Existing `choices.js`, `experience.css`, shared component styles | Semantic primary/support/draft/destructive variants; native loading/disabled behavior; visible focus; form-only dark action variant; existing teal/yellow draft progression. No new competing button API. |
| Inputs | Native FieldGroup/controls plus `forms.js`, `selectors.js`, `choices.js` | 40px desktop/44px touch controls, consistent border/radius, labels and help, inline errors and `aria-invalid`/`aria-describedby`, native Link validation, compact finite radio/checkbox choices. Read-only, disabled and loading states retain native authority. |
| Tables | `runtime.render_table`, shared table styles; planning, staffing, milestones, resources, financial summaries | Semantic table/header/row labels, existing responsive scrolling/card adaptation, controlled column weights for staffing/payments, numeric alignment, shared hover and empty state. Native list/report/stock grids remain native compatibility variants. |
| Alerts/toasts | `ui.feedback`, existing feedback hooks and shared CSS | Icon/content layout, semantic success/info/warning/error colors, inline field corrections, stable geometry; no avatar for routine save status. Existing important avatar hook remains optional. |
| Dialogs | Native Dialog plus `.pp-ui-dialog` | Existing focus handling, Escape/close and callbacks; centered desktop shell, bounded scrolling body, contextual sizes, consistent title/body/footer rhythm; mobile adaptation. |
| Disclosures/navigation | `ui.optional`, builder and native-filter adapter | Semantic details/summary or tabs, keyboard operation, selected/focus/disabled states and responsive rails. Advanced functionality remains reachable. |
| Loading/empty states | `runtime.loading_state`, `empty_state`, shared CSS | Existing green content loader and skeleton placeholder; native worker first-paint protection stays eager even when editor assets defer. Decorative motion honors reduced motion. |
| Themes/motion | `appearance.js`, shared tokens | Existing light/dark/system choice; theme-aware surfaces/text/semantic colors; 100/150/180ms press/hover/reveal tokens. Shared control transitions turn off with reduced motion. |

Spacing tokens follow 4px increments (4, 8, 12, 16, 20, 24, 32). Page title token scales 28–44px, card 18–22px, section 20–28px, prominent metrics 28–48px. The shared radius is 8px. Legacy native compatibility selectors remain scoped to the product theme or their precise owned component; no framework modules are replaced.

## Safe optimization and dependency audit

| Change | Dependency/behavior retained |
| --- | --- |
| Defer imports | `open_import` proxy loads the unchanged import engine through native `frappe.require`. Preview, validation, approval and transaction behavior remain server-owned. Concurrent opens share one load; failed loads can retry. |
| Defer staffing calendar | Operations explicitly awaits it; native PP Event Plan and Project consumers await the shared proxy. Week/Month/Year/Timeline and attendance/crew actions remain in the current calendar implementation. |
| Defer creation scaffold and its CSS | Loaded before the owned creation layout becomes visible. Existing agreement drafts explicitly request it too. Shared loading and worker first-paint rules stay eager. |
| Defer animation runtime | Loads only for an eligible important avatar. Reduced-motion, hidden/disconnected host and bounded animation checks remain. Public signing pages retain their own required include. |
| Remove duplicate old calendar fallback | Audited consumers: operations, event profile, native PP Event Plan and Project forms. They all use the current shared calendar/proxy. The current calendar, native hooks and business controller remain. |
| Remove three superseded CSS rules | Old 38px inputs, 112px textarea and absolute 11px error hint declarations conflicted with the existing shared 40/44px controls and inline correction contract. Current component rules replace only presentation. |
| Stable typing | Stage-dependent footer changes run only when the stage changes. Attribute values are not repeatedly rewritten when unchanged. Existing readiness/validation and draft updates continue. |
| Release discarded form calendars | Repeated-route measurements found four orphaned native calendars per cycle. `dispose_owned_forms` calls the native date-picker `destroy` method only before PLUS POINT-owned FieldGroups are discarded. It also cancels owned picker requests/debounce work. Native cached forms and active fields are untouched. |
| Narrow enhancement work | The existing bounded observer remains the sole enhancement observer; shared UI enhancements target visible pages/dialogs instead of every cached page. No polling, package or global observer is added. |

No backend module, DocType, database field, hook, controller, report, export, integration, permission rule, stock capability or financial calculation is removed. Native accounting, HRMS, stock/warehouse and authorized advanced views remain available. Hidden menu entries are not grounds for removing infrastructure.

## Measured evidence

Measurements use local QA in headless Edge at 1920×1200, the same six routes repeated three times and fresh authenticated browser contexts. Measurements include native Frappe assets. Raw encoded response sizes are not a production compressed bundle estimate. Route timing and heap samples are environment-sensitive; this is a local comparison, not a hosting benchmark or exhaustive leak proof.

| Measurement | Before | After |
| --- | --- | --- |
| Startup JS/CSS responses | 72 | 67 |
| PLUS POINT startup encoded bytes | 909,513 | 778,827 (14.4% lower) |
| Repeated footer mutations while typing 30 characters | 30 | 0 |
| Orphaned date pickers after repeated route cycles | 4 → 8 → 12 | 0 → 0 → 0 |
| DOM elements at the same settled route across three cycles | 13,913 → 14,149 → 14,385 | 13,684 → 13,678 → 13,690 |
| Registered enhancement callbacks | 10 | 10 |

Local route-ready medians from three visits per route:

| Route | Before | After |
| --- | --- | --- |
| Agreements list | 282ms | 214ms |
| Agreement profile | 535ms | 213ms |
| Agreement editor | 1068ms | 604ms |
| Event creator | 624ms | 344ms |
| Workers | 507ms | 212ms |
| Finance | 550ms | 261ms |

Some first visits add on-demand requests, as intended; later visits reuse the loaded feature. Route-level layout-shift observations vary with native list/profile replacement and are not consistently reduced; no CLS improvement is claimed. Typing did not reconstruct the footer. Final route heap samples ranged from 22.8–30.3 MiB, compared with 25.3–34.6 MiB in the baseline; these are samples, not a complete memory profile. The removed orphan calendars are separately verified through DOM counts and native instance teardown.

## Validation

- **297 backend regression tests passed**, zero failures/errors/skips. Coverage includes agreement/event architecture, drafts, signed changes, native permissions, attendance, wages, loans, stock/reservations, invoices/receipts, currencies and deletion safeguards. The rollback-only QA suite completed in 466 seconds.
- **19 agreement/event browser checks passed**, including actual agreement creation, event staffing, worker assignment, final save, client link/signature/CSRF behavior, lookup failure recovery and inline validation.
- **7 resource browser checks passed**, including real equipment reservations, insufficient-stock correction, own-reservation editing, vehicle allocation/conflict filtering and popup accessibility.
- **11 native-control/loading checks passed**: deferred assets, original advanced filters and sorting through keyboard disclosure, >200 choices with on-demand paging, native keyboard selection without accidental dialog submission, cancel/create-and-select client, import dialog loading once, four calendar views with crew action, reduced motion and no browser runtime errors.
- **5 responsive/performance checks passed**: discarded calendars released, bounded repeated-route DOM, stable footer typing, no empty Agreed work wrapper, no runtime errors. Agreement editor checked at 320/390/768/1024/1440/1920/2560px in light and dark. Automated WCAG A/AA checks found no violations in those tested editor states. The event profile and reservation popup were also checked in both themes at their desktop/tablet/mobile sizes by the browser suites. System theme uses the existing shared theme tokens; reduced motion is separately exercised. These checks do not constitute a complete manual screen-reader certification.
- **5 read-only working-site checks passed**; agreement/event profiles, Finance and client-link actions load, sidebar automated AA checks pass in both themes, and record counts are unchanged: 6 contract-term records (including internal event bases), 4 event plans, 50 workers, 1 invoice, 1 worker loan, 4 share records and 6 planning drafts.
- Modified JavaScript passes Node syntax checks. No new dependency or database migration is introduced.

Repeatable scripts: `scripts/browser-design-refinement.cjs`, `scripts/browser-native-controls.cjs`, `scripts/browser-context-ui.cjs`, `scripts/browser-resource-allocation.cjs`, and `scripts/audit-workflows.py --architecture-regression`. Evidence JSON, before/after screenshots and test logs remain in ignored `.local/qa/`; wide/mobile light/dark screenshots use the `refinement-` prefix. Test records were confined to exact disposable QA fixtures and restored after the checks.


## Recovery

The pre-release source is commit `ea0c9e748f994ab9c4dd609a446efd5a409fc40a`. The company site's database, configuration, public and private files were backed up under its private backups directory with prefix `20261027_211419-high4tech-events-fd166a217c_localhost`. Backup data and local browser evidence are excluded from Git.

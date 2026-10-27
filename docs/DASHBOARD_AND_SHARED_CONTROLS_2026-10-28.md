# Dashboard, rate-card inheritance and shared controls — 28 October 2026

## Scope and audit

The customer Overview now uses the requested dashboard composition. The platform administration dashboard retains its original renderer. Existing Frappe/ERPNext/HRMS DocTypes, permissions, advanced filters, accounting, stock operations, reports and exports remain available. No dependency or database migration was added.

The old customer presentation used oversized metrics, a 900px workspace limit, repeated home tools and a two-column analytical layout. It also offered independently editable crew prices alongside the negotiated rate card. The shared input implementation had separate native and product sizes, and ordinary Select controls used an operating-system menu.

The implementation improves the shared owners in `public/js/ui_components.js`, `public/css/ui_components.css`, `forms.js`, `selectors.js` and `runtime.js`. Customer dashboard composition is an on-demand consumer in `dashboard_analytics.js/.css`. Backend providers use permission-checked native records in `dashboard.py` and `dashboard_analytics.py`.

## Dashboard and data mapping

The centered customer canvas is capped at 1320px. Available space determines the number of columns, including when the native sidebar is visible. Four KPIs appear in one desktop row. Amounts start at 32px and fit the available width; exceptionally long values use the card's full width. Exact text remains available to assistive technology. There are no invented trend percentages or decorative data series.

| Component | Authoritative source and meaning |
| --- | --- |
| Active workers | Current active native Employees in the selected company. |
| Active work sites | Active sites belonging to the company's readable financial projects. |
| Revenue earned | Existing project-finance provider: approved daily work and approved fixed milestones, lifetime. |
| Wages unpaid | Existing approved-work balance after linked posted payments and recoveries. |
| Approved worker-days | Approved PP Work Entry units grouped by actual work date within the selected period; a half day contributes 0.5. This is not an attendance percentage. A single-day period uses a bar to avoid a degenerate line. |
| Workforce by site | Current assignment records at active, open sites, excluding draft events. The center and percentages use the same assignment denominator; they do not claim unique people. |
| Revenue vs wages | Monthly aggregates of dated approved daily client charges and approved wages. Fixed milestone revenue remains in lifetime KPIs because its due date does not establish an earned date. |
| Events | Native lifecycle status; Active, Upcoming and Draft remain distinct. Shows up to five records with a link to the full list. |
| Needs your attention | Existing conditions, priorities, notification read state and contextual actions. |
| Recent work activity | Five most recently updated approved work entries, with their actual worker/date and an attendance link. |
| Outstanding worker wages | Approved wages less posted wage settlements and loan recoveries, grouped by worker; no invented payment deadline. |
| Business details and work history | Existing financial snapshot, invoice/cash balances, contribution, client activity and budget information remain available through a disclosure and report links. |

The chart-period control changes only the dated analytical series. Current and lifetime cards are explicitly labeled and are not silently reinterpreted. Native Frappe Charts supplies tooltips; keyboard-accessible data disclosures expose exact chart values. Empty and failure states are local and retriable.

The original Attendance → Approved work → Worker earnings / Client billing SVG paths and signals are retained, centered at the bottom. The extra marketing copy is removed. Motion follows visibility and reduced-motion preference. Page loading uses the shared green avatar once; chart-level loading uses skeletons without repeating the avatar.

## Rate-card ownership

For a daily agreement using **Rate card**, one negotiated price exists per category. Crew rows and daily payment estimates inherit that price immediately in the editor. The crew popup shows the inherited value and a source explanation instead of another editable rate. An unpriced category is highlighted at the category field and cannot be committed.

Server validation enforces the same rule, including API and native-form saves. Currency-tagged prices pass through the existing accounting conversion once; the crew price then comes from the normalized rate card. Categories missing a negotiated price are rejected. Fixed agreements retain their separate milestone pricing.

Saving changes still respects the existing agreement-approval boundary. Signed/shared agreements require client approval or recorded company attestation. Previously created events retain their own commercial snapshots and approved work/financial history. Opening an editor does not rewrite those records.

## Shared Figma component contract

The supplied Figma file was inspected through component metadata, screenshots and detailed default/focused/error/disabled variants: [inputs and textareas](https://www.figma.com/design/NU1SlgUvw6zmalvW1Qhj6K/?node-id=1238-278), [Select and menu components](https://www.figma.com/design/NU1SlgUvw6zmalvW1Qhj6K/?node-id=11132-11643). The base-components divider was resolved to its actual Inputs and Select pages.

| Property | Shared customer contract |
| --- | --- |
| Labels and helper/error text | 14px / 20px; medium labels, regular supporting copy; 6px separation. |
| Standard controls | 42px high; 16px / 24px values; 8px radius; 12px horizontal padding; subtle 1px/2px shadow. |
| Textarea | 128px minimum, 12px × 14px padding, 16px / 24px text; native vertical resizing. |
| Native list filter variant | 40px desktop, 44px mobile; 14px / 20px text, aligned input, match operator, sort and scope controls. |
| Focus, error and disabled | Teal focus treatment without a geometry jump; semantic red input and associated correction; disabled/read-only states retain native behavior. |
| Help targets | 16px Figma glyph inside a 24px keyboard-focusable target. |
| Select/menu | 8px surface radius, 6px menu inset, 42px options, selected check, hover/active treatment, viewport-aware positioning and overflow scrolling. |
| Search and keyboard | Search for more than eight options; arrows, Home/End, Enter, Escape, Tab and open-menu typeahead. Escape restores focus. |
| Themes and motion | Existing light/dark/system tokens and reduced-motion behavior. Teal branding and the installed app font are preserved. |

The Figma orange focus color and low-contrast border were adapted to PLUS POINT teal and the existing accessible border token. The proprietary design font was not downloaded or introduced. Five supplied SVG glyphs are stored locally under `public/images/figma/`; no expiring Figma URL is used at runtime.

Plain rate-card inputs also delegate numeric restrictions, positive-value validation and inline feedback to the same shared field rules. The original native Select remains the value/validation authority behind the shared visible combobox. Native onchange handlers, options, disabled state, field errors and permissions remain intact. Read-only fields without an input are left intact. Finite radio/checkbox choices and the native Link/Awesomplete picker retain their existing behavior. Native advanced filtering remains available through the existing contextual disclosure.

There is one open Select menu, no new global observer or polling loop, and initialization is idempotent. The existing bounded enhancement pass is reused. Menus close on navigation, modal disposal or anchor movement; queued focus scrolling does not immediately dismiss a newly opened menu.

## Performance and lifecycle

Native chart instances, resize observers, requests and owned references are released when leaving Overview. Delayed native chart callbacks cannot redraw disposed hosts. Repeated navigation verifies zero active customer charts away from Overview and three for populated analytics on return.

Startup samples compare the same working company before and after the change. Route and typing samples use equivalent disposable QA fixtures from the preceding source version:

| Measurement | Before | After |
| --- | ---: | ---: |
| PLUS POINT JS/CSS transferred on Overview | 778,825 bytes | 817,285 bytes |
| Overview JS/CSS resource count, including framework | 67 | 69 |
| Startup DOM nodes | 12,678 | 13,007 |
| Startup heap sample | 20.36 MB | 21.65 MB |
| Footer mutations while typing 30 characters | 0 | 0 |
| Typing sample | 484ms | 497ms |
| Warm agreement editor | 573ms | 604ms |
| Warm event creator | 341ms | 334ms |
| Warm worker list | 179ms | 167ms |
| Warm finance view | 249ms | 228ms |

The additional ~38KB and two resources provide the new shared controls and lazily loaded customer analytics. No chart package was added. These local samples show bounded navigation and stable typing; they are not a claim that every route became faster. Dashboard date queries are bounded to supported periods and aggregate approved amounts in the database. Financial loading does not post ledger entries.

## Verification and recovery

Final results:

- **310 backend tests passed**, zero failures/errors/skips, in 649 seconds. Includes nine dashboard cases and four new rate-card cases, plus native permissions, agreement approvals, drafts, events, attendance, wages, loans, stock/reservations, invoices, currencies and deletion safeguards.
- **19 workflow browser checks passed**, including actual agreement/event creation, worker assignment, client signing/CSRF, local retry, inline corrections, responsive AA and aligned desktop/mobile filters.
- **7 resource browser checks passed**, including real stock/vehicle reservations, own-reservation editing, availability conflicts and popup AA.
- **8 Figma/control browser checks passed**, including search/keyboard behavior, disabled/read-only controls, inline errors, numeric restrictions, missing-rate prevention and inherited pricing without premature saving.
- **9 dashboard browser checks passed**, including truthful empty data, six widths in both themes, oversized/negative/zero amounts, period changes, keyboard chart data, retries, SVG preservation, reduced motion and bounded chart cleanup.
- **11 native-control checks passed**, preserving advanced filters, sorting, paged Link pickers, contextual creation, import loading and the calendar's views/actions.
- **5 responsive/performance checks passed**, including seven editor widths in both themes, stable footer typing, bounded repeated navigation, datepicker disposal and no runtime errors.
- **5 read-only working-site checks and 4 platform preservation checks passed**. Company record counts remained identical. The administrator dashboard retained its original renderer and native controls without loading customer analytics.

Repeatable checks are `scripts/browser-dashboard.cjs`, `scripts/browser-figma-controls.cjs`, `scripts/browser-context-ui.cjs`, `scripts/browser-resource-allocation.cjs`, `scripts/browser-native-controls.cjs`, `scripts/browser-design-refinement.cjs` and `scripts/audit-workflows.py --architecture-regression`.

Local evidence, screenshots, logs and performance JSON are in ignored `.local/qa/`. Dashboard screenshots cover 390px/1920px light and dark; control/menu screenshots cover 390px/768px/1600px. The builder performance suite covers 320/390/768/1024/1440/1920/2560px. Automated AA evidence applies to the tested views/states, alongside keyboard and visual inspection.

The previous source is `d3ae3044470e5cad5983deb795f8f8ea59f2c734`, tagged `backup/pre-dashboard-controls-20261028`. The company site's database, configuration and public/private files were backed up under its private backup directory with prefix `20261028_001814-high4tech-events-fd166a217c_localhost`. Private backups and company screenshots are excluded from Git. Working-site checks compare record counts before/after without editing company records.

# Overview — supplied Figma design

Reference: [Labor Management System, frame 23:16714](https://www.figma.com/design/jZ63XyjbXM1v4evqYuzQLD/Labor-Managment-System?node-id=23-16714). The supplied `Desktop.svg` and screenshot describe the same 1440 × 1998 desktop composition. The linked 23:16713 node is its containing canvas.

## Component ownership and appearance

- Primary orange is `#FF5800`. `brand.css` updates shared primary controls, navigation and focus/accent variants. Semantic success, error, warning and neutral colors remain semantic. Small text on orange uses navy ink for AA contrast; decorative orange remains the exact supplied color.
- The native shell is restyled, not rebuilt. Platform administration, native permissions, advanced filters, reports, warehouse functionality and accounting remain available.
- `ui.overview_metric` is the shared analytics panel's financial-card variant. `dashboard_overview.css` defines its title band, value fitting, spacing, border, radius, shadow, sparkline, responsive and dark contracts.
- `ui.badge(..., {variant:'outline-dot'})` owns the outlined status treatment; other consumers retain the default pill variant.
- Summary tables use existing `render_table(..., {selection:false})`. Workers supplies page-scoped selection and existing permission-checked deletion review. Operational tables retain their default bulk controls and sticky actions.
- Inputs, date validation, dialogs and theme menus use shared/native controls. Figma icons and the High4Tech wordmark are local assets. Actual worker images or initials replace sample people.
- The static workflow footer is the supplied illustration, not an image replacing live application controls. It has a text alternative and keyboard-accessible scrolling on phones.

Desktop uses a 264px sidebar, 24px main gutter, three financial cards, paired operational tables and a 240px activity rail. Attendance spans two equal panels, followed by the searchable five-row Workers table and workflow illustration. Smaller screens reflow panels and preserve table scrolling. Light, dark, system and reduced-motion modes share the component geometry.

## Real data

`dashboard_view.view` is read-only, manager-authorized and company-scoped. It excludes archived projects and does not write records or cache financial results.

| Display | Native source / meaning |
| --- | --- |
| Revenue Earned | Existing financial-report lifetime earned revenue, including approved fixed milestones |
| Unpaid Wages | Existing report's current unpaid approved wages |
| Total Loan | Submitted loans minus submitted recoveries, never negative per loan |
| Sparklines | Selected-period approved daily billing, earned wages and loan disbursements, respectively |
| Event progress | Assigned worker-days divided by planned worker-days, capped per requirement |
| Milestones | Uninvoiced fixed milestones and daily checkpoints, earliest due first; future daily amounts say Attendance based |
| Attendance Rate | Present-equivalent units divided by approved eligible register entries. Half day = 0.5, absent = 0; full-day leave is excluded from the eligible roster |
| Attendance Register | Latest four registers in the selected period, with native event, venue, date and approval state |
| Worker balance | Approved wages minus submitted settlements and recoveries, with unlinked events excluded from financial scope |
| Worker status | Active state plus current dated assignments; draft/cancelled plans do not claim an active booking |
| Activity | Native timestamps; seven entries visible and up to 25 in View all. Draft attendance is explicitly labelled |

Currency is projected exactly once through the existing exchange service; stored values are unchanged. No fake growth percentages, sample points, task counts or due dates were added. Cards describe current/lifetime balances; charts and attendance use selected dates.

## Assets and loading

Inspected Figma sections: sidebar 23:16717/16726; header 23:16918; metrics 23:16957; tables 23:16991; activity 23:17050; attendance 23:17179; workers 23:17251; workflow 23:17300. Matching exports live in `public/images/dashboard/`. No expiring Figma URLs or large reference SVG load at runtime.

The existing modular ECharts 6.1.0 engine is reused; no extra chart package was added. Overview and charts remain lazy features. The dashboard does not load Three.js/event-world code. One abortable request updates the combined projection; search is debounced by 350ms. There is no dashboard polling. One owned resize observer coalesces resizing through one animation frame. Four charts exist on Overview, zero after leaving; returning mounts four fresh instances. Errors preserve figures and offer local Retry. No new global observer or native-framework override was introduced.

## Verification

- **71 rollback-only QA tests passed**, covering scope, conversion, no-write guarantees, event/agreement workflows, approved attendance, wages, leave, loans, billing and receipts. An existing date-sensitive payroll test now accounts for earnings spanning calendar months; the payroll rule is unchanged.
- **28 browser checks passed**, including native worker-list and agreement/event profile navigation: balances/assets, search/filter/pagination/selection reset, dates/periods, activity, theme menu, error/retry, long amounts, disposal and no browser exceptions.
- Six widths (320, 390, 768, 1024, 1440, 1920) passed in light/dark without document overflow. Automated WCAG A/AA checks at 390/1440px passed in both themes. These are scoped automated checks, not a full manual certification.
- Sampled idle window: **zero DOM mutations and zero dashboard requests** over 1.5 seconds.

Reproduce with `scripts/browser-overview-design.cjs` and `scripts/audit-workflows.py qa.localhost --dashboard`. Ignored evidence/screenshots: `.local/qa/overview-design/` and `.local/qa/dashboard-20261101-backend.log`.

## Performance

`browser-overview-performance.cjs` serves source commit `392e637` only into isolated baseline contexts against the same company/server. It never deploys older code. Two cold samples per version are diagnostic. Interactions compare each design's period control. Baseline byte counts include intercepted source bodies rather than recording them as zero.

| Measurement | Previous | Updated |
| --- | --- | --- |
| Cold readiness | 3,315 / 3,390ms | 3,458 / 3,619ms |
| Period interaction | 390 / 328ms | 577 / 253ms |
| Uncompressed JS/CSS | 9,611,646 bytes | 9,637,161 bytes |
| JS/CSS requests | 74 | 75 |
| Dashboard API requests at readiness | 3 | 3 |
| DOM nodes | 13,127 / 13,127 | 12,951 / 12,951 |
| Used JS heap | 25.10 / 26.36MB | 26.28 / 26.56MB |

Tradeoff: approximately **25.5KB** more JS/CSS and one stylesheet request. The chart engine is unchanged. Cold readiness averaged 3.54s versus 3.35s (about 0.19s additional time) in this small final run; period interaction timings varied. Four charts now render for this company versus one populated chart previously. These diagnostic samples cannot establish a general speed or memory improvement. Evidence: `.local/qa/overview-performance.json`.

Backup source tag `backup/pre-orange-overview-20261101` preserves `392e637`. No database migration is required.

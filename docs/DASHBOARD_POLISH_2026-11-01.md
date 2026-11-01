# Company dashboard and shared shell refinement

The company overview renders its own skeleton immediately. It no longer briefly displays the legacy operations dashboard and setup links. Business setup/actions were removed from the overview presentation; native Frappe, ERPNext and HRMS capabilities, permissions, reports and advanced views remain available.

## Shared components and behaviour

- White labels/icons on orange primary actions and selected navigation. The exact Figma orange `#ff5800` remains the accent; white-labelled surfaces use its darker accessible action tone `#cf4600` (hover `#b83d00`).
- Search retains the native command search and keyboard behaviour, anchored under the sidebar search field. Notifications reuse the native tabs, read state and settings under the header bell.
- KPI tooltips render outside clipped chart cards. Chart data opens in a native dialog.
- Embedded dashboard tables use the shared native-list variant: 15px body text, 14px headings, 24px line height, aligned selection and visible icon actions. Activity symbols identify their entity independently of status colour.
- Help has annotated real components, workflow links and a screenshot of an example form. The publicly served example contains no company or client data.
- Attention items are persistent, dismissible corner toasts with relevant action links. Closing them lasts for the current app session; no business state is changed.
- The business workflow is a shared SVG with signal dots. Animation stops offscreen, when the page is hidden, and for reduced-motion preferences.

## Decorative journey and performance ownership

The wide-screen perimeter shows agreement, crew, warehouse, venue, delivery, attendance, approved work and billing checkpoints. Workers and a vehicle move according to scroll progress. This is decorative context, not an operational simulation or new source of business truth.

- Uses the local event-world asset kit. The optional event scene also consumes the shared van factory.
- `scripts/build-dashboard-journey.cjs` renders eight shapes into one 60,384-byte PNG atlas. The dashboard never loads Three.js, a model file, or a WebGL renderer.
- The optional journey loads after figures/charts are ready, during an idle opportunity. Its layout gutter is reserved up front on screens at least 1600px wide. Narrower screens keep the readable dashboard and compact workflow diagram.
- One passive scroll listener with coalesced animation frames; no autonomous JavaScript render loop, polling, global observer, or third-party runtime dependency. Existing dashboard resize ownership is reused. All listeners, idle callbacks, observers, nodes and charts are cleaned up on navigation.
- Shared chart instances update in place. Worker searches, pagination and status changes skip chart work when their chart data is unchanged.

## Verification

- **71/71 rollback-only QA tests passed:** dashboard analytics, operations, currency billing and the full attendance/leave/loan/receipts/reporting workflow.
- **28/28 overview browser checks passed:** real data, search, selection, pagination, dates, retry, six widths, both themes, accessibility, long numbers and lifecycle cleanup.
- **36/36 shared-shell browser checks passed:** company screens, native menus, mobile navigation, keyboard operation, light/dark responsiveness and WCAG AA scans.
- **19/19 event-scene checks passed:** deferred engine loading, frozen poster, camera controls, after-hours state, reduced motion, resource disposal, retry and unchanged business records.
- **23/23 dashboard-polish checks passed:** initial layout, white controls, unclipped tooltips, semantic activity, anchored search/notifications, visual help, chart-data popup, table sizing, chart reuse, local atlas, scroll movement, animation preferences, toast dismissal and cleanup.

Browser evidence is under ignored `.local/qa/dashboard-polish`, `.local/qa/overview-design`, `.local/qa/app-shell` and `.local/qa/event-scene`. No new business records are posted by these browser checks; QA database tests roll back.

## Timing comparison

Compared with commit `293147c` in isolated cold browser contexts, two samples per version, with the same asset-delivery method in both phases:

| Measure | Before | After |
|---|---:|---:|
| Dashboard ready | 3.232 / 3.393 s | 3.104 / 2.684 s |
| Date-period interaction | 364 / 206 ms | 251 / 347 ms |
| Dashboard data requests at readiness | 2 | 2 |
| DOM elements | 12,928 | 12,708–12,742 |
| JS/CSS bytes including native framework | 9,653,152 | 9,675,005–9,677,363 |

The samples show comparable interaction latency and no added blocking data request. They are local measurements, not a production capacity or network benchmark. The optional 60 KB image atlas loads separately after readiness. Steady-state checks detect no repeated data requests or accumulating chart instances.

## Reproduce

- `node scripts/build-dashboard-journey.cjs`
- `node scripts/browser-dashboard-polish.cjs`
- `node scripts/browser-overview-design.cjs`
- `node scripts/browser-app-shell.cjs`
- `node scripts/browser-event-scene.cjs`
- `node scripts/browser-dashboard-performance.cjs`
- Run `scripts/audit-workflows.py qa.localhost --dashboard` inside the Frappe environment, from its `sites` directory.

Browser scripts use the existing local administrator credential without logging it. No new packages or external model downloads were added.

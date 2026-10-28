# Agreement, event and crew refinement — 28 October 2026

## Delivered

- The shared form builder keeps rich-text formatting visible and focuses the whole editor. Resource commitment stays open; crew availability is one summary inside Sites and crew.
- Shared disclosures retain the actual action controls when collapsed. The action region is a sibling of the disclosure heading, avoiding nested interactive controls; actions open the section as well as its dialog. Controls are moved, not cloned.
- Single-section dialogs use their existing white surface without nested native-layout shadows. Modal padding, completion links/actions and draft indicators are consistent. Availability refresh keeps its previous content in place, and number steps preserve scroll position.
- CC addresses are separate native Email controls with add/remove actions. The existing server delivery parser and validation still receive a normalized address list. No email was sent to real clients during testing.
- Agreement profiles use Overview, Milestones, Crew & Resources, Details and Documents. Overview presents one outstanding milestone, linked events and resource management. Detailed terms and all payment records remain in dedicated sections. Tabs span both content and collaboration columns.
- Event profiles use the same full-width navigation and sidebar alignment, with detailed event facts in Details. Agreement-linked events do not repeat their governing payment schedule; independent events retain theirs.
- Profile tables retain the shared semantic table renderer and use native-list surface, header, typography, hover and spacing tokens.
- The worker picker excludes already assigned workers from the available queue, retaining their assigned chips for review/release. It uses one shared daily rate, optional individual overrides, and profile salary for monthly pay. The existing 30-day monthly-to-daily calculation and over-budget confirmation remain authoritative.
- Auto-selection assigns available workers and returns exact shortages. Add crew opens the relevant category; undo releases only the returned new assignments. Permission, company, event and attendance checks remain in force. Blank automatic rosters use the native cleanup hook; recorded attendance blocks undo. Earlier assignments are preserved.
- The existing self-hosted ECharts engine now uses softer area treatments, rounded workforce rings, and a single-month horizontal comparison instead of a fake trend. Tooltips, keyboard exploration, exact data tables, credits, empty states and reduced motion remain available. No second chart engine was added.

## Verification

The full 314-case server run passed 313 cases. One old test required all-or-nothing auto-selection, contradicting the new requested behavior. Its expectation was changed to partial assignment with a shortage result. The affected planning, hierarchy and native event suites were rerun: **118 passed, zero failures/errors**. Merging those results with the full run verifies **314 distinct cases**, including the four new crew/pay regressions. This is a full run plus targeted revalidation, not a claim of a second full run.

Browser results:

- **19** existing context checks: creation, signing/CSRF, staffing, final event save, native filters and responsive themes.
- **12** new refinement checks: editor focus, collapsed actions, CC serialization, profile navigation, stable number-step dialog bounds, partial allocation/undo, daily overrides, profile monthly pay, and both themes. Worker popup and all event tabs passed automated AA scans at 390, 900 and 1600 pixels.
- **11** dashboard checks: actual ECharts engine, lazy/retry loading, negative credits, keyboard values, reduced motion, resizing/AA at six widths, request retries and bounded instance disposal.
- **7** read-only checks on the current company: dashboard, amount fitting, light/dark views, current agreement/event tabs, unchanged record counts and zero browser runtime exceptions. It retained 50 workers; the script did not create company records.

Automated accessibility scans do not substitute for a complete assistive-technology audit. Current and empty company data remain truthful; test charts with populated distributions use explicit browser-only fixtures, not invented business records.

Evidence is stored locally in `.local/qa/refinement-unit-verified.json`, `workflow-refinement-browser.json`, `context-ui-browser.json`, `dashboard-browser.json` and `dashboard-after.json`. Current company captures are `company-agreement-overview.png`, `company-event-overview.png` and `dashboard-working-1600-light.png` in that folder.

## Performance sample

Two isolated browser runs per version used the same company and the previous commit's changed frontend assets as the baseline. The framework and engine were not replaced or disabled.

| Measure | Before | After |
| --- | --- | --- |
| Dashboard readiness | 3,589 / 3,524 ms | 3,357 / 3,126 ms |
| Chart-period update | 346 / 374 ms | 392 / 407 ms |
| JS/CSS requests | 72 | 72 |
| Encoded JS/CSS bytes | 9,503,111 | 9,519,348 |
| DOM elements | 12,950 | 12,993 |
| JS heap samples | 24.4 / 25.7 MB | 24.7 / 24.5 MB |

The new presentation adds about 16 KB of raw frontend assets and 43 chart DOM elements, with no added requests or chart engine. Period redraw was about 40 ms slower in this small sample; readiness was lower. These are local diagnostics, not universal speed claims. The dashboard lifecycle regression separately verifies disposal on departure and bounded instances on return. Evidence: `.local/qa/refinement-performance-final.json`.

The current-company checks verify saved data and normal view refreshes. They do not certify the local Socket.IO transport: one diagnostic session logged a development authorization/fetch warning. The normal pages and APIs subsequently passed; this change does not alter realtime infrastructure.

## Preservation and backup

No Frappe, ERPNext or HRMS modules, DocTypes, fields, accounting functions, advanced filters or stock capabilities were removed. Existing native validation, permissions and allocation APIs remain available; only PLUS POINT auto-selection changes its shortage behavior. No new polling, global observers or runtime packages were introduced.

A private company database/config/public/private-file backup was saved before deployment: `20261028_155204-high4tech-events-fd166a217c_localhost-*` in the site's private backups folder. Credentials, private data, tokens and generated client documents are not committed to Git.

Source rollback point: `backup/pre-workflow-refinement-20261028` at `00d7fd6`.

ECharts styling follows the official [area chart](https://echarts.apache.org/handbook/en/how-to/chart-types/line/area-line/) and [doughnut chart](https://echarts.apache.org/handbook/en/how-to/chart-types/pie/doughnut/) component APIs.

# Dashboard chart components — 28 October 2026

The company overview now uses Apache ECharts 6.1.0 for approved worker-day line/bar charts, workforce-by-site donuts and revenue/wage comparison bars. Dashboard providers, calculations, permissions and financial records are unchanged.

## Choice and component ownership

The four supplied libraries were reviewed. ECharts provides the required charts and SVG renderer in the existing JavaScript/Frappe app. `react-chartjs-2` is a React wrapper; introducing React solely for this dashboard was unnecessary. Vizzu's storytelling transitions and D3's lower-level visual primitives are not needed for these three chart types. A single chart engine keeps rendering and interaction consistent.

- Shared owner: `public/js/charts.js`; drawing/theme tokens: `public/css/charts.css`.
- The dashboard supplies categories and series; the shared component owns tooltips, axes, focus, theme updates, number formatting and SVG rendering.
- One mounted instance per host; explicit disposal and a weak host registry prevent duplicate chart instances.
- One existing dashboard ResizeObserver handles both metrics and chart resizing. No new observer or polling loop was added.
- The existing appearance observer dispatches theme changes. Dynamic reduced-motion changes are handled while the dashboard is mounted; listeners are removed when leaving it.
- Internal SVG updates are excluded from the existing global UI enhancement observer.
- Arrow/Home/End keys explore exact values; Escape closes the tooltip. Descriptions, status announcements, named series and exact data tables/list alternatives remain available.
- Negative finance values remain negative. Tooltips retain original source amount strings while the plotting engine uses numeric coordinates.

## Loading, security and preservation

The engine is self-hosted, with no runtime CDN or outbound data transfer. Build dependencies and integrity are pinned in `scripts/chart-bundle/package-lock.json`; a checked-in, reproducible bundle means deployment does not need npm. Apache and transitive notices are included with the vendor asset. npm reported zero known vulnerabilities at installation; this is not a full application security audit.

Only Line, Bar, Pie, Grid, Tooltip, Aria and SVGRenderer are bundled. The result is **553,700 bytes**, **191,939 gzip bytes**, SHA-256 `eca67d2971dddda2e1a59ce8134d049635189208ef5bb2a34d826fb75afb4a06`. This is an additional chart-engine payload, not a claimed bundle-size reduction over the former native chart implementation. It loads only when at least one chart has data and is reused thereafter. Empty company dashboards and unrelated/native platform screens do not load it.

Dashboard assets use the existing native asset manager without its page-wide freeze. Script and analytics failures expose local Retry actions. Explicit retries use fresh native cache keys because the native loader also caches failed downloads. No native loader method, native chart constructor or advanced framework capability is replaced.

The shared controls, overview layout, existing teal palette, native Frappe/ERPNext/HRMS capabilities and platform dashboard remain intact.

## Verification

- Dashboard: **11 browser checks passed**, including actual plotted values, credit values below zero, engine download failure/retry, nonblocking loading, analytics retry, reduced motion and disposal on three leave/return cycles.
- Six viewport widths in light and dark themes: no tested overflow or automated AA violations; SVG dimensions track their container width.
- Keyboard chart exploration and exact data-table access passed.
- Three active chart instances on the overview, zero on departure, three on return; one successful engine download after the deliberate failure.
- Native filters, lookup/pagination, contextual creation, imports and calendar controls: **11 checks passed**.
- Actual company dashboard, both themes and mobile/desktop, unchanged business-record counts and no runtime errors: **5 checks passed**.
- Separate platform/native dashboard preservation: **4 read-only checks passed**.

The populated chart stress fixtures are browser-only test responses; they are not saved as company records. QA fixtures were restored. No schema, backend accounting or production business-data changes were needed.

Evidence lives under `.local/qa/`: `dashboard-browser.json`, `echarts-*-*.png`, `dashboard-working-*-*.png` and `dashboard-after.json`.

References: [modular imports](https://echarts.apache.org/handbook/en/basics/import/), [SVG renderer](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/), [chart lifecycle](https://echarts.apache.org/handbook/en/concepts/chart-size/), [accessibility](https://echarts.apache.org/handbook/en/best-practices/aria/).

Backup: `backup/pre-echarts-20261028` preserves source commit `39e7e48`; the private company database/files backup completed as `20261028_142420`. The reproducible build repeated the same SHA-256.

## Local before/after measurements

`browser-chart-performance.cjs` compared source commit `39e7e48` with the new renderer in isolated browser contexts against the same actual company/provider responses. It changes no company records. Two runs per version are diagnostic, not a broad benchmark:

| Measurement | Previous native charts | ECharts |
| --- | --- | --- |
| Cold overview ready | 3,456 / 3,361ms | 3,269 / 2,623ms |
| Period interaction | 411 / 251ms | 186 / 233ms |
| JS/CSS resources | 69 | 72 |
| Total uncompressed JS/CSS | 8,942,092 bytes | 9,504,531 bytes |
| DOM nodes | 13,007 | 12,933 |
| Used JS heap | about 22.8MB | about 25.5MB |
| Active charts on departure | 0 | 0 |

No latency regression appeared in these local samples. The tradeoff is about 562KB extra uncompressed assets (engine gzip about 192KB), three optional requests and about 2.7MB extra JS heap on a populated dashboard. No universal speedup or memory saving is claimed. KPIs matched exactly across versions. Full evidence: `.local/qa/chart-performance.json`.

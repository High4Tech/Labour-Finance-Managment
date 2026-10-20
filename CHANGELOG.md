# Development changelog

## 2026-10-20 — Approved company access

Approval now provisions a separate empty local company workspace and owner login instead of ending at a demo record. Signup accepts an optional company login ID, uses the email for login and offers private native password setup after approval. High4Tech has progress, retry, login and expiring-link refresh actions, including for older approved requests. Initial passwords are random; links are encrypted, role/token gated and consumed natively. Local trial software invoicing is blocked while normal subscription billing remains native. Payment stays simulated and no email is sent. New company onboarding uses the registered business name without copying demo data.


## 2026-10-18 — Event organizer operations

- Add saved event plans, venue phases/daily crew requirements, availability previews, atomic crew allocation and exact-date accessible calendars.
- Add native warehouse availability, equipment reservation peaks, counted stock imports and crew/cargo vehicle capacities/bookings.
- Extend top-of-list Import/template/review to clients, venues, vehicles, items, warehouses, balances and basic events.
- Add company-owned, resumable first-event onboarding with dimmed/inert background; existing businesses remain quiet.
- Display company account identity, remove customer staff-login management, move Help to the top action bar and adapt labelled dummy projects to events.
- Retain the explicitly requested demo-only plan/signup/approval flow and existing earned-work/billing rules.


## Demo signup and header drag ordering — 2026-10-18

Added a central local pricing/signup page linked from login, published native fixed-rate plans, a business/contact request, explicit simulated payment and High4Tech-only approval/rejection. Requests use private hashed status tokens and preserve price snapshots. Pending approvals appear in the platform dashboard. No money, password, user/tenant provisioning or email is created by this demo. Added actual section-header dragging with automatic per-user save, failed-save restoration and the existing keyboard arrangement controls. Documented local source/data storage, admin login and the invoice/document/signing feature boundaries.

## Local startup recovery — 2026-10-18

The local app and platform worker now start with their Docker container, recover after process failure, and expose HTTP health status. Initial setup still uses the launcher; ordinary restarts preserve installed sites and skip bootstrap. Deliberately stopped services require Start/Up or the launcher to resume.

## Native theme and current-rate display currencies — 2026-10-18

Removed the forced dark/citrus palette while retaining card layout and accessible motion. Dashboard surfaces now inherit the existing Desk theme and teal emphasis; financial figures are bold. Added PKR, USD, EUR, GBP, AED, SAR, CAD and AUD display currencies. Permission-checked overview data is converted with Decimal arithmetic at the latest published daily cross rate, including charts, project rows, budgets and monetary notices. Worker/day counts and source books remain unchanged. The rate, update time, source attribution and book currency are visible; unavailable rates retain original amounts with a retry action.

## Reference-inspired dashboard presentation — 2026-10-18

Adapted the Ferrule reference into the customer overview: matte dark card surfaces, citrus accents, asymmetric work/finance panels, staggered card entrances, growing real-data bars and sequential project-row reveals. Added an explanatory attendance → approved work → earnings/billing graphic with moving connector signals, plus a readable compact mobile version. Motion pauses outside the graphic viewport and respects reduced-motion preferences. APIs, figures, warnings, approvals, billing, payments, notifications and native navigation are unchanged. High4Tech and native record forms keep their existing presentation.

## Aligned activity calendars — 2026-10-18

Added Monday–Sunday row labels, month headings and year labels to the existing 91-day client calendars. Dates use explicit week/day grid positions. Cells stay square and inside responsive cards; client names wrap without pushing totals outside the header. Month headings follow actual dates and preserve space at range boundaries. Existing day details and keyboard navigation remain available.

## Activity dashboard and personal navigation — 2026-10-17

Added six customer summary tiles, an action inbox below stats, per-user read acknowledgements, selectable approved-work history and a revenue/cost comparison on the main overview. Added permission-scoped section landing pages and saved up/down sidebar ordering. Client/company front pages show keyboard-accessible 91-day activity calendars with named day details. Database-side activity aggregation and batched budget totals reduce repeated reads. Added an idempotent, local-only labelled demo story with realistic people/business names, work history and native illustrative invoice/receipt/wage records.

## Quieter established-business overview — 2026-10-17

Removed the always-visible setup/import banner, home tour button and duplicate quick-start block for established businesses. Setup now renders only when the existing server response reports an unfinished business with no assignments. Skip and completion clear that prompt. Manual setup and workflow guidance remain in Help; employee/finance imports stay beside the relevant list Add buttons. The seeded demo opens directly to daily operations without onboarding prompts.

## Visible list imports — 2026-10-17

Added a persistent Import action beside the native top Add action on supported customer employee/finance lists, including populated lists. Each opens the corresponding import type. Moved Download template above collapsible template instructions and the file chooser. Preserved existing native Add behavior, permissions and the preview/posting workflow.

## Guided setup and historical imports — 2026-10-17

Added a resumable customer setup guide: company prerequisite, worker, site/project/client, billing agreement, worker assignment and optional imports. The focused dialog blurs and removes background focus; Skip setup and explore preserves saved steps and restores normal navigation. Existing businesses are not interrupted on rollout.

Added employee and historical finance CSV templates, company reference-ID downloads, bounded CSV/XLSX upload, row previews, error downloads and explicit posting confirmation. Employee profiles can be created or updated. Financial imports create native approved work/milestones, supplier/client invoices, client receipts and employee payments/settlements. Immutable source receipts prevent replay duplicates; changed posted rows are refused. Final checks preserve budgets, native accounting validation, permissions and atomic file rollback. Google Sheets is supported through CSV/XLSX export.

## Spending stops and actionable states — 2026-10-17

Added a separately enabled project spending budget using the native estimated-cost field. Warn at 80%, require pre-submit acknowledgement within the limit and stop cost-increasing approvals/submissions above 100% on both client and server. Covers approved contractor wages, whole attendance registers, net posted purchases and sanctioned claims. Reused posted expense rows for consistent project costs, including claim conversion and cancellation. Client billing, milestone values and existing owed wages remain separate.

Added red overruns, amber warnings, success feedback, retry errors and empty/setup guidance with next-action controls on both dashboards and relevant native forms. Added real budget/posting regressions and browser checks for blocked/warning paths, success actions, error recovery and mobile empty states.

## Dashboards above the overview tools — 2026-10-17

Added real company-scoped dashboards to both product homes, preserving every existing work link below them. PLUS POINT shows workers/sites, approved seven-day attendance, unpaid wages, invoice balances and project contribution. High4Tech shows software customers, access/trials, monthly invoices/receipts, outstanding invoices and six-month sales/cash history. Reused native permissions, posted accounting records and existing contractor report calculations. Added company selection, refresh, loading/error/empty states and responsive chart/table layouts.

## Focused products and native customer support — 2026-10-17

Added one curated native sidebar and overview per site, filtered command suggestions and returned unrelated routes to the product home. High4Tech contains software customers, pricing, subscriptions, owner support, invoices/receipts, expenses, financial results and receivables. Contractor operations and reports remain inside PLUS POINT.

Added immutable PP Support Request records, native RQ across registered local customer sites, login-ID validation, session invalidation, native one-time recovery, encrypted/masked temporary results and redacted errors. Native authentication is unchanged. Registered the existing MVP demo as a trial customer without fake sales. See VERIFICATION_STATUS.md and USER_GUIDE.md for tested flows and limits.

## Two product sides, one entry per site — 2026-10-17

Simplified the native launcher to one PLUS POINT entry on customer sites and one High4Tech admin entry on the separate platform site. Engine apps retain their native route/dock metadata and permissions, while staff accounts, accounting and HR tools are accessible inside the customer workspace. Rewrote guidance around the two business sides, with a separate platform workflow instead of contractor instructions for High4Tech. Updated real browser navigation/onboarding checks to verify the single launcher entry and continued access to native tools.

## Research-context alignment — 2026-10-17

Reviewed the owner's complete research handoff against the actual implementation and recorded RESEARCH_ALIGNMENT.md. Added native Project Finances with financial/deployment views and Worker Statement with dated work/payments, opening/closing wage balances and assignment history. Added home, Employee, Project and billing-terms shortcuts, calculation notes and native export support. Project totals remain lifetime scoped; fixed milestone revenue is not allocated to workers. Replaced the raw financial popup with a filterable report.

Fixed the deployment/rate-change dead end: used assignments can close only while retaining all saved work, and cannot reopen or extend. Historical identities and rates stay locked. Serialized same-worker/same-site overlap checks prevent duplicate allocations while retaining different-site split days and the existing attendance day cap. Expanded the real database suite to 31 regressions; the existing 21 offline/pure-rule tests also pass. See VERIFICATION_STATUS.md for browser/export evidence and explicit remaining MVP/production requirements.

## Simpler customer workspace — 2026-10-16

Added a task-focused home with Mark attendance, workers/sites, client billing and worker payments. The attendance shortcut prepares a populated draft or reopens the saved site/date register; approval remains an explicit Submit action. Grouped the native tenant sidebar, moved less frequent records under More, simplified custom list labels and removed their internal ID column. Setup tools and the six-step guide start collapsed, with contextual help available on demand. Native title metadata improves linked record labels. Existing operator layouts, explicit home preferences and platform navigation are preserved.

Real Edge checks cover desktop/390px mobile layouts, attendance creation/reopening and administrator fixture cleanup, tenant/platform onboarding and native navigation. Added UX_DESIGN.md with the principles applied and their limits. This change preserves the existing financial rules and native permissions; it does not claim customer usability research or complete accessibility acceptance.

## Product onboarding — 2026-10-16

Added a workforce quick start, app-role guide, opt-in native tour, contextual home links, screen explanations and keyboard/click field tips. Added native help descriptions for 42 contractor/platform fields and clear guidance distinguishing dehadi, HR attendance, invoicing and payments. The separate platform app tile now opens High4Tech subscriber administration. Added USER_GUIDE.md and real tenant/platform onboarding browser regressions; navigation, attendance draft creation/cleanup and 11 offline checks pass. Upstream source and document access rules remain unchanged.

## Navigation correction — 2026-10-16

Fixed the completed setup wizard reloading from All apps by running Frappe's native post-setup transition in local demo seeding. Updated PLUS POINT's app entry to the canonical Desk route. Included Purchase Manager in local tenant owner roles so the native Home purchase card can load. Corrected the requested local dummy accounts and linked the tenant login to the sample employee for native HR self-service. Added a real browser regression covering the app switcher, HR, Home, Users, return navigation and optional employee self-service; verified as the tenant dummy login with no browser/server errors. All 11 offline checks also pass.

## 0.4.0 — 2026-10-16

Integrated the discovered v0.3 source into the existing repository without replacing Git history; archived the original foundation documentation. Added pinned Windows Docker Desktop setup, persistent volumes, resumable native app installation and upstream setup defaults.

Reused native ERPNext/HRMS/Frappe business records, Desk, authentication and APIs. Repaired snapshots, historical allocations, pagination and posting concurrency guards. Added native invoice source reservation/posting/cancellation, client receipt summaries, wage settlements against native employee payments, and clear outstanding/profit figures.

Added separate High4Tech workspace/tenant registry backed by native subscriptions/plans, trusted local provisioning/owner accounts, hostname-isolated databases and current host-managed quota/expiry/suspension enforcement. Payment mode stays manual/development. Corrected Bench default-site routing and cached-entitlement enforcement after live tests exposed the defects.

Rotated local credentials following a process diagnostic exposure; provisioning no longer puts passwords in process arguments. Added real database, HTTP, isolation, subscription, browser and disposable-installer checks plus CI definitions. See VERIFICATION_STATUS.md for 45 automated unit/integration tests and separately executed live/browser checks, and explicit unverified production requirements.
Additional concurrency audit: explicitly configured READ COMMITTED for MariaDB 11.8 snapshot behavior, added current locking reads for financial limits/reservations, and verified 10 simultaneous attendance requests (one winner, nine duplicate rejections). Initialized native site encryption keys before web startup to repair fresh-runner first-token authentication. Added the write race to integration CI.

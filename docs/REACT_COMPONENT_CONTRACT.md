# React company interface contract

The existing orange PLUS POINT visual system remains the source of visual tokens. `frontend/src/components.tsx` owns recurring React markup and interaction. `public/css/react_ui.css` scopes its additions to React roots; the native framework is not globally restyled by these components.

| Component | Contract |
| --- | --- |
| Button | 40px default target, 20px local SVG icon, 8px icon gap, shared border/radius/type tokens. Primary orange/white; draft yellow; destructive red; form emphasis dark; supporting grey; ghost/text variants. Icon-only controls need a meaningful accessible name. Loading disables duplicate activation and supplies `aria-busy`; reduced motion stops its spinner. |
| Field / Input / Textarea | Visible 14px/20px label, 6px label gap, 15px/22px entered text, 40px input, 8px radius. Full available width; no fixed-width internal field wrapper. Error border and associated solution text use `aria-invalid` and `aria-describedby`. Form owners retain field-specific validation. |
| Checkbox | Existing Figma control styling is authoritative, square 20px dimensions, orange selected state, native checked/indeterminate/disabled semantics and visible keyboard focus. Forms and DataTable use this same primitive. |
| Select | Same field geometry; controlled value, selected mark, keyboard arrows/Home/End/Enter/Escape, searchable long options, bounded scroll. Escape dismisses an open menu; when closed it propagates to the containing dialog. Overlay closes outside/resize/parent scroll and stays within a modal's native top layer. Listeners are released on close/unmount. |
| RadioGroup | Native radio semantics and one group name; shared horizontal layout which wraps at narrow widths. Only mutually exclusive choices use radios. |
| Panel | White/foreground content surface, integrated soft heading background, 20px/28px heading, shared padding/elevation/border. Header actions use the same button contract. A native dialog does not gain a decorative nested card unless its content contains genuine sections. |
| DataTable | Existing compact list/table geometry, consistent heading/body typography, fixed checkbox column, controlled row keys/selection/indeterminate state, horizontal action group with sticky end column and horizontal overflow. Selection actions do not replace the create action. Reset selection when the result/filter scope changes. |
| Badge | Shared fully rounded semantic pill. The refined dashboard's outlined-dot status is an explicit visual variant. Semantic success/warning/error colors are not alternate brand palettes. |
| Dialog | Centered desktop/viewport-bounded mobile, 24px body gutters, scrollable body, semantic heading, native focus/inert handling, focus restored on dismissal, Escape/outside close. Busy posting blocks dismissal. No empty footer when content supplies its own actions. |
| Feedback | Straight semantic accent, full available content width, icon plus text, alert/status semantics. Field mistakes also highlight the corresponding input. Business explanations must state the next action. |
| SummaryCards | Same label/value hierarchy and layout; bold labels, legible bounded numbers. Dashboard financial metrics are a separate documented chart-card variant. |
| Worker | Real photo or first/last initials; optional avatar-only presentation. The supplied 3D portrait is used only on the worker detail identity panel. |

Light/dark variants use the established tokens. Mobile grids collapse without page-wide horizontal overflow; wide tables scroll within their region. Keyboard and automated WCAG AA checks are included for the migrated owners. Automated checks do not replace a manual accessibility audit.

## Runtime ownership

- Mount one complete screen subtree, never a legacy HTML-string renderer inside React. Shared select/dialog portals remain owned by that subtree.
- Abort read requests on departure and reject stale responses. Use bounded, user/company-scoped list snapshots only; current financial balances and all write decisions are server checked.
- Coalesce relevant existing realtime events; no interval reload. Dispose roots, chart instances, observers, subscriptions and native route overrides on departure.
- Product list routes retain native metadata/permission checks but skip initializing a second hidden native table/filter/sidebar. Other DocTypes and explicitly requested advanced views use their original native lifecycle.
- Preserve Frappe/ERPNext/HRMS APIs, controllers, permissions, hooks, accounting/stock infrastructure and advanced exports. Removing superseded PLUS POINT presentation is different from removing framework functionality.
- Builds retain earlier local hashed chunks for already-open browser tabs. The generated allowlist publishes only the current manifest graph; no automatic recursive deletion of served assets occurs.

## Superseded presentation audit

The old `worker_profile.js` renderer returned immediately to the React adapter for company users; platform users never entered its mount handler. Its only legacy editor consumer was `people.js:render_worker_editor`. Searches across routes, hooks, tests and public JS found no remaining consumers. Their unreachable renderer/editor/sync bridge were retired after the React worker suite passed. Shared identity/category helpers and native Employee forms/controllers remain. The native advanced view is exercised separately in the worker browser suite.

## Agreement component variants and ownership

- Panel optionally adds the shared 32px semantic heading icon. All typography, heading tint, action spacing and body gutters still come from the same Panel contract.
- Tabs uses one controlled active panel, roving keyboard focus and matching `aria-controls`. Section changes keep the profile owner mounted.
- Facts spans genuinely long location/reference values across its available content width. Document names use left-aligned file-type SVG, text and end action geometry.
- RichText owns an isolated installed Quill control. It initializes the saved HTML explicitly and synchronizes text-change immediately so rapid review/save cannot lose the last keystroke. It releases its handlers on departure. RichContent is the read-only variant: preserve supported document formatting; exclude active tags, event attributes and unsafe URLs.
- EmailFields uses one input per address, wrapping CC rows horizontally when space permits. Removal controls align with the input, with shared 12px gaps. Each row has its own label and error association.
- DocumentPreview fetches private PDF bytes only when opened, creates an object URL for the preview/download and revokes that URL on close or late unmounted completion. The native File uploader remains an explicit adapter until the import/upload owner migrates.
- Agreement resource edits are staged locally and serialize only existing persisted venue IDs; new sites resolve by name. Price conversion is left to the existing explicit-currency backend boundary. Edits still use the existing immutable proposal/client-signature or company-attestation workflow.
- A worker created from a missing crew category uses the shared WorkerEditor with an initial category value, not a copied form. The category popup and profile use the same field/button/dialog components.

## Full form variants

- CreationSteps and CreationFooter define the shared three-step form navigation. Desktop steps have room for their full description, mobile steps wrap into a compact row, and the footer spans the main content container. Explicit reset classes keep native fixed-height button rules from clipping the step descriptions. Only the current form stage is displayed; hidden fields retain their React state.
- Field labels have stable IDs. RichText references the same label and focuses the complete rounded editor/toolbar container. RadioGroup exposes its field error using the same invalid/description association as text inputs.
- Select supports an optional remote query and scroll-end pagination without changing local-choice behavior. Pending requests and stale results belong to the owner; no top-of-list Load more action is injected.
- CostConfirmation is the single explicit over-budget confirmation variant. It retains entered data and only sends the original backend override flag after confirmation.
- A new agreement reuses AgreementResources in inline staging mode and FixedMilestone/BulkMilestones in local staging mode; existing saved editors keep their original authorized mutation/proposal boundaries. Staged bulk milestone edits validate the aggregate contract total before applying.
- DraftSession and useAgreementDraft own serialized autosave, revision handling, bounded recovery, visibility flush and disposal. Empty defaults are not content. A revision conflict preserves recovery and requires explicit user resolution. Draft status is a plain utility state, never a second animated helper.

## Shared interface and import ownership

- DashboardSkeleton uses the dashboard's final header/three metrics/two tables/activity/attendance grids, not an unrelated native workspace skeleton. Financial reads remain uncached and the existing chart owner updates its instances.
- DataTable inside a form/dialog measures the header and first six rows before paint when there are more than six. Its local observer handles wrapping/resizing, and unmount releases it. Horizontal scrolling and the pinned action column remain independent.
- PaymentName and AttendancePeriod are the shared schedule cells in creation and saved-agreement views. Context is readable, a one-day date is not duplicated, and optional working hours distinguish overnight shifts without changing wage/attendance accounting.
- ImportUpload and ImportDialog replace the old product import FieldGroup/string-table renderer. They use the original local SVG file types, original server templates/preview/approval APIs, native permissions and transactional posting. The old native product import renderer has no remaining caller after open_import delegates to the React owner. Frappe's advanced Data Import is untouched.
- The company branch in the native dashboard loader returns to React before running its platform flow. Its private company-only budget presentation helper had no remaining call and was removed; budget APIs, event controls and the platform renderer remain available.
- Native file upload/photo widgets remain documented integration boundaries until their consuming owners migrate; no second equivalent React photo widget is introduced.

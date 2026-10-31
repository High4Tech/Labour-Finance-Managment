# App appearance and actions

Current creation UI: [Context-aware three-stage workflows and shared components](docs/CONTEXT_AWARE_UX_2026-10-27.md). This supersedes earlier five/four-step layout descriptions; the underlying business architecture is retained.

The [community component review](docs/COMMUNITY_COMPONENTS_2026-10-24.md) records the 21st.dev patterns adapted into the native system. Shared `empty_state`, `loading_state` and `render_table` helpers own supporting-table feedback. Empty states provide a clear title and next-step guidance without duplicating surrounding actions. Loading placeholders are static and expose one status message. Agreement/event step navigation shows completed checks and connecting separators while retaining the native validation gates. Table row feedback follows both pointer hover and keyboard focus. These patterns add no external runtime dependencies.

All template imports share one drag-and-drop file component with native keyboard file selection, a filename/size summary and Remove action. Only one CSV/XLSX file up to 2 MB is accepted. Replacing/removing a file invalidates its review and consent; confirmation remains beside the posting action. Network failures require a fresh review rather than automatic posting retries. [The template audit](docs/IMPORT_TEMPLATE_AUDIT_2026-10-25.md) records supported fields, creation/link behaviour and end-to-end coverage.

Agreement list imports, including the native list menu/empty-state handler, use that same importer for company managers. Importing inside a new agreement fixes the import type and flushes the existing draft first. One saved agreement opens automatically in the agreement editor, including a duplicate replay that resolves to an existing record. A batch presents record choices before navigating. Existing partial drafts are preserved. Saved agreement links use the product editor rather than the generic DocType form. Platform and unsupported native import paths retain their framework behavior.

PLUS POINT and High4Tech use the same action system in `public/css/interface.css`. It loads after feature styles. New actions should use native `.btn` variants or Frappe `.es-button` controls; avoid per-page button heights, padding or border-radius overrides.

| Token / role | Desktop | Mobile / touch |
| --- | --- | --- |
| Default action height | 40px | 44px |
| Icon-only action | 40 × 40px | 44 × 44px |
| Horizontal padding | 12px | 12px |
| Icon | 16px | 16px |
| Radius | 8px | 8px |
| Icon and group gap | 8px | 8px |
| Type | Inherited app font, 13px / 20px | Same |

Primary actions use the product teal with white text. Secondary actions use the current theme's control surface and border. Destructive confirmation buttons use red. Disabled, loading, hover and visible keyboard-focus states retain native behavior and shared styling. Small field utilities, calendar cells and activity-map cells retain their own control geometry. The mobile page header has separate title and action rows so touch targets fit without covering list filters.

The Desk main panel owns content scrolling and contains its positioned descendants. This keeps hidden table captions inside the panel, prevents a second document scrollbar and blank space below the app, and keeps the sidebar stationary. Do not hide document overflow to mask escaping content.

**Appearance** is always available at the bottom of the sidebar. Light, Dark and System use the native `User.desk_theme` setting and theme engine. System follows operating-system changes, and explicit choices survive a reload. Both products use this control. A failed preference save keeps the previous choice and shows a retry message without opening another dialog. Theme changes do not convert or change any business data.

Dark mode inherits native Desk surfaces and typography; product chart, activity, warning, error and success colors have explicit dark variants. Semantic status colors remain distinct from action colors. The featured metric retains a dark teal background with light text.

`scripts/browser-appearance.cjs` checks saved preferences, reload/system changes, failed saves, list/form/dialog sizing, icon alignment, mobile header bounds, status readability and mobile overflow. It restores the original user appearance and removes its exact disposable company fixture.


## Record editors and lists

Agreement and event editors use the same numbered, accessible step navigation with a bottom Previous/Next row. Next validates the current step; going back retains entered values. New agreements cannot skip incomplete required steps. The editor replaces duplicate page/global toolbars with one header action group. Save draft and Import agreement are available while incomplete; Save agreement appears when client, scope, dates, pricing and crew are ready. Draft saving never removes the normal completion requirements. Incomplete agreement and event forms autosave into their respective lists with Draft status. Completing an agreement opens the event-details/signature handoff; event creation supports Draft, Now and Schedule. The saved event keeps actual crew and transport bookings in their relevant steps. Other record sections use accessible top tabs. Supporting guidance lives behind 14px information controls aligned with the heading or field-label row; blocking errors remain visible. Native input heights are shared across both form columns, including error states. Checkbox controls retain native checked rendering at 16px.

Site/crew requirements use explicit row editors and a visible save action. Tables have meaningful column labels and adapt to record cards when the content area is narrower than 1000px, including when the activity rail is open. Worker names and row actions remain visible. Native searchable/sortable lists are preserved without the redundant List View selector; row metadata uses stable references and record-specific actions rather than likes/comments.

App-level report currency affects aggregate displays. Agreement/event editors label monetary fields with their saved currency and convert only at the accounting boundary using the agreed rate.


Worker identity uses one capsule with a 30px photo or initials, a legible name, and an optional remove/action affordance. Profile headers use the same identity at 52px. Worker editing keeps native save/validation behind a focused three-tab surface. Action dialogs are scoped to their originating record and restored hidden on close; cancellations discard uncommitted editor state. Help text uses a body-level overlay to avoid clipping by tabs/tables. Navigation section labels use muted 11px bold text, distinct from 13px links; drag grips appear on hover or keyboard focus. Schedule cells have at least 104px vertical room for date, demand and assigned values. Attendance heatmaps retain square cells and scroll within the panel for long periods.


Draft autosave uses one active editor session, a 1.5-second debounce and one coalesced request in flight. A bounded per-user/company session recovery cache retains only unsynced form snapshots for up to 12 hours (at most five, 48 KB each); server drafts are capped at 96 KB. Leaving the tab flushes the current form. Scheduled event creation runs once a minute, handles at most 25 due drafts and locks each draft to prevent duplicates. Mobile step titles remain available to screen readers even when visually shortened. New editor dependencies load before rendering, with a shared on-demand recovery request for older cached Desk include lists.
# Saved record profiles

Drafts belong in their respective Client agreements and Events lists, with a Draft indicator and Resume draft link. Use the native list adapter described in [inline drafts](docs/INLINE_DRAFTS_2026-10-25.md); do not add a separate Drafts navigation destination or create financial/operational records for incomplete forms. Keep source-aware selection/deletion, scoped queries, completion handoff and scheduling intact.

Creation/full-edit screens share `flow_builder.js` and `flow_builder.css`, described in [the creation-flow review](docs/CREATION_FLOWS_2026-10-25.md). Move original controls into cards; do not clone forms, duplicate actions or add separate save logic. Keep a five-step agreement rail and four-step event rail, native draft/signing/scheduling rules, local field errors and a single comments composer. The event Save button moves to the footer only on the final step; never reinsert action buttons on ordinary input changes. Worker avatars and event pay occupy separate table columns. Timeline view uses real staffing bars and retains the Week/Month/Year calendar views.

Agreement profiles use document sections and the shared fact-list, section-heading, table and popup-editor components in `profiles.js`. Events reuse the operational crew/resource/timeline components without forcing the contract document layout. Use `?record=<id>` for a saved profile and `?record=<id>&edit=1` only for an explicit full edit; imports started inside New agreement keep the edit handoff. Scrollable tables must be labeled keyboard-focusable regions. Keep creation signing actions visible and explain unavailable outgoing email in place.

Saved agreements follow the compact teal header, four summary cards and two-column detail/sidebar composition documented in [the agreement layout review](docs/AGREEMENT_LAYOUT_2026-10-25.md). The five tabs share one pricing component and one comments composer. Keep scope separate from dates, expose section edits through the existing popup editor and open signing on demand. Attachments use the native private uploader. Restore the active tab only for the immediate save/upload refresh; a normal record opening starts at Details. Never hide overflow on the hero in a way that creates an internally scrollable header: all title text and actions must stay visible after viewport changes.

Saved events use the operational composition in [the event layout review](docs/EVENT_LAYOUT_2026-10-25.md): a compact title/action header, date/client/agreement/venue context and five accessible tabs. Overview keeps the information, crew, resource and timeline sections together; focused tabs move those same sections rather than creating parallel editors. Avatar summaries open all worker names and individual pay/move controls. Keep agreed vehicle demand distinct from actual bookings; inventory reservations belong with equipment. The sidebar shows date-derived phase progress, one comments composer and available recent activity. Never fabricate preparation or pack-down dates. Event uploads remain private native attachments. The page uses the existing teal and semantic status tokens in both themes.

Agreements and saved events share `pp-record-hero`, including its dark teal surface and contained decorative layer. Keep action menus outside that clipped decorative layer. Event headers span the full record width and include total planned worker-days. The shared [staffing calendar](docs/EVENT_HEADER_CALENDAR_2026-10-25.md) shows explicit assigned/agreed counts, real dates and approved attendance in day details. Its Sunday-first Week/Month/Year views default to today, allow navigation outside event periods and align year labels to actual week columns. Calendar weekday classes are separate from the worker attendance heatmap; legacy table cell sizes are overridden only within the staffing calendar. Overview places it below the operations/sidebar at full width; the Timeline tab reuses that same instance.

## Freddy feedback

Use `plus_point.freddy_feedback(element, {message, tone, solution, rich})` for new error, warning, guidance, loading, empty and success messages. Existing field errors, native messages/snackbars and info popovers are adapted by the shared component. Keep it beside the relevant field or action; preserve backend validation, linked-record actions and `aria-describedby`. Explain the problem and the fix in a short sentence. Use supplied expressions with still images by default, one brief animation at a time, and reduced-motion support. Do not add a second floating assistant or a remote model call for ordinary feedback.

New event creation validates the initial details, then opens the real event editor at Venues and crew through Create event and continue. Never show read-only requirement previews in place of worker assignment controls. Reuse an existing event explicitly when its agreement already has one, preserving its details, budget and assignments. Scheduling is optional and keeps budget settings and draft comments. See [event-start controls](docs/EVENT_START_CONTROLS_2026-10-26.md).


The supplied PLUS POINT button reference is implemented in `interface.css`: 32/40/48px small/default/large buttons, 14px default text, 8px icon gap, primary/secondary/text/ghost/destructive states, focus rings and loading feedback. Touch actions are at least 44px. The public signing form reuses this same stylesheet.

Company navigation and profile/action icons use the locally hosted Streamline Core Line sprite (`icons.js`, `images/streamline.svg`). Set navigation icons in the initial server metadata; do not replace sidebar icons after paint. Streamline credits are available in the company menu's About PLUS POINT entry.

Keep render readiness explicit: agreement/event builders show their loading state until the final controls and collaboration rail are composed. Never paint an intermediate form and then transform it visibly. Reuse unchanged footer/help/error widgets; typing must not replace avatars, footer text or hidden review panels. Shared UI enhancements react to meaningful DOM/route changes, not every keystroke. Component redraws synchronously reconcile one header and its action; do not add duplicated inner headings. List setup must not trigger a second render just to hide a column. Refresh/route changes reconcile the actual selection before exposing bulk actions. Close a worker-summary dialog fully before opening pay/move controls. See [the stability review](docs/UI_STABILITY_2026-10-26.md).


## Shared native component layer — October 27

`ui_components.js/.css` owns creation panels and heading bands, centered icon metrics, optional disclosures, semantic alerts/status styles, native dialog surfaces and common control states. Builders use its panel primitive; agreement and event metrics share its metric primitive. Native fields use 15px input text, visible borders/focus and inline correction text; toolbar controls are 40px desktop/44px mobile, including Filter/reset/sort and record scope. The existing single bounded UI observer handles compatibility enhancements. Native Dialog behavior remains authoritative; desktop dialogs no longer slide upward before settling. Financial/native form sections and worker editing share the same white-on-grey surface treatment.

## Shared table selection and review controls — October 29

`plus_point.table_selection(tableOrContainer, {keys, eligible, actions})` is the authoritative selection layer for PLUS POINT tables. It adds a 44px selection column, labelled checkboxes, an indeterminate Select all state, selected count and contextual actions. Existing native list/table selection remains authoritative. Narrow venue tables show Select all above their cards when the header is hidden. Selection tools use the shared 14–15px typography, 8px action gap, native button focus/disabled states and theme tokens; no entrance animation, polling or extra observer is needed. `dispose()` releases the old selection before an incremental table refresh. Read-only tables support copying selected values; mutations require an explicit feature action and retain backend protections.

`plus_point.bulk_edit` uses native Dialog and shared inputs. Users explicitly choose which fields to change; unchecked fields keep their original values. Creation crew, vehicles and milestones; saved agreement crew/vehicles; event requirements/reservations; and crew pay use their contextual mutation/approval paths. Posted/invoiced rows are never unlocked by the presentation layer. Multi-record writes are bounded, scoped and atomic. Agreement changes still go through client approval.

Filters contain one record-status radio group, sort-field/order radio groups, Advanced criteria and Reset at the end. The original native filter and sort controllers remain available; their duplicate presentation is hidden. Resource commitment reuses its original control inside Billing setup: horizontal choices on desktop and a select on mobile. Final wizard buttons invoke the existing create/save command rather than incrementing the step index.

Deletion blockers use one bordered card per record, a shared status pill, a short reason, a linked-record action and an optional explanation disclosure. Single long facts span the available panel width. Upcoming milestones use the shared table with an action column. Signature fingerprints remain evidence, with readable acceptance dates and optional verification details in the generated document source.

## Creation scaffold, calendar and documents — October 29

The shared builder owns viewport height and footer placement: the footer stays at the bottom and spans the whole main workspace beside the app navigation, including the stepper width, using the existing responsive gutters. Review cards use shared 15px text, 16px headings and 16/20px spacing. The existing resize observer owns sizing and is disposed with the builder; never add another observer to implement a feature-specific footer. Native controls and create/save commands remain authoritative.

`render_document_list(root, files)` owns agreement/event file rows. It uses a 40px supplied file-type icon column, flexible left-aligned title/metadata, 44px action column, 12px gaps and 16px insets. PDF preview/download use scoped private File reads. Display names can be descriptive while native storage keeps bounded filenames and immutable URLs. File rows have no entrance animation and use the shared theme, button and focus tokens.

The event calendar owns period/date/venue state and a selected-day link to the native Attendance register, filtered by project, date and venue. It does not duplicate the worker roster. Its date control is centered independently of the left-aligned Timeline/Week/Month/Year controls and right-side venue filter; narrow containers stack these controls. Today is the default, formatted as an abbreviated weekday, ordinal day, month and year. Do not add a second date-range line under the picker. Coverage uses shared filled pills. Selecting a day and opening Attendance do not create registers or work entries; no polling occurs. Event overview places this component first and keeps crew/resource cards expanded; shortages are an inline part of crew coverage. See [verification and constraints](docs/EVENT_CREATION_AND_REVIEW_2026-10-29.md).


## Shared upload assets and table actions — October 29

`design_assets.js` owns the supplied file-type and country-flag map. Use `assets.file(filename)` in every document/import row and `enhance_country_picker(control)` for native Country links. Local decorative images preserve the native field name and keyboard behavior; they are requested only when shown. The supplied upload tile is extracted from the reference SVG. The import dropzone, selection row and real progress states are live controls styled by `upload_assets.css`, not a flattened illustration.

`open_file_upload(options)` is the PLUS POINT presentation adapter for the original Frappe uploader. Agreement/event attachments, worker photos and company branding use this one variant. Keep native permissions, private/public controls where authorized, library access, cropping, configured Drive integration, validation and upload endpoints. Its one instance-scoped progress subscription is removed when the dialog closes. There are no new global observers or polling loops. The fixed company passed into an import remains authoritative even when a reopened hidden Link control is still initializing; the server checks company access as before.

Owned tables with an Actions header use the shared horizontal action wrapper and a pinned final column. Keep the table horizontally scrollable at narrow widths, including mobile, rather than stacking its action buttons. Selection remains in one visible header checkbox; dynamic crew rows reapply the same shared table-action decorator when updated. Completed event-progress rows show a check; upcoming/unscheduled rows use a muted grey surface.

See [calendar and asset acceptance](docs/CALENDAR_AND_UPLOAD_ASSETS_2026-10-29.md) for the verification scope and asset provenance.

## Optional event scene — October 31

Event Overview exposes one full-width still-image button with a supporting **View event scene** action. The default 35 KB WebP is rendered offline from the shared world, with no worker or vehicle bookings, by `scripts/build-event-scene-poster.cjs`. `event_scene.js/.css` and the pinned local Three.js bundle are optional features: never add them to Desk includes, preload them, or initialize a canvas on event/dashboard render. The original event profile remains the operational interface.

`plus_point.event_scene` owns one venue template and one active native Dialog. `snapshot(data, options)` projects existing staffing dates, unique assignments and dated vehicle bookings; no equipment, employee positions or tracking are invented. A demo can explicitly preview Working hours / After hours. Now uses the current site timezone, event dates and the temporary preview hours. These hours are labelled as unsaved demo settings until persistent event shifts are defined.

The venue sits in one reusable world with streets, arrival plaza, landscaping and soft background buildings. Overlay counters and one contextual inspector use the shared panel/status contracts. Pointer dragging and arrow keys pan within bounded limits; markers link to the existing crew/transport tabs. Mobile places the same inspector below the world. Counts remain exact; representative figures are capped at 36 workers and 6 vehicles. Workers share instanced geometry, materials and one local sign texture. A 1024px shadow map is cached between state changes. There is one visible-scene animation loop capped at 30 FPS, a pixel-ratio cap of 1.5 and one instance-owned resize observer. Off-hours, paused and reduced-motion states render only on changes; a hidden document stops rendering. A single timeout updates Now at the next shift/date boundary, with no network polling. Close, replacement and route changes dispose graphics, observers, listeners and timers. Cached code is reused on reopening; GPU scenes do not accumulate.

The popup inherits the shared native dialog/button/typography/theme contracts. Its preview controls, accessible counts and Back to event details remain usable when WebGL is unavailable. The scene canvas is an illustration with a text alternative; it cannot record attendance, reserve resources, create invoices or change event data. See [demo acceptance](docs/EVENT_SCENE_DEMO_2026-10-31.md).

Closing the scene may replace the poster with one frozen WebP of the last view before releasing the renderer. This image belongs only to the current page; never persist it in browser storage, upload a File record, or retain a background renderer. Capture failure must not prevent dialog cleanup. The image-button variant shares section-header, action, focus and responsive contracts, with dark-mode image treatment.

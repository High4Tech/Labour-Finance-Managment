# App appearance and actions

The [community component review](docs/COMMUNITY_COMPONENTS_2026-10-24.md) records the 21st.dev patterns adapted into the native system. Shared `empty_state`, `loading_state` and `render_table` helpers own supporting-table feedback. Empty states provide a clear title and next-step guidance without duplicating surrounding actions. Loading placeholders are static and expose one status message. Agreement/event step navigation shows completed checks and connecting separators while retaining the native validation gates. Table row feedback follows both pointer hover and keyboard focus. These patterns add no external runtime dependencies.

All template imports share one drag-and-drop file component with native keyboard file selection, a filename/size summary and Remove action. Only one CSV/XLSX file up to 2 MB is accepted. Replacing/removing a file invalidates its review and consent; confirmation remains beside the posting action. Network failures require a fresh review rather than automatic posting retries. [The template audit](docs/IMPORT_TEMPLATE_AUDIT_2026-10-25.md) records supported fields, creation/link behaviour and end-to-end coverage.

Agreement list imports, including the native list menu/empty-state handler, use that same importer for company managers. Importing inside a new agreement fixes the import type and flushes the existing draft first. One saved agreement opens automatically in the agreement editor, including a duplicate replay that resolves to an existing record. A batch presents record choices before navigating. Existing partial drafts are preserved. Saved agreement links use the product editor rather than the generic DocType form. Platform and unsupported native import paths retain their framework behavior.

PLUS POINT and High4Tech use the same action system in `public/css/interface.css`. It loads after feature styles. New actions should use native `.btn` variants or Frappe `.es-button` controls; avoid per-page button heights, padding or border-radius overrides.

| Token / role | Desktop | Mobile / touch |
| --- | --- | --- |
| Action height | 36px | 44px |
| Icon-only action | 36 × 36px | 44 × 44px |
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

Agreement and event editors use the same numbered, accessible step navigation with a bottom Previous/Next row. Next validates the current step; going back retains entered values. New agreements cannot skip incomplete required steps. The editor replaces duplicate page/global toolbars with one header action group. Save draft and Import agreement are available while incomplete; Save agreement appears when client, scope, dates, pricing and crew are ready. Draft saving never removes the normal completion requirements. Incomplete agreement and event forms autosave into one Drafts list. Completing an agreement opens the event-details/signature handoff; event creation supports Draft, Now and Schedule. The saved event keeps actual crew and transport bookings in their relevant steps. Other record sections use accessible top tabs. Supporting guidance lives behind 14px information controls aligned with the heading or field-label row; blocking errors remain visible. Native input heights are shared across both form columns, including error states. Checkbox controls retain native checked rendering at 16px.

Site/crew requirements use explicit row editors and a visible save action. Tables have meaningful column labels and adapt to record cards when the content area is narrower than 1000px, including when the activity rail is open. Worker names and row actions remain visible. Native searchable/sortable lists are preserved without the redundant List View selector; row metadata uses stable references and record-specific actions rather than likes/comments.

App-level report currency affects aggregate displays. Agreement/event editors label monetary fields with their saved currency and convert only at the accounting boundary using the agreed rate.


Worker identity uses one capsule with a 30px photo or initials, a legible name, and an optional remove/action affordance. Profile headers use the same identity at 52px. Worker editing keeps native save/validation behind a focused three-tab surface. Action dialogs are scoped to their originating record and restored hidden on close; cancellations discard uncommitted editor state. Help text uses a body-level overlay to avoid clipping by tabs/tables. Navigation section labels use muted 11px bold text, distinct from 13px links; drag grips appear on hover or keyboard focus. Schedule cells have at least 104px vertical room for date, demand and assigned values. Attendance heatmaps retain square cells and scroll within the panel for long periods.


Draft autosave uses one active editor session, a 1.5-second debounce and one coalesced request in flight. A bounded per-user/company session recovery cache retains only unsynced form snapshots for up to 12 hours (at most five, 48 KB each); server drafts are capped at 96 KB. Leaving the tab flushes the current form. Scheduled event creation runs once a minute, handles at most 25 due drafts and locks each draft to prevent duplicates. Mobile step titles remain available to screen readers even when visually shortened. New editor dependencies load before rendering, with a shared on-demand recovery request for older cached Desk include lists.
# Saved record profiles

Agreement profiles use document sections and the shared fact-list, section-heading, table and popup-editor components in `profiles.js`. Events reuse the operational crew/resource/timeline components without forcing the contract document layout. Use `?record=<id>` for a saved profile and `?record=<id>&edit=1` only for an explicit full edit; imports started inside New agreement keep the edit handoff. Scrollable tables must be labeled keyboard-focusable regions. Keep creation signing actions visible and explain unavailable outgoing email in place.

## Freddy feedback

Use `plus_point.freddy_feedback(element, {message, tone, solution, rich})` for new error, warning, guidance, loading, empty and success messages. Existing field errors, native messages/snackbars and info popovers are adapted by the shared component. Keep it beside the relevant field or action; preserve backend validation, linked-record actions and `aria-describedby`. Explain the problem and the fix in a short sentence. Use supplied expressions with still images by default, one brief animation at a time, and reduced-motion support. Do not add a second floating assistant or a remote model call for ordinary feedback.

# App appearance and actions

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

**Appearance** is always available at the bottom of the sidebar. Light, Dark and System use the native `User.desk_theme` setting and theme engine. System follows operating-system changes, and explicit choices survive a reload. Both products use this control. A failed preference save keeps the previous choice and shows a retry message without opening another dialog. Theme changes do not convert or change any business data.

Dark mode inherits native Desk surfaces and typography; product chart, activity, warning, error and success colors have explicit dark variants. Semantic status colors remain distinct from action colors. The featured metric retains a dark teal background with light text.

`scripts/browser-appearance.cjs` checks saved preferences, reload/system changes, failed saves, list/form/dialog sizing, icon alignment, mobile header bounds, status readability and mobile overflow. It restores the original user appearance and removes its exact disposable company fixture.


## Record editors and lists

Agreement and event editors use the same numbered, accessible step navigation with a bottom Previous/Next row. Next validates the current step; going back retains entered values. New agreements cannot skip incomplete required steps. The editor replaces duplicate page/global toolbars with one header action group. Save draft and Import agreement are available while incomplete; Save agreement appears when client, scope, dates, pricing and crew are ready. Draft saving never removes the normal completion requirements. Event creation previews its source agreement before creating the plan; the saved plan keeps crew and transport actions in their relevant steps. Other record sections use accessible top tabs. Supporting guidance lives behind 14px information controls aligned with the heading or field-label row; blocking errors remain visible. Native input heights are shared across both form columns, including error states. Checkbox controls retain native checked rendering at 16px.

Site/crew requirements use explicit row editors and a visible save action. Tables have meaningful column labels and adapt to record cards when the content area is narrower than 1000px, including when the activity rail is open. Worker names and row actions remain visible. Native searchable/sortable lists are preserved; row metadata uses stable references and record-specific actions rather than likes/comments.

App-level report currency affects aggregate displays. Agreement/event editors label monetary fields with their saved currency and convert only at the accounting boundary using the agreed rate.


Worker identity uses one capsule with a 30px photo or initials, a legible name, and an optional remove/action affordance. Profile headers use the same identity at 52px. Worker editing keeps native save/validation behind a focused three-tab surface. Action dialogs are scoped to their originating record and restored hidden on close; cancellations discard uncommitted editor state. Help text uses a body-level overlay to avoid clipping by tabs/tables. Navigation section labels use muted 11px bold text, distinct from 13px links; drag grips appear on hover or keyboard focus. Schedule cells have at least 104px vertical room for date, demand and assigned values. Attendance heatmaps retain square cells and scroll within the panel for long periods.

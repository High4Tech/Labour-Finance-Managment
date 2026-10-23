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

Record sections use accessible top tabs. Supporting guidance lives behind 14px information controls aligned with the heading or field-label row; blocking errors remain visible. Native input heights are shared across both form columns, including error states. Checkbox controls retain native checked rendering at 16px.

Site/crew requirements use explicit row editors and a visible save action. Tables have meaningful column labels and adapt to record cards when the content area is narrower than 1000px, including when the activity rail is open. Worker names and row actions remain visible. Native searchable/sortable lists are preserved; row metadata uses stable references and record-specific actions rather than likes/comments.

App-level report currency affects aggregate displays. Agreement/event editors label monetary fields with their saved currency and convert only at the accounting boundary using the agreed rate.

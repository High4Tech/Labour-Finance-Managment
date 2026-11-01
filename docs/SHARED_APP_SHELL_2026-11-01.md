# Shared company header and navigation

Reference: the supplied Desktop.svg and Figma file `jZ63XyjbXM1v4evqYuzQLD`, header `23:16918`, sidebar `23:16717`. This promotes the Overview design into the company app shell; it does not replace native document pages or the platform administration shell.

## Ownership and visual contract

- `public/js/app_shell.js` and `public/css/app_shell.css` own the company breadcrumb, reporting currency, appearance, help, notification badge, upgrade link and mobile navigation variant. The existing `experience` scheduler mounts one persistent header. Overview consumes it instead of maintaining a second header/menu.
- Native sidebar links, permissions, search, section collapse/reorder and account actions remain authoritative. Navigation metadata supplies the reference order and labels. The sidebar uses the exported High4Tech wordmark, a bordered search field, orange selection and a white account panel with actual signed-in user information. No sample user, unread count or module count is invented.
- The shell uses system typography (14px/20px), 264px navigation, 4px spacing increments, 8px control radii, subtle borders/shadows and locally stored Figma icons. Desktop header height is 88px; the phone variant is 116px with two rows and a menu opener. Icon controls are 36px desktop / 40px phone. On the narrowest phones Upgrade becomes an accessible icon with the same label and destination.
- Orange remains `#FF5800`. Navy foreground on orange preserves the existing AA contrast decision. Light/dark surface, muted text, border, hover and focus variants share the shell tokens. Reduced motion disables shell transitions.
- The phone drawer reuses native sidebar contents, restores its previous expansion state, provides Close/Escape/backdrop actions and makes the underlying main page inert while open. Native account menus appear above the drawer; opening a dialog closes the drawer.
- Currency uses the existing saved reporting preference and refresh event. Options are supplied in boot data without fetching financial totals on every route. Notification counts use the native notification source. Native appearance saves the same framework preference; the company header uses the reference moon icon without loading hidden animated weather images.
- Initial report loads with missing required filters show an actionable prompt. Required filters, backend validation, exports and native accounting/stock capabilities remain intact.

## Verification

`scripts/browser-app-shell.cjs` checks all 15 main company destinations, persistent header identity, selected navigation, sidebar ordering/search/collapse, account keyboard access, company/theme/help controls, phone navigation, light/dark geometry at 320/390/768/1024/1440/1920px, targeted WCAG A/AA scans and idle activity. Evidence is written to ignored `.local/qa/app-shell/`.

`scripts/browser-overview-design.cjs`: 28 checks passed after promoting the header, including real data, four charts, responsive layouts, search, filtering, retry and route cleanup. `scripts/audit-workflows.py qa.localhost --app-shell`: 69 isolated hierarchy, permission, architecture and planning-list tests passed; test changes only update the intended navigation labels.

The broader suite was also run: 292 of 293 tests passed. The unrelated existing `test_imported_unused_event_can_be_deleted_without_deleting_its_receipt` expects deletion review to be clear, while the current deletion policy requires unused crew bookings to be released. No deletion controller, ledger or company record was changed by this shell work.

## Performance comparison

`scripts/browser-shell-performance.cjs` compares two isolated browser contexts per version, using saved commit `36aaa4a` assets only in the baseline browser. Business data and server remain identical. Small local samples are evidence against a material regression, not a general speed guarantee.

| Measure | Previous | Shared shell |
| --- | --- | --- |
| Dashboard ready, two runs | 3.35s / 3.44s | 3.42s / 2.92s |
| Date-period interaction | 544ms / 278ms | 331ms / 292ms |
| JS/CSS transferred (native framework included) | 9,636,430 bytes | 9,654,422 bytes |
| Dashboard data requests | 3 | 2 |
| DOM nodes | 12,954 | 12,928 |
| Idle shell mutations / extra requests in 1.5s | — | 0 / 0 |

The additional 17.6 KiB provides the shared shell and phone variant. No additional observer or polling loop was introduced, and unrelated scene/3D assets remain deferred.

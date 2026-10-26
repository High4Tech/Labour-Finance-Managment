# Stable company app layouts and shared controls

The reported issues had several separate causes: an unfinished builder was visible while its fields loaded; each keystroke rewrote the footer and triggered Freddy to recreate its markup; hidden review panels were also rebuilt; list enhancement ran a second render after selection setup; component wrappers retained old header actions when their contents refreshed; and worker-summary dialogs could still be closing when their pay dialog opened.

## Repairs

- Agreement/event builders retain a loading state until their final layout, fields and collaboration rail are ready. Worker profiles hide their native form from initial load and reveal the product editor after composition.
- Footer copy and avatars retain node identity when the message is unchanged. Field errors render Freddy synchronously, preserve unchanged feedback, and do not create empty error rows for valid fields. Platform forms retain plain-text errors.
- Shared UI enhancement no longer wakes on every pointer/key event. Mutations inside editable content and animation internals do not trigger a full-app enhancement pass. Hidden agreement review panels are not rebuilt during typing. Existing bounded draft autosave remains intact.
- List metadata sets name-column visibility before first render. Refresh reconciles selection against the actual records, resets cached header references and restores native actions. Leaving a list clears selection; unfinished list instances are guarded. No extra list render is used to make cosmetic changes.
- Payment schedules, vehicle requirements and resource panels have one heading and one header action group. Component redraws synchronously replace that group's actions instead of leaving duplicates. Add site is primary teal; category creation is secondary. Crew/category actions remain available within each site.
- “Record past work” is now **Allow dates in the past**. It explicitly enables historical entries while upcoming work still requires today or later. The unused space around the checkbox is removed.
- Worker-summary dialogs finish closing before pay/move dialogs open. Scheduling and daily-payment dialogs remove their hidden wrappers after closing.

## Button and icon system

`interface.css` implements the supplied reference using the existing palette: 32/40/48px small/default/large sizes, 14px default text, 8px icon gaps, primary/secondary/tertiary/ghost/destructive variants, pressed/disabled/loading/focus states and at least 44px touch targets. Next arrows follow the label. Theme changes do not animate button colors through low-contrast intermediate states. The public client-signing form reuses this stylesheet.

Streamline Core Line icons are combined into one local SVG sprite. Native icon calls, initial navigation metadata, profiles, actions, appearance controls and searchable pickers reuse that set. No third-party request is made for icons at runtime. Geometry sources and adaptations are documented in `public/images/STREAMLINE_LICENSE.md`; credits are available under **Company menu → About PLUS POINT**. Official source: [Streamline vectors](https://github.com/webalys-hq/streamline-vectors), CC BY 4.0.

## Verification

- `scripts/audit-workflows.py qa.localhost --ui-stability`: 39 backend tests pass for inputs, date boundaries, historical mode, salary/leave/loan limits, finance protection, event/draft creation, scheduling, list states, source-aware deletion and company isolation.
- `scripts/browser-ui-stability.cjs`: 11 checks pass, exercising actual scope typing, initial builder paint, payment generation, vehicle edits, selection/deselection, leaving/returning to a list, draft deletion, worker editing and repeated inline errors. It also checks shared client-signing buttons and automated desktop/mobile accessibility states. The client document is keyboard-scrollable on mobile.
- Typing probe: zero footer mutations, the same footer/avatar nodes throughout, and one enhancement pass during the scope-typing check. The date-option card has 23px of space below its final control.
- `scripts/browser-builders.cjs`: 12 checks pass for agreement save/conditions/review and event creation/budget controls, plus all nine editor steps at desktop/mobile sizes in light/dark themes.
- `scripts/browser-event-start.cjs`: 8 checks pass for actual event creation, scheduling cancellation, worker assignment/pay changes, one visible modal during the pay transition, singular resource actions after refresh and existing-event preservation.
- Browser fixtures are isolated and restored. Working account business data is preserved. Automated WCAG A/AA scans and viewport checks supplement interaction and visual checks; they do not certify every possible application state.
- Read-only working-account smoke: staffing controls, singular resource actions, the historical-date label, one vehicle heading, primary Add site, 40px buttons and Streamline navigation all pass. Agreement/event/worker/draft counts are unchanged; no browser runtime errors.

Backup: `backup/pre-ui-stability-20261026` at `b162009`. No database migration is required.

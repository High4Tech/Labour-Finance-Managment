# Community component review

Reviewed [21st Community](https://21st.dev/community/components) on 24 October 2026 for the existing company app. The app keeps its Frappe/ERPNext/HRMS controls, teal action tokens, native lists and server workflows. These are native adaptations of useful composition patterns, not imported React components or a new design system.

| Reviewed pattern | Applied in this app |
| --- | --- |
| [Origin UI Stepper, inline titles](https://21st.dev/@originui/components/stepper/with-inline-titles) | Agreement and event steps share separators, numbered current steps, completed checkmarks and an accessible completion description. Existing validation gates and Previous/Next handlers remain authoritative. |
| [shadcn Empty](https://21st.dev/@shadcn/components/empty/background) | Shared empty title/description for empty tables, vehicle reservations and warehouse equipment. Existing action buttons stay in their usual locations. |
| [shadcn Skeleton](https://ui.shadcn.com/docs/components/skeleton) | Shared static loading placeholders in record editors and resource profiles. One spoken status; decorative bars are hidden from assistive technology. |
| [shadcn Table](https://21st.dev/@shadcn/components/table) | Restrained row hover/focus feedback in the shared native table, preserving header relationships, inline controls and responsive labels. |

The reviewed Origin UI stepper/table and shadcn table pages identify MIT licensing. No third-party source files were copied or vendored. The new native code implements the composition using existing product controls and tokens; source references are retained here for provenance.

## Deliberate choices

- Preserve buttons, text inputs, date picker, searchable selects and dialogs. They already carry business validation, keyboard behavior and lifecycle cleanup; adding a second engine would create inconsistencies.
- Keep native sortable/selectable employee-style lists. The table treatment applies to the shared supporting tables; it does not replace lists with an unrelated grid.
- Loading placeholders are static: no repeated animations, background requests, new observers or framework dependencies.
- No 21st scripts, tracking pixels, remote fonts or runtime assets are loaded by the app.
- Empty-state title and description are escaped. Empty table messages occupy a single spanning cell; mobile labels are suppressed for that cell.
- Current step numbers use the shared primary action colour and white text in both themes. Keyboard focus is visible.
- No decorative shaders, animated backgrounds, magnetic buttons, new sidebar or marketing cards were added to operational screens.

## Verification

`scripts/browser-community-components.cjs` uses a disposable QA company and restores it in `finally`. It covers real editor transitions and resource dialogs, loading replacement, empty-state escaping, table semantics and keyboard feedback, 390px layout, both themes and scoped automated WCAG AA checks. Related draft-flow and component-validation suites are run separately against the same test workspace, sequentially to avoid competing fixture defaults. Results and screenshots are kept under ignored `.local/qa/`.

Backup: `backup/pre-community-components-20261024` points to `aae81fc`, the version before these changes. This release changes presentation only; there are no schema migrations or accounting changes.

### Results

- Shared component browser suite: 18 passed, including five scoped automated AA scans.
- Draft workflow regression suite: 20 passed, including six scoped automated AA scans. Partial drafts, tab-hide saving, recovery, daily milestones, scheduling, creation and reload behavior passed.
- Field component regression suite: 26 passed. Calendar boundaries, date ordering, corrective field errors, email/phone rules, integer input, salary/leave/loan limits and action spacing passed.
- All three disposable QA fixtures restored successfully. No unhandled browser errors in these runs.
- The final asset version is `20261024-community-2`. Working-site smoke checks confirm real agreement navigation, responsive empty states, the native worker list and bounded idle behavior.

These are targeted presentation and workflow checks, not a claim that every financial transaction or every WCAG requirement was manually audited for this release.

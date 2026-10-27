# Context-aware creation and shared components — 27 October 2026

This update applies the latest supplied three-stage workflow to the existing native Frappe application. It supersedes the five/four-stage presentation described in the earlier creation and consolidated architecture notes. No schema, financial controller, payroll engine, stock ledger or business record migration is introduced.

## Task journeys

| Journey | Previous presentation | Updated presentation |
| --- | --- | --- |
| Agreement | Client → details → sites/crew → milestones → review | Who and what → Commercial terms → Review and create |
| Job/event | Information → staffing → resources → schedule | Work details → Workforce and resources → Review and create |
| Existing client | Complete contact/address form repeated | Compact saved-client summary; Edit client details opens its original fields |
| Simple agreement | Crew commitments prominent by default | Quantities confirmed per event by default; agreed commitments remain available on expansion |
| Short event schedule | Month-wide timeline first | Relevant week first for events of seven days or fewer; Timeline/Month/Year remain selectable |
| Client link while signed into Desk | Read POST failed native CSRF validation | Read-only GET; acceptance POST supplies the current native session token |

The reduction from five/four displayed stages to three is directly observable. No task-completion time or speed improvement is claimed without measurement.

## Shared component ownership

`public/js/ui_components.js` and `public/css/ui_components.css` define the panel, metric, badge, disclosure, feedback and modal presentation. They use the bundled Tabler icons and existing theme tokens. Native FieldGroup, Dialog, lists, selectors, validation and server permission checks retain behavior.

- Creation canvas is light grey with white rail, form panels and collaboration panel. Heading bands reach panel edges; supporting heading buttons have a darker grey background.
- Text/search/select/date/currency controls use common heights, border, focus, disabled, error and success treatments. Native form and worker edit sections share the same surfaces. Field errors remain under the affected control and reserve their own space.
- List quick-search and native filter/reset/sort/status controls use 40px desktop heights and 44px mobile heights. Small controls outside that toolbar keep their appropriate size.
- Alerts use semantic colors, a stable icon/content layout and existing real actions. Field errors, draft-save status and routine messages do not gain an avatar. The existing green content loader and explicitly important avatar hook remain available.
- Desktop dialogs center from their first visible frame. The native upward slide is disabled; long bodies scroll within the viewport. Native focus trapping, close behavior, confirmation callbacks and mobile behavior remain.
- Agreement and event metrics use one shared centered-icon component. Native business status calculation remains authoritative.
- One existing bounded UI observer is reused. There is no new polling loop or per-field observer.

## Agreement behavior

Who and what retains client, title, validity, dates and scope controls. Existing complete client profiles appear as a compact summary. Missing required information remains editable. Client lookups reject stale responses, preserve edits made while a lookup is pending, and retain the current values on failure. A local Retry/Change client message provides recovery. The client's saved currency is suggested for new agreements while explicit or restored currency choices are preserved.

Commercial terms keeps daily/fixed pricing and existing payment schedule validation. Sites, crew, rate cards, conditions and vehicles are optional disclosures. The original validation gates run before moving forward or creating the agreement. Switching to Fixed refreshes the native amount control so a previous hidden state cannot conceal it.

Review and create uses the existing summary/edit actions and final creation confirmation. Save draft remains available. Email sending still requires the explicit checklist choice; creating/copying a portal link does not send mail. Existing document generation and the post-creation event/signing handoff are retained. Prepared event drafts are reused through the current draft controller.

Saved agreement pages lead with commercial terms and linked events. Contact details, dates/reference, conditions and vehicle commitments remain available on demand. Pricing still moves into the Milestones tab without duplicating the underlying component or financial obligation.

## Event behavior

Work details preserves agreement/standalone selection, client and inherited commercial context. Dates inherit from the agreement and remain editable within existing validity rules. Continuing prepares the actual internal Draft so the next stage has live worker and resource controls.

Workforce and resources retains category/count, actual worker selection and separate daily/monthly pay. Auto-selection appears only after a crew requirement exists. Vehicles/equipment are optional in this same stage. Review requires a staffing requirement or resource reservation, with a local correction action before the final save. No worker or resource is silently booked.

Review shows the current dates and worker-day coverage alongside the original actionable schedule. Final Save makes a future event Upcoming; unfinished events remain Draft.

Saved events show one recommended next action based on actual dates, coverage, commercial confirmation and native permissions: review terms, assign workers, review schedule, mark attendance or view finances. No future attendance approval is suggested. Ended dates do not mark invoices paid. Detailed crew/resource tables remain available through expansion and their existing tabs.

## Client portal and security

The reproduced failure was an authenticated POST read without the native CSRF token. Read-only review/refresh now uses GET. The uncached public page includes the current native session token for acceptance POSTs. Native CSRF validation remains enabled; a signed-in acceptance request without the token is still rejected.

Existing hashed/encrypted, expiring bearer grants, frozen agreement snapshots, acceptance evidence and scoped event progress remain unchanged. The portal does not expose worker identities, pay, loans, budgets, comments, profitability or other clients' records. Guest access and authenticated company-browser access are both exercised.

## Navigation and preservation

Clients and work precedes Workforce and resources in the new default order. A versioned tenant ordering preference avoids migrating the older Daily work-first arrangement into the new structure; future deliberate reordering remains personal. Platform administration keeps its prior ordering preference and navigation.

The existing agreement→multiple-event/standalone-event relationships, approved attendance, wage snapshots, loans, partial settlements, currency accounting, native invoices/receipts, stock valuation, availability conflicts, amendments, signed documents and tenant isolation are retained.

## Verification and evidence

Final results:

| Verification | Result |
| --- | --- |
| Full rollback-safe architecture/attendance/finance/component regression | 297 passed, 0 failures/errors/skips |
| Final commercial architecture/linked-event follow-up | 20 passed (a subset of the regression coverage) |
| Actual three-stage creation, authenticated/guest signing, failure recovery and layout browser journey | 19 passed |
| Actual equipment/vehicle reservation and popup browser journey | 7 passed |
| Working account read-only navigation/profile/Finance and record-count smoke | 5 checks passed |

The 26 browser checks include desktop/tablet/mobile overflow and automated WCAG A/AA scans in light/dark themes, centered-dialog geometry, actual assignment and save operations, native filter heights, and missing-token rejection. The deliberately injected client outage initially exposed an unhandled callback rejection; local handling was fixed and the final browser run has no runtime errors. The popup check exposed the native upward animation; desktop positioning is now stable from its first visible frame.

Working-site before/after counts matched: 6 contract-term records, 4 events, 50 workers, 1 invoice, 1 worker loan, 4 sharing grants and 4 planning drafts. Contract-term counts include internal event commercial bases, not only formal agreements. Records can subsequently change through normal user activity.

Full private working backup completed at `20261027_172821-high4tech-events-fd166a217c_localhost-*` under the site's private backups directory. Source recovery tag: `backup/pre-context-aware-20261027`, preserving `1d74579`. Asset version: `20261027-context-3`. QA mutation scripts use exact disposable companies and restore their records. Real outgoing email is not used. Working-site verification is read-only. Automated accessibility checks are coverage of tested views, not certification of every possible screen or assistive technology.

Browser evidence is generated under ignored `.local/qa/`: `context-ui-browser.json`, `context-agreement-desktop.png`, `context-event-desktop.png`, `context-list-filters.png`, `context-modal-geometry.json` and resource allocation evidence. Private database/files backup is outside Git.

## Files

Shared UI: `ui_components.js/.css`, `flow_builder.js/.css`, `feedback.js`, `experience.js`.

Workflow/profile composition: `operations.js`, `agreement_profile.js`, `event_profile.js`, `event_calendar.js`.

Portal/navigation/delivery: `signing.js`, `www/agree.py/.html`, `navigation.py`, `hooks.py`.

Verification: `scripts/browser-context-ui.cjs`, the existing resource browser and backend runners, and `tests/test_consolidated_architecture.py`.

## Limits

- No new AI service, external UI framework or separate portal authentication system was added.
- Existing native confirmation and financial authorization requirements remain. Optional disclosure is presentation, not permission to bypass them.
- Native accounting/report screens continue using their existing detailed forms and tables with the shared controls and surfaces; they were not replaced by a new application.
- SMTP delivery, production load testing and manual accessibility certification remain separate from these local checks.

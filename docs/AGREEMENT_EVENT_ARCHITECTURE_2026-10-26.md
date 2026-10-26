# Agreement and Event architecture update — 26 October 2026

## Scope and resulting flow

This is an extension of the existing Frappe/ERPNext application. The relationship is now **Client → optional formal agreement → one or more events → existing operations and finance**. No Job module, parallel accounting engine, authentication change, database reset or new DocType was introduced.

Existing agreements retain their Contract, Project and history. Additional deliveries get independent native Projects and existing PP Contract Terms records marked as event commercial snapshots. They reference the governing agreement and retain the negotiated rates, conditions and source version. Standalone events use the same native billing foundation, without displaying an internal billing record as a formal agreement in the company agreement list. One event still uses one operational Project.

The legacy `operations.create_plan` call remains idempotent for older callers. The new wizard/draft handoff requests a new occurrence; `agreement_events.create` is the explicit new API. Existing import templates keep their legacy agreement-first mapping.

## Changes visible to users

- The wizard keeps its green vertical rail. The order is Client details, Agreement details, Sites and crew, Pricing and milestones, Review and share. Billing setup is at the beginning of the sites/crew step, so the client currency and fixed/daily model are established before crew prices. Payment schedules and milestones follow the requirements, with estimated daily totals separated from approved invoiceable work.
- Fixed-period and ongoing agreements are supported. Fixed periods require an ordered end date. Ongoing agreements have no invented end date. Resource commitment can be fixed, estimated, minimum, a rate card or confirmed per event. Rate cards and per-event agreements do not require sites or crew quantities.
- Event creation supports From agreement and Standalone. Agreements remain selectable after their first event. Dates inherit from the agreement and remain editable within its validity. Each delivery has independent staffing, sites, vehicles, equipment, budget and expenses. A dated daily event can have its own payment schedule, including under an ongoing agreement.
- Existing agreement edits can be saved as drafts. Creation asks for explicit review in a confirmation dialog; there is no checkbox that appears mandatory while leaving creation unaffected. Email delivery controls use the available width and accept multiple CC addresses separated by commas, semicolons or new lines, up to ten addresses. Invalid addresses and email-header injection are rejected.
- Small radio groups align with neighboring fields and no longer retain native select arrows. Documents show a type icon, left-aligned filename and an accessible icon-only download. PDF previews close reliably even during their opening transition, and repeat clicks cannot stack loading previews.
- Agreement profiles show linked events with dates, states and links, plus a contextual Create event action. Standalone event profiles show their client and commercial controls without an empty agreement warning.
- A4 documents show ongoing validity, resource commitment and negotiated rate cards. Existing private document storage, frozen signed versions and invoice source links remain in use.

## Approval and history boundary

Profile popup edits and full agreement edits propose a change rather than immediately replacing current terms. The proposed values, summary, original version and exact client-visible document are stored in the existing immutable PP Agreement Share record. With outgoing email configured, the client receives a private link and explicitly approves the update by signing. Reading a link does not approve it. Current terms stay unchanged while the request is pending. A stale proposal cannot overwrite a later version.

The alternative **Client already agreed — record company attestation** applies the update with an audit entry explicitly identifying it as the company’s statement, not a client signature. This distinction also appears in the document evidence. Superseded unsigned requests are revoked after approval; signed history is retained. Native Contract edits and direct changes to shared/signed commercial terms cannot bypass this boundary.

Approved agreement updates do not rewrite existing event commercial snapshots, assignments, wages or invoice sources. New event rates outside the inherited commercial basis are explicitly marked Pending until their confirmation source is recorded. Pending event pricing blocks new invoices, including extra/native project invoices.

## Financial integrity

- Daily earned revenue continues to use approved work and its recorded client-rate snapshot. Payroll and attendance engines are unchanged.
- Fixed event amounts are explicit allocations, not repeated copies of the agreement value. Allocations and approved parent/event milestones share a locked agreement-wide ceiling. An existing legacy delivery can share its remaining fixed value with later deliveries; its displayed allocation becomes the residual rather than duplicating the total contract value.
- Each invoice retains one event Project. A parent daily billing period can generate separate native invoices for the relevant event snapshots. Existing source reservation and duplicate-invoice guards are retained.
- Agreement summaries aggregate the relevant projects once. Contract value, earned revenue, invoiced totals, cash, wages, expenses and contribution remain separate. Related event invoices also appear in the agreement’s Documents tab.
- Foreign-currency rate cards are converted once at the accounting boundary and shown in client units when edited or printed.

## Database changes and deployment

All changes are additive to existing entities:

| Existing DocType | Change |
| --- | --- |
| PP Contract Terms | Added `validity_mode`, `resource_mode`, `rate_card`, `event_basis`, `governing_agreement`, `commercial_status`, `commercial_source`, `recurrence_note`, `commercial_snapshot` |
| PP Agreement Share | Added `proposed_values`, `base_modified`, `approval_method`, `change_summary` |
| PP Event Plan | Staffing is optional during initial creation; commercial-link description updated |

The repeatable `agreement_events.install` reloads these three metadata definitions, backfills only blank validity modes from the existing end date, adds the governing-agreement/event-basis lookup index and clears cache. It is included in the existing migration hook. Existing records are not replaced, copied into new history or deleted. No attendance, wage, invoice or payment values are migrated.

Installed on QA and the working High4Tech Events account. The working profile opened without browser errors and the smoke check reported 50 workers. Production-account tests did not create sample agreements, events, workers, invoices or emails.

Recovery sources:

- Source tag: `backup/pre-agreement-architecture-20261026` at `ee8038b`.
- Database backup: `/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261026_223251-high4tech-events-fd166a217c_localhost-database.sql.gz` (1.3 MiB), with its matching private configuration backup. Keep configuration files private.

## Executed verification

Final counts are recorded from actual test output, with repeated cases counted once:

- **280 unique backend tests passed** across the broad regression run and focused follow-up runs. Coverage includes one/multiple events, standalone draft idempotency, ongoing agreements, rate cards, currency conversion, event budgets, actual approved work, separate event invoices, aggregate ceilings, legacy compatibility, stale approvals, native edit bypass protection, permissions, drafts, attendance, payroll and existing billing.
- **32 browser checks passed** across agreement architecture, sharing and event-start journeys. Mutation journeys used exact disposable QA fixtures and restored them. No browser runtime errors remained in the passing runs.
- Scoped automated axe checks passed for the tested profile, wizard, dialog and staffing surfaces in desktop/mobile sizes and light/dark themes, using WCAG A/AA rule tags through 2.2. This is scoped automated evidence, not certification of every app screen or PDF accessibility.
- The actual ongoing agreement PDF was rendered and visually inspected: one readable A4 page, 595 × 842 points, with ongoing validity and the negotiated rate card present. Actual invoice/signature PDFs and private-download denial were also exercised by the sharing journey.
- Changed Python, JavaScript and JSON files passed syntax/parse checks and Git whitespace checks.

Verification found and repaired compatibility issues in implicit end-date defaults, duplicate event/project names, draft reuse, standalone handoff, native date types, currency conversion, invoice allocation ceilings, selected-step contrast and preview-close timing. Test setup/selectors were also updated where the requested behaviour intentionally replaced the previous single-event or checkbox flow. The final passing runs are the evidence; earlier failures are not counted as passes.

Private run logs, signing tokens, screenshots and PDFs stay in `.local/qa/` and are excluded from Git. Real outbound email delivery was not exercised: email behaviour was tested with mocks, while actual private client preview/signature behaviour was tested in the browser.

Repeatable backend commands:

```text
docker compose exec -T -w /home/frappe/frappe-bench/sites frappe /home/frappe/frappe-bench/env/bin/python /workspace/scripts/audit-workflows.py qa.localhost --architecture-regression
docker compose exec -T -w /home/frappe/frappe-bench/sites frappe /home/frappe/frappe-bench/env/bin/python /workspace/scripts/audit-workflows.py qa.localhost --architecture-final
```

Browser journeys: `scripts/browser-agreement-architecture.cjs`, `scripts/browser-agreement-sharing.cjs`, `scripts/browser-event-start.cjs`. Run mutation journeys serially on QA, using the configured local Playwright/axe environment.

## Deliberate limits

- Future occurrences are planning notes; events and resource bookings are not automatically generated annually.
- Estimated/minimum requirements describe the commitment. Billing still follows approved attendance or fixed milestones; no new minimum-charge or shortfall-billing engine was added.
- Legacy records preserve their original relationships. New occurrences use independent snapshots. Existing upload templates remain compatible with their agreement-first workflow; standalone entry is available through the wizard and new API.
- Client approval email requires a configured outgoing account. The current development site uses a localhost URL; external clients need the deployed site’s public HTTPS URL.
- Existing submitted financial history remains protected. Changing staffing or dates may require first adjusting unused operational allocations; approvals do not rewrite earned work or posted invoices.

## Exact files changed

- `apps/plus_point/plus_point/agreement_documents.py`
- `apps/plus_point/plus_point/agreement_events.py`
- `apps/plus_point/plus_point/agreement_updates.py`
- `apps/plus_point/plus_point/api.py`
- `apps/plus_point/plus_point/billing.py`
- `apps/plus_point/plus_point/daily_billing.py`
- `apps/plus_point/plus_point/drafts.py`
- `apps/plus_point/plus_point/event_testing.py`
- `apps/plus_point/plus_point/events.py`
- `apps/plus_point/plus_point/hooks.py`
- `apps/plus_point/plus_point/install.py`
- `apps/plus_point/plus_point/operations.py`
- `apps/plus_point/plus_point/planning_list.py`
- `apps/plus_point/plus_point/plus_point/doctype/pp_agreement_share/pp_agreement_share.json`
- `apps/plus_point/plus_point/plus_point/doctype/pp_agreement_share/pp_agreement_share.py`
- `apps/plus_point/plus_point/plus_point/doctype/pp_contract_terms/pp_contract_terms.json`
- `apps/plus_point/plus_point/plus_point/doctype/pp_contract_terms/pp_contract_terms.py`
- `apps/plus_point/plus_point/plus_point/doctype/pp_event_plan/pp_event_plan.json`
- `apps/plus_point/plus_point/plus_point/doctype/pp_milestone/pp_milestone.py`
- `apps/plus_point/plus_point/public/css/flow_builder.css`
- `apps/plus_point/plus_point/public/css/interface.css`
- `apps/plus_point/plus_point/public/js/agreement_profile.js`
- `apps/plus_point/plus_point/public/js/agreement_share.js`
- `apps/plus_point/plus_point/public/js/choices.js`
- `apps/plus_point/plus_point/public/js/daily_billing.js`
- `apps/plus_point/plus_point/public/js/drafts.js`
- `apps/plus_point/plus_point/public/js/event_profile.js`
- `apps/plus_point/plus_point/public/js/flow_builder.js`
- `apps/plus_point/plus_point/public/js/operations.js`
- `apps/plus_point/plus_point/public/js/profiles.js`
- `apps/plus_point/plus_point/public/js/signing.js`
- `apps/plus_point/plus_point/reporting.py`
- `apps/plus_point/plus_point/signing.py`
- `apps/plus_point/plus_point/tests/test_agreement_architecture.py`
- `apps/plus_point/plus_point/tests/test_agreement_sharing.py`
- `apps/plus_point/plus_point/tests/test_drafts.py`
- `apps/plus_point/plus_point/tests/test_event_start.py`
- `apps/plus_point/plus_point/tests/test_hierarchy.py`
- `apps/plus_point/plus_point/workflows.py`
- `apps/plus_point/plus_point/www/agree.html`
- `scripts/audit-workflows.py`
- `scripts/browser-agreement-architecture.cjs`
- `scripts/browser-agreement-sharing.cjs`
- `scripts/browser-event-start.cjs`

- `docs/AGREEMENT_EVENT_ARCHITECTURE_2026-10-26.md` (this implementation and verification report)

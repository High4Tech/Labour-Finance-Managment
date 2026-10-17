# Research alignment — 2026-10-17

The owner supplied the “PLUS POINT — Complete Project Context & Development Handoff” on October 17. Its business requirements guide this implementation. Its historical notes saying installation, live tests and Git pushes were unverified describe an earlier stage; current observations belong in VERIFICATION_STATUS.md.

## Product boundary

PLUS POINT serves labour contractors and workforce suppliers. The core chain is **client → contract → project → work site → dated worker assignment → attendance → wages earned → client billing → costs → project results**. High4Tech manages a separate chain: **tenant → users → monthly subscription → billing → access/limits → renewal or suspension**. A paying tenant and its client companies remain different records in different contexts.

Frappe Desk, authentication, roles, APIs, migrations and reports are reused. ERPNext owns Customer, Contract, Project, invoices, Payment Entries, accounting, expenses and subscriptions. HRMS/Employee supplies worker profiles and optional standard HR workflows. PLUS POINT adds the contractor-specific data and calculations. Broader native modules such as Manufacturing are optional upstream tools, not new PLUS POINT scope. No native modules or existing customer records were deleted during this review.

## Findings and corrections

| Research requirement | Observed implementation and action |
| --- | --- |
| Daily billing and worker wages use separate rates | Retained approved work snapshots and server-side full/half/absent day calculations. |
| Fixed contract value differs from earned revenue | Retained milestone recognition and contract cap. Fixed worker days produce wages without direct client revenue. Reports state this explicitly. |
| Revenue, invoices, receipts, wages earned/paid and profit must remain distinct | Existing financial API already separated them. Added **PLUS POINT Project Finances** in the native report interface, accessible from home, billing terms and Project. Replaced the raw field-name popup with the report. |
| Companies, sites, deployments and workforce days must be understandable | Added the report's **Deployment overview**, with client/project filters, active sites/contracts, distinct deployed workers and approved day units. Deployment is labelled as assignment-based rather than proof of attendance. |
| Worker history, rate history, payments and balances should be easy to access | Added **PLUS POINT Worker Statement**, available from home and Employee. It includes client/project/site work history, actual settlement-linked payments, opening/period/closing balances, date filters and an **Assignment history** view. Native export and print controls are reused. |
| Workers transfer between sites and rates change without rewriting old earnings | Found that used assignments could never be closed. Now allow an earlier end date only when it includes every saved work entry, including drafts. Worker/site/project/start/rates stay locked. Start a replacement allocation the next day. Native Version tracking remains enabled. |
| Validate overlapping assignments and prevent duplicate attendance | Added serialized same-worker/same-site date-range validation. Different-site allocations remain possible for split days; existing work-entry validation still caps the worker at one day across all sites. |
| Monthly SaaS with separate High4Tech administration | Existing native subscriptions/plans, independent site databases, trusted provisioning worker and server-side access/quotas retained. No custom gateway or shared-table tenant system introduced. |
| Reuse a mature reporting and accounting system | Added small native Script Reports over approved PLUS POINT records and existing financial API; no reporting UI, ledger, authentication or accounting engine was rebuilt. |

## Scope and remaining gaps

Project financial figures are **lifetime project totals**, including completed projects unless filtered. The report deliberately does not invent dated or site-level profitability from cumulative native project costs and undated milestone approval. Select a client/project for its scope; use Worker Statement for dated activity. Financial totals require one legal company/currency. Operational contribution excludes documented costs and is not statutory net profit.

Worker statements use approved work and submitted settlements linked to employee Payment Entries. Advances and unallocated payments remain native records and are not silently subtracted from the contractor wage balance. Assignment history preserves allocations with no attendance. No fixed-project revenue allocation to individual workers is implied.

These corrections improve the core MVP; they do not complete the entire roadmap. Dedicated tenant administrator/supervisor/finance role and field-privacy acceptance, attendance correction/reversal, contract-level accounting-source attribution, dedicated site/closure reports, approval timestamps for historical revenue recognition, representative bulk/concurrent performance, provider webhooks, production deployment and backup/restore acceptance remain work. Employee default wage automation is not implemented; dated assignment rates remain the source of truth. The existing read-only APIs and basic role restrictions are not a substitute for those remaining acceptance requirements.

Press remains an evaluated option for future hosting operations. Live payment-provider choice, production hosting prices and commercial delivery dates are still undecided; historical estimates in the handoff are not current quotes.

## Verification

See VERIFICATION_STATUS.md for executed database/browser/export checks and limitations. TEST_PLAN.md and LOCAL_RUNBOOK.md describe reproduction. No customer data was rewritten to fit the research brief.

# Worker salary, leave and loan workflow

Open a worker by name. **Edit profile → Salary and leaves** contains daily or monthly salary, monthly leave allowance, loan eligibility, waiting months from joining, and the usual recovery percentage. Monthly salary provides a payroll rate of salary ÷ 30 for approved work; entering salary settings does not post wages for unworked days. Existing recorded wage rates remain historical snapshots.

New workers default to Active. An inactive saved worker has **Activate worker** on the overview. Activation still observes the subscription limit and company permissions.

**Assign leave / half day** records a dated leave with a reason. Full days count as 1 and half days as 0.5 against that calendar month’s allowance. Duplicate leave and dates outside employment are rejected. A full day of approved leave removes the worker from that day’s register; half leave limits attendance to half a day. Existing approved attendance must be corrected before leave is added. The activity calendar and event coverage show the effect of leave, and the crew selector prevents overlapping full-event bookings.

**Assign to an event** lists active upcoming events by name. Matching positions show their site, dates and free places. Where no position is free, **Add as extra crew for this event** explicitly adds event demand and an allocation, keeping the client agreement unchanged. The server rechecks active employment, category, company, leave, dates and conflicting allocations at assignment time. A worker cannot be assigned twice to the same event.

## Loans and actual money

**Assign loan** checks the worker’s eligibility on the disbursement date. Enter the amount, purpose/terms, date and monthly recovery percentage. All worker pay and loans use the company’s accounting currency.

- Without a payment, the loan is a draft. It does not reduce outstanding wages or count as money advanced.
- Record and submit an ERPNext employee Payment Entry to an **employee advance receivable** account. Its date, worker, company, currency and amount must match the loan. Use **Record disbursement** to link it. A wage payment cannot also be used as a loan, and a payment cannot disburse two loans.
- The overview displays the loan balance, approved wage outstanding, proposed monthly deduction, and the balance after that proposal. A proposal does not post money.
- **Post monthly deduction** chooses an event and posts an ERPNext Journal Entry debiting employee payable and crediting the advance receivable. A `PP Loan Recovery` links that exact journal to the worker, loan, month and project. The recovery is capped by approved earnings × the declared percentage, unpaid wages, and the remaining loan balance. Each loan has at most one active recovery per month.
- Cash wage settlements cannot exceed wages remaining after recorded recoveries. The worker statement and project summary distinguish cash payments from loan recoveries. Recoveries do not inflate project revenue or labour cost.

Submitted records are retained. Cancel recovery through its record to reverse its exact journal; cancel recoveries before cancelling a loan. The native accounting record cannot be independently cancelled while its active loan/recovery link remains.

## Agreement revisions

Agreement tabs are **Client details → Agreement details → Pricing and milestones → Sites and crew → Send and sign**. Conditions are repeatable rows included in the client signature snapshot. Agreement currency is chosen in pricing, independently of the client and the top-bar report currency. Changing display currency converts form amounts while preserving accounting value; historical invoices keep their own currency and rate.

Each site contains a crew table. Fixed pricing hides wage/rate columns and uses the fixed agreement value plus milestones; payroll comes from existing payroll rates or worker salary settings. Daily pricing requires category payroll wages and client rates.

Editing targets updates the event plan and unused assignment rates. Saved attendance preserves its assignment/rate snapshots. Removing an agreement requirement that still has deployed workers keeps that deployment as extra event crew, visible against the revised agreement. It does not erase attendance or silently unassign people. Sites can be saved before their first crew row is added.

## Installation and verification

The normal migration hook installs Employee benefit fields, agreement conditions and the `PP Worker Leave`, `PP Worker Loan`, and `PP Loan Recovery` records. No benefits or cash postings are fabricated for existing workers. Before the schema update is installed, the overview remains readable and the new benefit actions show as unavailable.

Run the rollback integration suite with `bench --site demo.localhost execute plus_point.testing.run_hierarchy`. Run `node scripts/browser-worker-flows.cjs` with Playwright and Chrome for isolated QA screen checks. The browser fixture deletes only its exact disposable leave and unpaid loan records; it refuses cleanup when financial postings or a disbursed loan are present.

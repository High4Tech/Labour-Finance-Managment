# Payments, costs and worker loans

Payments and costs has four native work lists: Worker payments, Worker loans,
Receipts and payments, and Expenses. These use the same selection, filtering,
sorting and record actions as the employee list. No status/date filters are
automatically applied by the finance shortcuts.

Business reports remains a dedicated sidebar section with its overview,
Project finances and Worker statement. Worker reimbursements are reachable from the payments overview and the Expenses
list; supplier invoices and employee reimbursements keep their distinct native
approval and accounting records.

The entire Business setup section is removed from customer navigation. Billing
items, suppliers, accounts and wages earned remain supporting records. Hiding these links does not
remove the chart of accounts, earnings or historical financial records. The
separate High4Tech software administration navigation is unchanged.

## Loan management

Use Worker loans → Assign loan, choose a worker, and enter the amount, date,
monthly recovery percentage and purpose/terms. The existing eligibility check
applies. A loan without its matching submitted employee advance payment is an
**unpaid draft**, excluded from money advanced and loan balances.

The native loan list shows worker names, amounts, dates, recovery percentages,
loan status and the remaining balance. Open a loan for disbursement, a selected
month's proposed recovery, wage outstanding before/after the proposal, and
recovery history. All amounts are in the company's accounting currency.

Record disbursement links a matching real Payment Entry. Post monthly deduction
uses the existing checked accounting workflow: it caps recovery by approved
earnings, unpaid wages and the balance, and allows one active deduction per
loan per month. A proposal never posts money. See [Worker benefits](WORKER_BENEFITS.md)
for exact validation and cancellation rules.

Section totals use permission-scoped database aggregates. Loan list balances
load only for the current page (up to 200 records); per-worker monthly amounts
load only when opening a loan or changing the month. There is no finance polling
timer or persistent balance cache. Refresh or completing an action loads current
values. Route changes discard the custom summary and reject late responses.

## Backup and verification

Before this change, the source was preserved at Git tag
`backup/pre-finance-simplification-20261023`, also as an ignored local ZIP.
The customer site's database and both uploaded-file stores were backed up with
the site backup tool. Customer databases, uploads and credentials stay outside Git.

Rollback accounting tests: `bench --site demo.localhost execute plus_point.testing.run_hierarchy`.
Browser flow: `node scripts/browser-finance.cjs`, with Playwright and Edge (or
`PP_TEST_BROWSER` for another installed Chromium browser). The browser run uses
an exact disposable QA company and unpaid draft; it never posts customer money.

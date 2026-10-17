# Using PLUS POINT

Start at **PLUS POINT → Workforce home**. Customer logins open this workspace by default unless an administrator has chosen another starting app. The overview groups everyday work into attendance, workers and work sites, client billing, and worker payments.

Choose **Mark attendance**, select the work site and date, then **Review attendance**. This prepares a draft with assigned workers, or reopens the saved register for that site and date. Review the entries before **Submit** approves earnings. Opening attendance never approves it automatically.

The sidebar groups **Daily work** and **Billing and payments**. Expand **More** for clients, contracts, projects and fixed contract milestones. Lists use labels such as **Add work site** and **Assign worker**, with internal record IDs removed from the main list display. Native permissions still determine which links and actions you can use.

For help, use **How it works**, **Show me around**, or expand the six-step **Quick start**. Quick start and **More tools and setup** begin collapsed; the guide remembers your preference in this browser for your login and site. Fields with a **?** explain what to enter; hover, focus with the keyboard, or tap the button. Longer field guidance appears when you focus the field. **Explain this screen** opens guidance for the current record.

## Which app does what?

| App or area | Use it for |
| --- | --- |
| PLUS POINT | Your contractor workflow: sites, worker allocations, dehadi, daily and fixed billing, wage settlements and project figures. This is the usual starting point. |
| ERPNext | Shared client, contract, project, invoice, payment and accounting records. PLUS POINT opens these records when needed; you do not need to maintain a second copy. |
| Frappe HR | Employee profiles, leave, shifts and standard payroll. Employee self-service requires a login linked to an active Employee. |
| Framework | Login accounts, roles, permissions and system settings, mainly for administrators. |
| High4Tech admin | The separate platform site for subscriber organizations, subscription plans, trials, renewals, access limits and suspension. Customer workforce records remain in their own site database. |

Manufacturing is an optional ERPNext module for factories and production. It is outside the PLUS POINT labour-contracting workflow. You can return from other Desk modules using **Workforce home**. These broader modules remain available to authorized users; onboarding does not remove or change permissions.

## Follow one job

1. **Set up the client and job.** Your **Company** is your own business. A **Client company** is the organization paying you. Create its Contract and Project.
2. **Agree billing terms.** Link the contract and project, choose Daily or Fixed, and activate the terms when agreed.
3. **Allocate workers.** Create the project's Work sites, add Workers, then create dated Worker allocations with agreed wage and client rates.
4. **Record attendance.** On Workforce home choose **Mark attendance**, select the site and date, then **Review attendance**. You can also use **Prepare daily attendance** on a work site. Review 1 for a full day, 0.5 for a half-day, or 0 for absence. Save a draft for review; Submit creates approved worker earnings. A worker can total at most one full day across sites on a date.
5. **Invoice the client.** Open active Billing terms and choose **Prepare client invoice**. Review and submit the native invoice, then record client receipts with Payment Entries.
6. **Pay workers and review figures.** Record a submitted employee Payment Entry and link it in Worker payments. Open Billing terms → **Project finances** to review earnings, receipts, wages and outstanding balances.

## The two billing models

- **Daily:** client earned revenue is approved day units × the worker's agreed client rate. Worker earnings are the same units × the worker wage rate.
- **Fixed:** client earned revenue comes from approved milestones within the agreed contract value. Worker daily wages remain independent of that revenue.

Approved work keeps its historical rates. To transfer a worker or change rates, set the old allocation's last date, then create the new dated allocation. The old end date must include every saved work entry, including drafts. A used allocation cannot reopen or extend, and the same worker cannot have overlapping allocations at the same site. Different sites may share a date for split days, subject to the one-day attendance limit.

## Business reports

On Workforce home, use **Business reports**:

- **Project finances** separates fixed contract value, revenue earned, invoices, cash received, wages earned/paid/outstanding, other project costs and operational contribution. Select your own company, then optionally a client, project or project status. Completed projects are included unless filtered. Change **Show** to **Deployment overview** for sites, active billing contracts, assigned workers and workforce days. Deployed today means an active assignment, not confirmed attendance.
- **Worker statement** shows approved work and settlement-linked payments for a worker, with opening and closing wage balances. Filter by client/project and dates. Change **Show** to **Assignment history** for deployments and agreed rates, including allocations with no attendance. You can also open this report directly from the worker's Employee record.

Project and Billing terms records also have **Project finances** shortcuts. These are native Frappe reports with the existing export and print controls. Project figures cover the lifetime of the selected projects; worker dates filter actual work/payment records. Advances and unallocated payments are excluded from the statement. Reports currently require the manager role; dedicated supervisor/finance permissions remain separate work.

## Terms that should stay separate

| Term | Meaning |
| --- | --- |
| Company / client | Your own legal business / the customer hiring it. |
| Worker / user | A workforce profile / someone allowed to log in. Most workers do not need a user account. |
| Contract value / earned revenue | The total agreement / the portion earned through approved work or milestones. |
| Invoice / receipt | A bill issued to the client / money actually received. |
| Wages earned / wages paid | What approved work owes the worker / a real payment allocated to those earnings. |
| Work site / tenant site | A physical job location / an isolated customer organization's application and database. |

PLUS POINT daily registers do not automatically create HR Attendance or run HR payroll. Worker settlements allocate existing payments; they do not send bank transfers. Project figures are operational contribution, with documented cost exclusions, rather than certified statutory net profit.

## What was customized?

The custom extension implements sites, dated allocations, attendance registers and rate snapshots, daily/fixed billing integration, milestones, wage settlements, project reporting and tenant access controls. Customer and employee management, invoices, payments, accounts, login, permissions and the underlying Desk are reused from Frappe, ERPNext and HRMS, as requested in the original brief.

The current installation is a tested local development version. Dedicated production role/privacy controls, audited attendance corrections, live payment-provider integration and deployment/backup acceptance remain separate work; see VERIFICATION_STATUS.md. Installing the upstream apps does not mean every optional upstream feature has been audited or tested for this product.

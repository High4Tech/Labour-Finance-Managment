# Using PLUS POINT

Start at **PLUS POINT → Workforce home**. The workspace has **How it works**, a **Show me around** tour and a quick-start guide you can collapse. Fields with a **?** explain what to enter; hover, focus with the keyboard, or tap the button. **Explain this screen** opens guidance for the current record.

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
4. **Record attendance.** Open a work site and choose **Prepare daily attendance**. Review 1 for a full day, 0.5 for a half-day, or 0 for absence. Save a draft for review; Submit creates approved worker earnings. A worker can total at most one full day across sites on a date.
5. **Invoice the client.** Open active Billing terms and choose **Prepare client invoice**. Review and submit the native invoice, then record client receipts with Payment Entries.
6. **Pay workers and review figures.** Record a submitted employee Payment Entry and link it in Worker payments. Open Billing terms → **Project finances** to review earnings, receipts, wages and outstanding balances.

## The two billing models

- **Daily:** client earned revenue is approved day units × the worker's agreed client rate. Worker earnings are the same units × the worker wage rate.
- **Fixed:** client earned revenue comes from approved milestones within the agreed contract value. Worker daily wages remain independent of that revenue.

Approved work keeps its historical rates. Use a new dated allocation for changed rates.

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

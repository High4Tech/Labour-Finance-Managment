# Using PLUS POINT

Start at **PLUS POINT → Workforce home**. Customer logins open this workspace by default unless an administrator has chosen another starting app. The overview groups everyday work into attendance, workers and work sites, client billing, and worker payments.

Choose **Mark attendance**, select the work site and date, then **Review attendance**. This prepares a draft with assigned workers, or reopens the saved register for that site and date. Review the entries before **Submit** approves earnings. Opening attendance never approves it automatically.

The sidebar groups **Daily work**, **Clients and billing**, **Payments and costs** and **Business reports**. Expand **Business setup** for staff accounts, company, items, suppliers and accounts. Lists use labels such as **Add work site** and **Assign worker**. Native permissions determine the links and actions available to your login.

For help, use **How it works**, **Show me around**, or expand the six-step **Quick start**. Quick start and **Business setup** begin collapsed; the guide remembers your preference in this browser for your login and site. Fields with a **?** explain what to enter; hover, focus with the keyboard, or tap the button. Longer field guidance appears when you focus the field. **Explain this screen** opens guidance for the current record.

## Two sides of PLUS POINT

| Side | Who uses it and why |
| --- | --- |
| PLUS POINT | Each subscribed customer business manages its own clients, workers, work sites, attendance, wages, invoices and project results. Local customer workspace: `demo.localhost:8000/desk/plus-point`. |
| High4Tech admin | High4Tech manages subscribed businesses, subscription plans, trials, billing, renewals, limits and suspension on its separate platform site. Local owner workspace: `platform.localhost:8000/desk/high4tech`. |

Each site opens its own focused workspace. The sidebar and search suggestions contain the relevant product records. App/module switching menus, HR tools, Manufacturing and other unrelated workspaces are removed from the interface. Opening an unrelated Desk route returns to this site's overview. Native ERPNext/HRMS dependencies remain installed to power invoices, accounts and workers; this navigation change does not replace backend permissions.

The platform guide explains software customer setup, pricing, support, billing and access. A customer business can have its own administrator and staff; those accounts do not become High4Tech platform administrators.

## High4Tech customer support and software finances

Open **Customers**, choose the PLUS POINT business, and use **Change customer login ID** or **Reset customer password**. A support request is queued for the native worker. Open **View support result** to check completion; reload the request if its displayed status is old. Login-ID changes keep the customer's email address and sign out existing sessions. Reset produces a native one-time link; the old password is never shown. No email is sent automatically. Share the link only with the verified account owner through your established support process. The protected result is displayed to platform administrators for up to 20 minutes, and native reset expiry also applies. A suspended subscription must be reactivated before the customer completes the native reset form.

**Pricing plans** sets recurring software prices; **Subscriptions** links a billing customer, plan and period. **Customer accounts** links that subscription to the customer's independent application and owner email. Access changes normally reach the customer within one minute while the local synchronization worker is running. Changing a plan is not proof that money was received: review the native subscription/invoice before billing.

Use **Software invoices** for software sales, **Receipts and payments** for money actually received or paid, **Business expenses** for your operating costs, **Financial results** for the native profit/loss report and **Outstanding invoices** for unpaid bills. These are High4Tech's accounts, separate from each customer's clients, wages and project finances. Billing setup contains the supporting company, service items, billing contacts, suppliers and accounts.

The local PLUS POINT Demo is registered as a trial software customer; no real purchase or receipt was fabricated. QA is an isolated test customer. Live payment collection and outgoing email are not connected in this development setup.

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

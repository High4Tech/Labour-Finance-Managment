# Using PLUS POINT

Start at **PLUS POINT → Workforce home**. Customer logins open this workspace by default unless an administrator has chosen another starting app. The overview groups everyday work into attendance, workers and work sites, client billing, and worker payments.

The overview starts with a dashboard. Choose your **Company** and use **Refresh figures** for the latest saved records. PLUS POINT shows active workers/sites, unpaid wages, the client invoice balance, approved attendance over seven days and a project snapshot. Financial totals are lifetime figures for projects with PLUS POINT billing terms; the attendance chart counts approved worker-days. Draft attendance is excluded. All existing work links remain under **Work tools**.

High4Tech's dashboard shows registered software customers, trial/access status, invoices and customer receipts this month, outstanding invoices, six months of billed/received figures and customer access needing attention. Financial figures belong to the selected High4Tech company. Trials are not sales; cash receipts and invoice totals are separate. Amounts include posted invoice taxes, receipts are net of refunds, and future-dated postings are excluded from the monthly chart. Existing links remain under **Your tools**. Zero and empty states use actual saved data, without sample revenue.

Choose **Mark attendance**, select the work site and date, then **Review attendance**. This prepares a draft with assigned workers, or reopens the saved register for that site and date. Review the entries before **Submit** approves earnings. Opening attendance never approves it automatically.

The sidebar groups **Daily work**, **Clients and billing**, **Payments and costs** and **Business reports**. Expand **Business setup** for staff accounts, company, items, suppliers and accounts. Lists use labels such as **Add work site** and **Assign worker**. Native permissions determine the links and actions available to your login.

For help, choose **Help**. It contains the contractor workflow and optional **Guided setup**. Fields with a **?** explain what to enter; hover, focus with the keyboard, or tap the button. Longer field guidance appears when you focus the field. **Explain this screen** opens guidance for the current record.

## Guided setup

New, unfinished businesses with no assignments open guided setup automatically. An established business, including the seeded demo, has no setup banner or repeated onboarding prompts on its overview. To deliberately open or resume the guide, choose **Help → Guided setup**. It focuses on one step while the rest of the workspace is blurred and unavailable to clicks or keyboard focus. **Skip setup and explore** releases the workspace immediately and removes the setup prompt. Your saved step follows your login across reloads. This focus mode does not change anybody’s account permissions or block another staff member.

After selecting or creating your own company, add or choose one **worker**, add or choose a **work site** under its client project, select or record the **client billing agreement**, then **assign the worker** with dates, a daily wage and the client rate. A new project and client can be entered within the site step. Fixed-price billing uses a zero worker-day client rate. The guide saves real records one step at a time. Skipping retains those saved records. Completing setup does not approve attendance, send payments or create employee logins.

## Import employees and existing finances

Choose **Import** beside the top **Add** action on the relevant employee/finance list, or **Import employees or finances** in the last guided setup step. Select your company and import type, then **Download template**. **Download reference IDs** provides the existing projects, assignments, billing terms, employees, suppliers, customers, service items, cash/bank ledgers and unpaid client invoices. The reference download is capped at 1,000 records per supporting type; use native lists to find additional IDs.

You can also choose **Import** beside the top **Add** button on Workers, Wages earned, Fixed milestones, Project expenses, Client invoices, Receipts and payments, or Worker payments. This remains available on populated lists and after refresh. The window selects the corresponding import type and shows **Download template** above the instructions and file chooser. Expand **How to fill this template** when needed. You can add more rows later or update employee profiles using their existing IDs.

Fill the template in Excel or Google Sheets. Keep its headers and use one worksheet, stable source IDs, YYYY-MM-DD dates and company-currency amounts without currency symbols or thousands separators. Format IDs and phone numbers as text. Replace formulas with values. From Google Sheets choose **File → Download → CSV** or **Microsoft Excel**. Upload UTF-8 CSV or XLSX, at most 200 rows and 2 MB per file. This is an uploaded snapshot, not a live Google Sheets connection.

| Template | What the system saves |
| --- | --- |
| Employees | Native employee profiles. A new stable `external_id` with blank `employee` creates a profile. An explicit existing Employee ID updates that company’s profile. Reusing an imported ID updates the same profile; optional blank last name/phone clear those fields. No user account is created. |
| Approved daily work | Dated work under existing assignments; units 1, 0.5 or 0. Wages and daily client earnings use the agreed historical assignment rates. |
| Fixed-price milestones | Approved milestone earnings under active Fixed billing terms, within the fixed contract cap. |
| Project expenses | Posted, unpaid supplier invoices for net project service expenses. These update project costs and spending budgets. |
| Client invoices | Posted client invoices and receivables. Link approved work/milestones using both `source_type` and `source_name` to reserve their earnings against rebilling. Blank source fields record a legacy invoice only; they do not invent operational earned revenue. |
| Client receipts | Posted historical money received, allocated to a submitted client invoice. Partial receipts reduce its outstanding balance. |
| Worker payments | Posted historical employee payments and wage settlements, limited to approved outstanding wages. |

Import employees and assignments before their daily work, then import work/milestones before related invoices or worker payments, then client receipts. A reference such as `import:invoice-001` can identify an invoice from an earlier invoice import; the same syntax works for invoice work/milestone sources and employee references in worker payments. Imports never contact a bank or send money.

**Review file** shows row actions, amounts, errors and projected spending. Nothing is saved at this point. Fix invalid rows or download the error list; select the confirmation only after reviewing the valid preview, then choose **Import employees** or **Import and post records**. Final native posting and permission checks run again. If any row fails, the entire file is rolled back, with a row-specific reason. A preview expires after 20 minutes and belongs to the signed-in user.

Repeated identical financial rows with the same company, import type and `external_id` are skipped. Changed posted rows are rejected rather than overwritten: review/cancel/correct the original record and use a new source ID for its reviewed replacement. Keep the original IDs when splitting files or retrying; changing an ID represents a new source record. Employee profiles remain editable through the employee import. Saved-record links and the refreshed dashboard help review the result.

The finance templates support net service invoices in company currency. Tax breakdowns, stock, foreign currencies, supplier payments, expense claims and general opening journals use their native accounting forms. Project spending uses its existing defined cost scope. Importing an invoice or a receipt does not substitute for the underlying work/milestone earnings. Existing native accounting periods, spending stops, contract caps and subscription limits still apply.

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

## Spending limits and next actions

A spending budget is separate from what you charge the client. Open **Projects**, choose the project, enter **Spending budget**, enable **Stop spending above budget**, then save. This uses the native Project estimated-cost field; a business administrator must approve budget changes. Existing projects keep enforcement off until you choose a limit.

Tracked spending is approved PLUS POINT wages, posted net project purchase items and sanctioned expense-claim lines in company currency. It excludes taxes, overhead, timesheets, stock consumption, manual journals and costs without a project. Do not enter the same worker wages again as purchases or claims. Client invoices, fixed milestones and wage payments do not consume this spending budget again.

| State | What happens and the next action |
| --- | --- |
| Below 80% | The spending check shows **Within budget**; use **Review spending budget** to inspect it. |
| 80% through 100% | Amber warning. Before approving wages/submitting a register or expense, choose **Confirm within budget** or **Review costs**. |
| A proposed cost exceeds 100% | Approval/submission stops before posting. Review cost entries or ask your administrator to revise the budget. Drafts stay available. The server also blocks direct API submissions. |
| Recorded costs already exceed a revised budget | Red spent/remaining figures and **Review spending budget**. Recorded wages/expenses remain intact. Cost-reducing reversals and zero-cost records remain possible. |
| No budget or no company/projects/workers | A setup state links to the next relevant record. Existing work tools remain available. |
| Attendance/wages submitted | A green success state links to worker payments or project finances; approval does not send money. |
| Dashboard/check failed | An error message offers retry; normal work links remain accessible and server budget checks still apply. |

The dashboards also flag missing approved attendance, unpaid wages/invoices, negative operational contribution, expiring trials, restricted customer access and failed/in-progress support. Each state has a next-action button. Expand **More next actions** for additional conditions. These indicators use words and next steps as well as colour.

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

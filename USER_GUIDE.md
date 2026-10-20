# Using PLUS POINT

Start at **PLUS POINT → Event operations**. Customer logins open this workspace by default unless an administrator has chosen another starting app. The overview groups everyday work into attendance, workers and work sites, client billing, and worker payments.

The overview starts with a dashboard. Choose your **Company** and use **Refresh figures** for the latest saved records. PLUS POINT shows approved worker-days today, active workers/sites, earned revenue, unpaid wages and the client invoice balance. The work chart switches between 7, 14, 30 and 91 days; the finance chart compares earned revenue, wages, other costs and operational contribution. Financial totals are lifetime figures for projects with PLUS POINT billing terms; the attendance chart counts approved worker-days. Draft attendance is excluded. All existing work links remain under **Work tools**. The overview cards use visual animations only; the workflow illustration does not approve work, issue invoices or send payments. Reduced-motion system preferences show the same information without animation.

**Action inbox**, immediately below the stats, shows budget and workflow warnings with next actions. **Updates** shows unread warnings/errors. **Mark updates read** acknowledges them for your login; unresolved actions stay visible. Updates are recalculated when the dashboard opens or you refresh, with no outgoing email or background push.

**Client company activity** shows the most recently active six clients over 91 days. Open any client for its own calendar on the main form, or your Company for client calendars. Calendars show Monday–Sunday down the left and the actual months/year above the weeks. Green intensity means approved worker-days, not login activity. Two half-days equal one worker-day; empty squares do not prove absence. Active-day count and longest consecutive calendar run are explicit. Hover or keyboard-focus a date for quantities, then select it for worker names, sites and source entries. Arrow keys move around the calendar.

Choose a sidebar section heading or its **overview** link to see its summary and work-list counts before opening a list. **Sidebar Menu → Arrange sections** lets you move whole sections up/down and save the order for your login. Company-specific links retain the same company/project scope as their counts. Charts stay on the main overview; activity calendars also appear on client/company front pages.

The local demo has people such as Ahmed Raza, Hassan Ali, Sara Khan and Bilal Ahmed, and clients Lumen Celebrations, Cedar Events and Orion Exhibitions. Records are labelled **Demo**. Its 70 added synthetic approved work entries and illustrative invoice/partial receipt/wage payment are examples, with no real sale or bank transfer. Stable internal IDs may still contain the original demo label.

**Display currency** converts the overview's money figures together, including earned revenue, wages, client balances, project costs, budgets and project rows. Choose PKR, USD, EUR, GBP, AED, SAR, CAD or AUD; the company's own currency is also available. Worker counts, attendance and calendar quantities stay the same. Refresh figures retains your selected currency during the current app visit.

A converted view shows the actual rate, its UTC update time and the rate source. These are the latest daily indicative rates from ExchangeRate-API, not a fixed 280:1 example or a bank buy/sell quote. Books, invoices, payments, imports and spending approvals remain in their original company currency. If the rate service is unavailable or too old, the overview shows original-currency amounts and **Retry conversion**. It never relabels unchanged amounts as another currency.

High4Tech's dashboard shows registered software customers, trial/access status, invoices and customer receipts this month, outstanding invoices, six months of billed/received figures and customer access needing attention. Financial figures belong to the selected High4Tech company. Trials are not sales; cash receipts and invoice totals are separate. Amounts include posted invoice taxes, receipts are net of refunds, and future-dated postings are excluded from the monthly chart. Existing links remain under **Your tools**. Zero and empty states use actual saved data, without sample revenue.

Choose **Mark attendance**, select the work site and date, then **Review attendance**. This prepares a draft with assigned workers, or reopens the saved register for that site and date. Review the entries before **Submit** approves earnings. Opening attendance never approves it automatically.

The sidebar groups **Daily work**, **Clients and billing**, **Payments and costs** and **Business reports**. Expand **Inventory and transport** for warehouse availability, items, warehouses, vehicles and reservations. **Business setup** contains company, billing items, suppliers and accounts. Staff login management is deferred. Lists use labels such as **Add event site** and **Assign worker**. Native permissions determine the links and actions available to your login.

For help, choose **Help** in the top action bar. Fields with a **?** explain what to enter. The company menu at the bottom of the sidebar opens **Guided company setup**.

## Guided setup

Fresh companies open a saved, company-owned journey automatically: company → client → event/venue → agreement → workers → daily staffing → vehicle → equipment → crew allocation. Each step saves real native records, dims the background and blocks background clicks/keyboard focus. Reload resumes the saved step. Existing businesses with assignments, including the demo, are not forced into onboarding. A voluntarily opened guide can close. Events may explicitly need no transport or no equipment. Completing the guide creates no attendance, wages, invoice or payment.

See [Event operations](EVENT_OPERATIONS.md) for the full guide, exact event-date calendars, multiple venues/phases, crew shortages and native equipment/vehicle reservations. A company account owns the workspace; named employees are workers, not staff software accounts. Payment is simulated; approved local signups receive separate empty company workspaces and choose their own passwords.

## Import employees and existing finances

Choose **Import** beside the top **Add** action on the relevant employee/finance list, or **Import workers from a template** in guided setup. Select your company and import type, then **Download template**. **Download reference IDs** provides the existing projects, assignments, billing terms, employees, suppliers, customers, service items, cash/bank ledgers and unpaid client invoices. It also includes warehouses, stock items, vehicles and event sites. The reference download is capped at 1,000 records per supporting type; use native lists to find additional IDs.

Clients, Event sites, Event plans/projects, Vehicles, Inventory items, Warehouses and Warehouse balances use the same template/review flow; see [event templates](EVENT_OPERATIONS.md#import-templates). Warehouse balances are absolute native stock/value counts, not cash received.

You can also choose **Import** beside the top **Add** button on Workers, Wages earned, Fixed milestones, Project expenses, Client invoices, Receipts and payments, or Worker payments. This remains available on populated lists and after refresh. The window selects the corresponding import type and shows **Download template** above the instructions and file chooser. Expand **How to fill this template** when needed. You can add more rows later or update employee profiles using their existing IDs.

Fill the template in Excel or Google Sheets. Keep its headers and use one worksheet, stable source IDs, YYYY-MM-DD dates and company-currency amounts without currency symbols or thousands separators. Format IDs and phone numbers as text. Replace formulas with values. From Google Sheets choose **File → Download → CSV** or **Microsoft Excel**. Upload UTF-8 CSV or XLSX, at most 200 rows and 2 MB per file. This is an uploaded snapshot, not a live Google Sheets connection.

| Template | What the system saves |
| --- | --- |
| Employees | Native employee profiles. A new stable `external_id` with blank `employee` or a new worker’s name creates a profile. An existing Employee ID updates that company’s profile. A unique existing full-name match checks date of birth before updating; ambiguous names require an ID. Reusing an imported ID updates the same profile; the full template includes middle name, your employee number, personal email, current/permanent addresses, emergency contact and passport details. Blank optional columns clear those fields; old templates preserve columns they omit. No user account is created. |
| Approved daily work | Dated work under existing assignments; units 1, 0.5 or 0. Wages and daily client earnings use the agreed historical assignment rates. |
| Fixed-price milestones | Approved milestone earnings under active Fixed billing terms, within the fixed contract cap. |
| Project expenses | Posted, unpaid supplier invoices for net project service expenses. These update project costs and spending budgets. |
| Client invoices | Posted client invoices and receivables. Link approved work/milestones using both `source_type` and `source_name` to reserve their earnings against rebilling. Blank source fields record a legacy invoice only; they do not invent operational earned revenue. |
| Client receipts | Posted historical money received, allocated to a submitted client invoice. Partial receipts reduce its outstanding balance. |
| Worker payments | Posted historical employee payments and wage settlements, limited to approved outstanding wages. |

Import employees and assignments before their daily work, then import work/milestones before related invoices or worker payments, then client receipts. A reference such as `import:invoice-001` can identify an invoice from an earlier invoice import; the same syntax works for invoice work/milestone sources and employee references in worker payments. Imports never contact a bank or send money.

**Review file** shows row actions, amounts, errors and projected spending. Nothing is saved at this point. Fix invalid rows or download the error list; tick the review box beside the Import button after reviewing the valid preview. The button then enables: choose **Import employees** or **Import and post records**. The box stays visible while the preview scrolls; file and posting errors appear inside this same import window. Final native posting and permission checks run again. If any row fails, the entire file is rolled back, with a row-specific reason. A preview expires after 20 minutes and belongs to the signed-in user.

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
## Local ownership, signup and document capabilities

The custom PLUS POINT source and setup files live in this Git checkout. Frappe, ERPNext and HRMS are installed locally inside the persistent Docker bench volume and retain their own open-source licenses. MariaDB databases live in the separate local database volume; uploaded files live in the bench volume. There is no externally hosted application database in this setup. Customer and High4Tech sites use separate databases on the same local MariaDB service. Currency conversion requests public exchange rates externally; company figures are not sent to that provider.

Git contains code and setup definitions, not live database contents, uploads, passwords or site configuration. A Git push does not back up those files or update an already deployed server automatically. On another computer/server, restore native site backups and configuration into the supported environment, then install the pinned dependencies and migrate. Normal code updates may require migration and cache refresh; keep upstream version pins deliberate. See LOCAL_RUNBOOK.md for backup and update procedures.

Customer login: http://demo.localhost:8000/login . High4Tech admin: http://platform.localhost:8000/login?redirect-to=%2Fdesk%2Fhigh4tech . The explicitly configured sample logins use example@email.com with user123 for the customer and admin123 for High4Tech. These are separate site accounts, not a shared database login.

**Local trial signup:** choose See plans & sign up on either login page, or open http://platform.localhost:8000/plans . Customer-site /plans redirects to that central High4Tech page. Choose a published fixed-rate plan, enter contact/business/email and an optional company login ID, continue to demo payment and choose Simulate payment & request approval. No card, bank detail, real payment or financial posting is collected. Your email is your login. Password creation happens privately after approval. Reloading the same browser tab resumes the request through a private session token; do not share browser storage containing that token.

High4Tech → Signup approvals lists the requests. After the simulated payment is submitted, choose **Approve & create workspace** or **Reject signup**. Approval queues the trusted local worker, which creates a separate site/database, a native owner login and a 30-day trial. Nothing is copied from the demo company. The owner sees **Set your password** and **Open my company workspace** on the signup page when ready. High4Tech can also open **Company login** on the approved request. Existing approved requests use **Create company workspace** once. Failures show **Retry workspace setup**, retaining existing data.

The owner chooses a password on Frappe’s native setup page. The registered email always works; a requested company login ID is an optional alternative. Initial passwords are random and never displayed. Private one-time links expire within 20 minutes (or sooner under native settings); use **Refresh password setup link** before first sign-in if needed. Once used, the link cannot reset the password again. High4Tech’s existing audited account support handles later recovery. No email is sent by this local flow. Keep the signup browser tab/private session token, or use the approved request in High4Tech to find the correct company address.

First entry starts company → client → event → agreement → crew → staffing → transport → equipment → allocation onboarding, with other tools dimmed and disabled until the guided steps are complete. Simulated trial subscriptions cannot generate software invoices. Real payments, email delivery/verification, domain/TLS hosting and production provisioning acceptance remain separate launch work. Native website-user self-registration stays disabled because it does not create an isolated business account.

High4Tech → Pricing plans owns the displayed price. A plan must use Fixed Rate, have a positive cost and enable Show on demo signup pricing. Public plan summary is shown on the pricing page. Existing request quotes retain their signup price if the plan changes later. Only the labelled existing local sample plan was published initially.

**Invoices and documents:** Clients and billing → Client billing → open active terms → Prepare client invoice creates a native draft invoice for approved, unbilled daily work or fixed milestones, optionally within dates. Review and submit it in Client invoices; receipts are separate. Record forms support attachments, permitted edits and activity/version history. Submitted accounting documents follow native cancellation/amendment rules. A complete client signing link, signature capture/audit trail and signed-document notification workflow is not implemented; native contract signed/name/date fields alone are not that workflow. There is no collaborative Word/PDF document editor.

**Arrange the sidebar:** drag a section header using its dotted grip to move the whole section and its links. The order saves automatically for your login and survives reload. Collapse sections first if you want a shorter drag distance. A failed save restores the previous order and explains the retry. Keyboard/mobile alternatives remain under Sidebar Menu → Arrange sections → up/down → Save my order. Individual links cannot be moved out of their section.

## Inline onboarding and one business workspace

Open **Onboarding** in the sidebar. Each screen saves one step in the dashboard; **Skip onboarding** remains available and keeps saved progress so you can resume later. Other sidebar tools unlock after skipping or completing setup. The paid account has one own-business profile. Add organizations that hire you under **Clients**, and jobs under **Event projects**; these do not create more subscribed workspaces.

Selecting the business country sets its currency automatically, including SAR for Saudi Arabia. You can correct the country at any time. Accounting currency is fixed once agreements, stock or accounting entries exist, so country corrections then preserve the original monetary amounts and currency; display-currency conversion on Overview is separate. A new client needs a contact person, email or phone and billing address. Existing-client selection shows saved contact/address details and offers Edit this client’s details, without a nested Create form. Click a completed step anywhere in its sidebar row to review/edit saved details. Saved agreements load their scope and billing values for editing in place; financial terms remain protected after crew assignments or earned work. Country and record pickers open on click, select the current text for replacement and filter as you type. Venues have country/region/city/street/postal fields and an optional Choose from map pin. Map tiles need Internet; manual address entry works without them.

Choose transport purpose before entering capacity. Crew vehicles ask for crew seats/passengers; inventory vehicles ask for load capacity/load. New equipment asks for the warehouse count and event quantity directly. Estimated unit value is optional; 0 records quantity without a value, with explicit confirmation. Counts still must cover reservations. Failed saves show an inline message and keep the entered fields.

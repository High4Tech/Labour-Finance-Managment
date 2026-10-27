# Using PLUS POINT

Current creation UI: [Context-aware three-stage workflows and shared components](docs/CONTEXT_AWARE_UX_2026-10-27.md). This supersedes earlier five/four-step layout descriptions; the underlying business architecture is retained.

Start at **PLUS POINT → Event operations**. Customer logins open this workspace by default unless an administrator has chosen another starting app. The overview groups everyday work into attendance, workers and work sites, client billing, and worker payments.

The overview starts with a dashboard. Choose your **Company** and use **Refresh figures** for the latest saved records. PLUS POINT shows approved worker-days today, active workers/sites, earned revenue, unpaid wages and the client invoice balance. The work chart switches between 7, 14, 30 and 91 days; the finance chart compares earned revenue, wages, other costs and operational contribution. Financial totals are lifetime figures for projects with PLUS POINT billing terms; the attendance chart counts approved worker-days. Draft attendance is excluded. All existing work links remain under **Work tools**. The overview cards use visual animations only; the workflow illustration does not approve work, issue invoices or send payments. Reduced-motion system preferences show the same information without animation.

**Action inbox**, immediately below the stats, shows budget and workflow warnings with next actions. **Updates** shows unread warnings/errors. **Mark updates read** acknowledges them for your login; unresolved actions stay visible. Updates are recalculated when the dashboard opens or you refresh, with no outgoing email or background push.

**Client company activity** shows the most recently active six clients over 91 days. Open any client for its own calendar on the main form, or your Company for client calendars. Calendars show Monday–Sunday down the left and the actual months/year above the weeks. Green intensity means approved worker-days, not login activity. Two half-days equal one worker-day; empty squares do not prove absence. Active-day count and longest consecutive calendar run are explicit. Hover or keyboard-focus a date for quantities, then select it for worker names, sites and source entries. Arrow keys move around the calendar.

Choose a sidebar section heading or its **overview** link to see its summary and work-list counts before opening a list. **Sidebar Menu → Arrange sections** lets you move whole sections up/down and save the order for your login. Company-specific links retain the same company/project scope as their counts. Charts stay on the main overview; activity calendars also appear on client/company front pages.

The local demo has people such as Ahmed Raza, Hassan Ali, Sara Khan and Bilal Ahmed, and clients Lumen Celebrations, Cedar Events and Orion Exhibitions. Records are labelled **Demo**. Its 70 added synthetic approved work entries and illustrative invoice/partial receipt/wage payment are examples, with no real sale or bank transfer. Stable internal IDs may still contain the original demo label.

**Display currency** converts the overview's money figures together, including earned revenue, wages, client balances, project costs, budgets and project rows. Choose PKR, USD, EUR, GBP, AED, SAR, CAD or AUD; the company's own currency is also available. Worker counts, attendance and calendar quantities stay the same. Refresh figures retains your selected currency during the current app visit.

A converted view shows the actual rate, its UTC update time and the rate source. These are the latest daily indicative rates from ExchangeRate-API, not a fixed 280:1 example or a bank buy/sell quote. Changing the display currency does not rewrite records. If the rate service is unavailable or too old, the overview shows original-currency amounts and **Retry conversion**. It never relabels unchanged amounts as another currency.

In onboarding, country suggests an editable **Default client invoice currency** (Saudi Arabia → SAR, UAE → AED). Choose another currency whenever needed. After financial activity or agreements exist, this saves the default for new invoices while preserving the original accounting currency. Each client has its own editable invoice currency, so a UAE client can pay in USD. On **Billing terms → Prepare client invoice**, review or change the currency and rate before creating the draft. Rates mean accounting currency per one invoice unit; a current published rate is suggested or you can enter an agreed rate. Approved source amounts remain in company currency and invoice amounts are actually converted. Native Payment Entries record receipts, and project totals convert them back to company currency. Existing invoices, books, import amounts and spending approvals retain their saved currency.

High4Tech's dashboard shows registered software customers, trial/access status, invoices and customer receipts this month, outstanding invoices, six months of billed/received figures and customer access needing attention. Financial figures belong to the selected High4Tech company. Trials are not sales; cash receipts and invoice totals are separate. Amounts include posted invoice taxes, receipts are net of refunds, and future-dated postings are excluded from the monthly chart. Existing links remain under **Your tools**. Zero and empty states use actual saved data, without sample revenue.

Choose **Mark attendance** or **Attendance > Create register**, select the **Event**, **Event site** and **Work date**, then **Open register**. The roster uses saved allocations and shows the planned headcount for that site's work day. Today's drafts are created automatically when crew are allocated to an active event, when the dashboard/attendance list opens, and by the hourly scheduler while the server is running. Opening the same site/date reopens its existing register.

Each worker starts **Not marked**. Choose **Present** (full wage), **Absent** (zero) or **Half day** (50%). There is no exit attendance. **Save draft** preserves marks without earnings; **Approve attendance** requires every allocated worker to be marked, checks the spending budget, and updates wages and daily client earnings once. Future-day approval is blocked. **Refresh crew** picks up allocation changes while preserving saved marks. Approved attendance remains locked.

Click a worker in **Workers** or in a register to open their overview: identity and designation, present/half/absent days, paid-day equivalents, earned/paid/outstanding wages, current event allocations and recent attendance. The 3-month/year calendar distinguishes absence, pending approval, unmarked and unscheduled days. **Edit profile** opens the underlying profile fields; **View full statement** opens their detailed history.

The sidebar groups **Daily work**, **Clients and billing**, **Payments and costs** and **Business reports**. Expand **Inventory and transport** for warehouse availability, items, warehouses, vehicles and reservations. **Business setup** contains company, billing items, suppliers and accounts. Staff login management is deferred. Lists use labels such as **Add event site** and **Assign worker**. Native permissions determine the links and actions available to your login.

For help, choose **Help** in the top action bar. Fields with a **?** explain what to enter. The company menu at the bottom of the sidebar opens **Guided company setup**.

## Agreement-led client and event management

Clients and billing has four links: **Overview**, **Client agreements**, **Event plans**, and **Billing and finances**. Daily work contains Attendance and Workers. Event sites and allocations belong inside Event plans. The subscribed business is selected automatically; there is no extra company tab or workspace selector.

In **Client agreements**, choose an existing client or enter their complete contact/address profile in the same screen. Define the scope, dates, daily/fixed billing, venues and required worker categories (for example manager or electrician), daily headcounts and category rates. Add categories inline when needed. The agreement retains its native contract and document attachments. Fixed agreements include payment milestones, which can also be added later. Choose a service item and enable automatic milestone invoice drafts if required.

In **Event plans**, select the agreement first. Client, venues, dates, categories and rates are copied from it. Choose workers for a category using the checklist and removable tags, or **Auto-select available crew**. Automatic selection respects the category, employment dates and overlapping allocations; shortages stop the whole allocation. Actual crew above the agreement is labelled as extra. Event plans contain project notes, a separate spending budget, site coverage, dated worker allocations, timeline, vehicles and equipment. Existing imported/untyped plans keep their original data and general crew behavior.

Use **Move or unassign** beside a worker allocation to change their site/event from today or a future date. Old attendance and wage snapshots stay with the original event; the new allocation uses destination rates. Recorded work on/after the proposed date blocks the move. Clear unapproved marks before moving an unposted roster. Worker profiles and lists show Assigned, Scheduled or Available status. Profile event cards link to the relevant event. Photos are optional: Add/Update/Remove photo in the profile. Photos are never spreadsheet requirements. The optional designation column in the employee template supplies the category for matching; new categories are listed in the review and created during the confirmed import. Earlier employee templates remain accepted and preserve categories they do not contain.

**Billing and finances** brings agreement milestones, invoices, earned revenue, wages, costs, contribution, client balance and cash together. Approving a milestone creates a native invoice **draft** when automatic invoicing is enabled. It does not submit an invoice or collect payment. Review descriptions, notes, due dates and extra-charge rates inline; approved source amounts remain protected. Extra invoices are supported separately. Submit only after review. Download PDF creates the actual invoice document. Email invoice requires a configured outgoing email account, an explicit recipient/message and the Send invoice email action; the result is queued delivery, not an unverified sent claim. No outgoing email account is connected in the current local setup.

Comments and activity sit in a sticky right-hand panel on desktop, below existing sidebar details where applicable. They move below the record on small screens. Native record comments and history remain intact after saving, refreshing and uploading a profile photo.

## Guided setup

Fresh companies open a saved, company-owned journey automatically: company → client → event/venue → agreement → workers → daily staffing → vehicle → equipment → crew allocation. Each step saves real native records, dims the background and blocks background clicks/keyboard focus. Reload resumes the saved step. Existing businesses with assignments, including the demo, are not forced into onboarding. A voluntarily opened guide can close. Events may explicitly need no transport or no equipment. Completing the guide creates no approved attendance, wages, invoice or payment; allocating crew for today can prepare an unmarked attendance draft.

See [Event operations](EVENT_OPERATIONS.md) for the full guide, exact event-date calendars, multiple venues/phases, crew shortages and native equipment/vehicle reservations. A company account owns the workspace; named employees are workers, not staff software accounts. Payment is simulated; approved local signups receive separate empty company workspaces and choose their own passwords.

## Faster forms and complete choices

Record dropdowns load every available page, sort names A–Z and show the total choices. Type to filter immediately, or scroll the full list. Normal company, date, active-record and permission filters still apply. Currency choices include installed currencies that have not yet been enabled; saving a company/client currency enables it. The event timeline selector also lists all matching event plans. Dropdown arrows are centered on desktop and mobile.

Selecting an existing event in worker assignment or reservation forms fills its saved dates, single active site, single active agreement and existing plan rates. Multiple valid sites/agreements stay selectable; prices are not guessed for a new event. Values remain editable, and details typed while a saved-context request is loading are preserved. A new event opened from a client profile carries that client forward. Onboarding offers **Use the client’s saved address for this venue** when that is the correct event address.

Number fields accept numeric input; whole-number fields reject decimal entries. Personal names accept international letters, spaces, apostrophes, hyphens and periods. Phone fields accept digits with normal international formatting. Registration/passport/worker codes allow letters, numbers and their normal separators. Email and date fields retain native validation. Business names, addresses and agreement text retain useful punctuation. Worker import previews apply the same name/phone rules before saving.

## Delete unused records

Open a saved record and choose **Delete**, or tick records on a list and choose **Delete selected**. Review the records, then confirm **Delete** or choose **Cancel**. Up to 50 selected records are removed together; if one fails, the entire batch is kept. Errors explain linked records inside the same dialog. Native permissions still apply.

Draft work, draft attendance/milestones and unused records can be deleted. Approved work/milestones, posted financial records and linked history stay protected. Release unused event crew before removing an allocated plan. Client deletion uses native cleanup: its unshared contacts/addresses are removed, while shared profiles remain. These actions do not erase earned wages or financial history.

## Appearance and buttons

Choose **Appearance** at the bottom of the sidebar for **Light**, **Dark** or **System**. Your choice is saved for your login; System follows your device's appearance. Buttons share the same sizing across dashboards, lists, forms and dialogs, with larger touch targets on mobile.

## Import employees and existing finances

Choose **Import** beside the top **Add** action on the relevant employee/finance list, or **Import workers from a template** in guided setup. Select your company and import type, then **Download template**. **Download reference IDs** provides all visible existing projects, assignments, billing terms, employees, suppliers, customers, service items, cash/bank ledgers and unpaid client invoices. It also includes warehouses, stock items, vehicles, event sites and approved unbilled work/milestone sources. Related profile fields accept exact, unique display names as well as IDs. Duplicate names need an ID. Missing dependencies have row-specific instructions rather than being silently created as financial history.

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
4. **Record attendance.** Choose **Mark attendance**, select the event, site and date, then **Open register**. Mark each assigned worker Present, Absent or Half day. Save a draft for review; Approve attendance creates approved worker earnings. A worker can total at most one full day across sites on a date.
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

## Choosing several workers

In onboarding, tick available workers in the crew list. Your choices appear as tags; use each tag’s remove button to deselect. Search names, IDs or phone numbers. Import workers brings in a sheet and refreshes availability; Add worker creates another profile inside the same screen. Availability uses the inclusive event dates, active status and joining/leaving dates, and excludes any overlapping site/project allocation.

The same selection appears under event-plan Choose crew and the normal Assign workers action on Worker assignments. Assign workers is also available from worker lists/profiles and event sites. The event planner uses only the chosen pool and shows any shortage; it never fills the gap using unchecked workers. Daily staffing controls how many selected workers each phase needs. Onboarding starts with your selection count for its first venue. Saving a manual multi-worker assignment creates all selected allocations together or saves none. Availability is checked again when saving. These actions create allocations and may prepare today's unmarked register. They do not approve attendance or create earned wages.


## Agreement pricing, sites and client signatures

Open **Client agreements** for the searchable list, then open or create an agreement. Follow Client details, Agreement details, Pricing and milestones, Sites and crew, then Send and sign. Use **Next** after completing each step and **Previous** to review without losing changes. The header has **Save draft** and **Import agreement**; **Save agreement** appears once the required details are complete. Partial forms, including an unfinished client, can be saved without creating client or accounting records. Changes autosave after a short pause and when you leave the tab. Reopen them from **Drafts**. **Save agreement** creates the completed agreement and its event draft. Names remain the main choices; the smaller Tracking ID is a stable reference for search and support.

Choose the agreement currency under **Pricing and milestones**. Daily client rates, fixed prices and milestones use that currency. Worker wages are entered in the event plan, not the agreement. Accounting conversion is handled internally. New agreements can override the client's suggested currency. Once allocations or financial activity exist, saved currency/rate changes are protected; individual invoices can still have their own reviewed currency/rate.

Under **Sites and crew**, add a site, then its crew categories and headcounts. Daily agreements require a client rate; Fixed agreements have no per-worker price column. For a returning client, select a previous site and choose whether to copy its crew and vehicle requirements. The copy uses the current agreement dates, even if the previous plan was longer. It does not copy old dates, worker pay, assigned workers or booked vehicles. Edit the copied requirements before saving. Optional vehicle requirements stay with this agreement. Assign actual vehicles and warehouse equipment only in its event.

Daily agreements support daily, weekly, monthly or custom billing milestones for non-overlapping approved attendance periods. A checkpoint does not earn extra revenue; it groups unbilled work into an invoice after the period ends. Fixed agreements can have payment milestones while being created. After saving, **Edit / approve** records milestone acceptance; automatic invoicing creates a draft if enabled. Review and submit the draft in Billing and finances. Extra invoices use the agreement currency and rate. PDF downloads are prepared within the browser.

Under **Send and sign**, create a private link and copy it or email it. Links expire after seven days. Creating another link or changing the agreement/milestones revokes pending links. Clients see a frozen version of scope, sites, headcounts, client pricing and milestones. They enter their name/email, confirm acceptance and may draw a signature. The signed snapshot and signature stay in the signing history, and the company receives an in-app notification. This records client acceptance; it is not an external identity verification service. Email delivery requires an outgoing Email Account; copying the link remains available.

The top-bar currency converts company-wide totals and the unfiltered financial report, and is saved for the user. Opening a specific agreement, event or project report keeps its own currency. Conversion does not rewrite transactions. Worker lists include **Open profile** and **Edit contact**; other lists have actions suited to their records.


## Focused worker and staffing forms

Worker profiles open with an operational overview. **Edit profile** uses three tabs: Overview, Work details and Contact. New workers use the same fields. The header and crew selections show the saved photo or the first two name initials. Photos remain optional and are added after saving a profile; import templates do not require them. Work details offers event departments, relevant worker categories and active management/senior staff for Reports to.

Action forms for site crew, categories, worker selection/moves, milestones and invoices open in dismissible dialogs. Starting another action replaces the previous action dialog. Cancel closes the action without saving it. Notifications include a close button; information icons open above tables and tab bars.

The agreement currency is selected under **Pricing and milestones**, not in the client details tab. New agreements suggest the business invoice preference, and pricing controls use the chosen currency. Used agreements retain their historical rate/currency; invoices can use a separately reviewed payment currency.

Agreed crew counts are compared with all active company workers, including people already booked elsewhere. The staffing dialog also shows how many are free for the selected dates. If demand exceeds the existing crew, the crew-count field shows an inline error. Choose **Use existing crew maximum** to reduce it or **Plan additional hiring** to confirm the extra hires. Availability is shown above the fields. This saves a staffing commitment, not fictitious worker profiles or duplicate assignments. Concurrent site/category demand is counted once per date rather than adding disjoint phases together.

Lists no longer receive automatic status or project filters. Filters chosen explicitly by the user remain native and editable. Retired app-added company/active-project filters are removed once when this update is installed.


After creating an agreement, choose **Enter event details** or **Send to client for signature** from the completion popup. Event details can stay as a draft, create the event now, or schedule creation for a future date and time in the displayed site timezone. Scheduled drafts can be reviewed, cancelled back to Draft, or created immediately. Failed creation stays visible in Drafts for correction. An event uses dates covered by the agreement and receives its crew requirements without assigning workers automatically. Saved events use Event information, Venues and crew, Transport and equipment, and Event timeline. **Save event** keeps notes and budget; crew and resource actions save immediately. Reloading Desk returns to Home; saved drafts remain available. Customer lists omit the redundant **List View** selector and retain search, selection and sorting.


Crew requirement rows default to **Event crew**. The availability banner shows workers in the selected category who can cover the selected dates; changing the category or dates refreshes the number. Workers booked to the same agreement remain available to its own event, while external bookings, leave and employment dates still affect availability. If that category is short, **Add crew** opens a worker form inside the same dialog with the category preselected. Save the worker to refresh the count and continue the requirement. Creating a worker does not assign them to an event.


## Current navigation, drafts and client portal — October 27

Attendance is directly below Overview. Expand Clients and work, Workforce and resources, Finance, or Reports and analytics to open their lists. Click the section heading for its summary; click its arrow to expand/collapse. There is no duplicate overview child link.

Unfinished events show Draft in Jobs and events. Open one to continue editing and choose Save event when its requirements are ready. Upcoming means planning is finished and the event start date has not arrived. You can save draft attendance marks, but finish the event before approving earnings.

On a created agreement or event, choose Copy client link. Share that private online link with the client so they can read/sign the agreement and see confirmed event progress. It is separate from the PDF and expires after seven days. Event links show that occurrence; agreement links show associated confirmed events. Refresh progress reads current scheduling information. It does not expose worker pay, loans, budgets or internal notes.

For equipment, select the item and quantity, then a warehouse with enough stock for the event dates. Available capacity returns automatically after the reserved period; this does not confirm a physical return or add consumed stock back. See [the complete release map](docs/CONSOLIDATED_ARCHITECTURE_2026-10-27.md).

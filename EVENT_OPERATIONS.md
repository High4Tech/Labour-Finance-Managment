# Event organizer workflow

PLUS POINT is the customer company's event operations workspace. High4Tech manages software customers, pricing, approvals, account support and software finances on its separate platform site. Payment remains **simulated**. Approval now creates a separate local company site/database and owner login. A private native password setup link opens the empty workspace and its company onboarding; no existing demo workers or projects are copied. No charge or email is sent.

## Start a company

A fresh company opens the guided journey automatically. Its saved progress belongs to the Company, and resumes after a reload. The background is dimmed and unavailable to pointer and keyboard interaction while the guide is open. Existing businesses with assignments, including the demo, are not forced through onboarding. Choose the company menu at the bottom of the sidebar → **Guided company setup** to reopen it deliberately.

1. Choose or create your event company and its accounting currency.
2. Add or choose the client organization hiring you.
3. Enter the event project, setup through pack-down dates and first venue.
4. Record the client agreement and Daily or Fixed billing terms.
5. Add or choose a worker; **Import workers from a template** can bring in the rest of the crew.
6. Set daily wage/client rates and venue phases. Each row has a venue, phase, inclusive dates and required workers per day. Add a new venue name when needed. The same venue's phases cannot overlap.
7. Choose/create a vehicle and reserve it for Crew or Inventory. An event with no transport needs can state that explicitly.
8. Choose/create equipment and its warehouse, optionally confirm a real counted starting balance, and reserve the event quantity. An event without warehouse equipment can state that explicitly.
9. Review crew availability, address shortages and allocate workers. Then open the saved plan.

The company menu displays the company account. Workers such as Ahmed Raza are crew records, not additional software accounts. Native authentication still uses a User internally. Staff account management is outside the customer interface for this MVP. Required onboarding is a UI focus mode; document permissions remain server enforced. Established companies may close a voluntarily opened guide.

## Plan subsequent events

Use **Plan an event** in Upcoming events or Event plans. Four screens collect the client/event dates, agreement, venue phases and final review. Saving creates the native Project, Contract, PP Contract Terms, PP Sites and PP Event Plan together; a failed save rolls them back together.

Open the event plan → **Preview crew plan**. Allocation uses active company workers whose employment and existing assignment dates permit the complete phase. It is deterministic date matching, with no skill or travel optimization. Existing complete-phase assignments at the same event site count toward its requirement. Other assignments remain commitments; partial-day or partial-phase optimization remains manual. Resolve shortages by adding/importing crew or revising the requirements. Allocation creates dated worker assignments, never attendance, earned wages, invoices or payments.

**Release unused crew to edit** removes only this plan's generated assignments. Any referenced draft/register/approved attendance prevents release. Existing financial history and used assignment rates cannot be rewritten.

## Read event calendars

The saved plan shows only its inclusive date range, with date range/duration, month/year and Monday–Sunday labels. Each venue has its own grid. A cell's number is the required headcount; amber means assigned crew is short, green means covered. Select a date to compare required/assigned workers with approved actual worker-days. Future dates cannot open attendance through the calendar. Long plans scroll inside their panel on narrow screens.

Client, Project and Company forms offer a saved-event selector and the same timeline. The overview also retains its historical client activity charts; these describe approved work within the chosen history range, distinct from future staffing plans.

## Inventory and transport

**Inventory and transport → Warehouse availability** shows native counted stock, peak overlapping reservations and available quantity for selected dates. Every item stays in its own unit; quantities of unlike items are not combined. A catalog entry alone has no on-hand stock. Add items and warehouses, then import counted balances with valuation rates to establish stock.

An equipment reservation reduces planning availability, without moving or consuming stock. Non-overlapping reservations reuse equipment. Requests exceeding available stock stop with an actionable error. Cancelling a booking releases its reservation. Count submissions and outgoing Stock Entries cannot reduce available stock below future reservations. Other native stock document types and stock cancellation paths need separate production coverage; this is not a warehouse-dispatch workflow.

**Vehicles** store registration/ID, make/model, crew seats excluding the driver, inventory capacity and unit (units/kg/m³). A dated booking assigns one vehicle to one event site, for **Crew OR Inventory**. Seat/load limits, company ownership and overlapping inclusive dates are checked on save. Future bookings prevent unsafe capacity reductions or disabling a booked vehicle. There is intentionally no individual item-to-vehicle manifest. Reserve crew and cargo vehicles separately.

## Import templates

**Import** stays beside Add on populated lists. After opening it, choose **Download template**, optionally download reference IDs, fill it in Excel or Google Sheets, upload CSV/XLSX, review errors and confirm. Google Sheets works through file export, without live synchronization.

| List / template | Result |
| --- | --- |
| Clients | Create/update named client organizations or individuals. |
| Workers | Create/update Employee profiles, without software logins. |
| Event sites | Create/update venues under a company event project. |
| Vehicles | Create/update car/van/truck profiles and capacities. |
| Inventory items | Create/update stock item catalog entries and native stock units. |
| Warehouses | Create named storage locations in the selected company. |
| Warehouse balances | Set an absolute counted quantity and value per unit via a submitted native Stock Reconciliation. This posts stock and its book value; it is not cash received. |
| Event plans / Event projects | Create a one-venue plan with dates, daily worker requirements and an agreement. Expand phases/venues on the saved plan. |

Existing finance templates remain available. Use stable external IDs; repeated unchanged rows skip. Profile templates can update the same target; posted financial/stock/event rows require a new external ID for a changed record. A preview is read-only, and all checks rerun on apply. A failed batch saves no rows. Limits remain 200 rows / 2 MB, formulas rejected. Native permissions, accounting and spending limits still apply.

## Daily work and billing

On an actual work date, **Mark attendance**, review units and submit the register to approve wages. Daily client billing uses approved worker-days at the separate client rate. Fixed-price client earnings use approved milestones, independently of daily wages. Billing terms → **Prepare client invoice** creates a native invoice for review; submitting posts it. Native receipts, worker payments and project spending budgets retain their existing behavior.

Help sits in the top action bar. The overview's inbox and Updates reflect saved business conditions on open/refresh. They are not outgoing email, live push or online signature notifications. Contracts and attachments are native records; a complete online signing workflow is not part of this increment.

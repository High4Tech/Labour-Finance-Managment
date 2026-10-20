# Event organizer workflow

PLUS POINT is the customer company's event operations workspace. High4Tech manages software customers, pricing, approvals, account support and software finances on its separate platform site. Payment remains **simulated**. Approval now creates a separate local company site/database and owner login. A private native password setup link opens the empty workspace and its company onboarding; no existing demo workers or projects are copied. No charge or email is sent.

## Start a company

A fresh business opens **Onboarding** inside the dashboard, with a permanent sidebar entry. It is a page, not a popup. A sticky **Skip onboarding** action is available at every unfinished step; skipping unlocks the other tools and keeps saved steps. Resume from the sidebar, including after a reload. Saved progress belongs to the business; a native single settings record also retains a skip made before the business profile exists. Other sidebar links are dimmed and unavailable during active onboarding. Established businesses are not forced through it.

1. Enter your business name and country once. Country suggests an editable **Default client invoice currency**, including Saudi Arabia → SAR. You can select USD instead. For an unused business this also sets the accounting currency and its posting accounts; after agreements, stock or transactions exist, only the future invoice default changes. Existing accounting history stays in its original currency. Each client also has an editable invoice currency: UAE suggests AED, but a USD override is saved and reused. Event venues can be in other countries.
2. Add a client with a contact person, email or phone, and structured billing address. Or select an existing client and review its saved contact/address; the selector does not offer a nested Create form.
3. Enter the event project and setup through pack-down dates. The first venue has separate country, region, city, street and postal fields, with an optional Choose from map pin.
4. Record the client agreement and Daily or Fixed billing terms.
5. Tick as many available workers as needed. Selected workers appear as removable tags. Search by name, worker ID or phone; Import workers refreshes the list and Add worker creates a profile inline. Workers booked for any overlapping project/site or outside their employment dates are excluded. No staff login is created.
6. Set daily wage/client rates and venue phases. Each row has a venue, phase, inclusive dates and required workers per day. Add a new venue name when needed. The same venue's phases cannot overlap.
7. Choose Crew or Inventory first. Crew asks only for passenger seats and event passengers, excluding the driver. Inventory asks for load capacity, units and event load. Unused crew/cargo fields are hidden. An event without transport can state that explicitly.
8. Choose/create equipment and its warehouse. For a new item, enter the total quantity you own and the quantity needed for this event, then confirm the count. Unit value is optional: 0 explicitly records quantity without assigning a stock value. One save creates the item, posts its starting stock and reserves the event quantity. Existing items use their recorded stock, with an explicit opt-in to replace it with an actual count. An event without warehouse equipment can state that explicitly.
9. Review crew availability, address shortages and allocate workers. Then open the saved plan.

The company menu displays the company account. Workers such as Ahmed Raza are crew records, not additional software accounts. Native authentication still uses a User internally. Staff account management is outside the customer interface for this MVP. Each subscription has one business profile and workspace. Clients are native Customer records inside it, not additional Company profiles or paid workspaces. Extra Company creation is blocked on customer sites. Older spare profiles are retained in the database but excluded from the active company selector/scope; records are not merged or deleted. The dashboard no longer asks customers to switch companies. Required onboarding is a UI focus mode; document permissions remain server enforced.

## Plan subsequent events

Use **Plan an event** in Upcoming events or Event plans. Four screens collect the client/event dates, agreement, venue phases and final review. Saving creates the native Project, Contract, PP Contract Terms, PP Sites and PP Event Plan together; a failed save rolls them back together.

Open the event plan → **Choose crew**. Use the same checklist and removable tags as onboarding. Allocation uses only your selected active company workers, free for the complete event dates. The preview shows which selected workers cover each required phase; extra selections do not increase staffing requirements. It is deterministic date matching, with no skill or travel optimization. Older plans without a saved selection keep their existing API planning behavior; opening Choose crew asks for an explicit selection. Existing assignments remain intact. Other assignments remain commitments; partial-day or partial-phase optimization remains manual. Resolve shortages by adding/importing crew or revising the requirements. Allocation creates dated worker assignments, never attendance, earned wages, invoices or payments.

**Release unused crew to edit** removes only this plan's generated assignments. Any referenced draft/register/approved attendance prevents release. Existing financial history and used assignment rates cannot be rewritten.

## Read event calendars

The saved plan shows only its inclusive date range, with date range/duration, month/year and Monday–Sunday labels. Each venue has its own grid. A cell's number is the required headcount; amber means assigned crew is short, green means covered. Select a date to compare required/assigned workers with approved actual worker-days. Future dates cannot open attendance through the calendar. Long plans scroll inside their panel on narrow screens.

Client, Project and Company forms offer a saved-event selector and the same timeline. The overview also retains its historical client activity charts; these describe approved work within the chosen history range, distinct from future staffing plans.

## Inventory and transport

**Inventory and transport → Warehouse availability** shows native counted stock, peak overlapping reservations and available quantity for selected dates. Every item stays in its own unit; quantities of unlike items are not combined. A catalog entry alone has no on-hand stock. New items added inside onboarding include starting quantity and valuation directly; missing or short counts stop before any records are created, with inline guidance beside the event quantity. Outside onboarding, add items and warehouses, then import counted balances with valuation rates to establish stock. Use Nos for individual pieces, or the actual unit you count; the unit is never silently changed.

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

On an actual work date, **Mark attendance**, review units and submit the register to approve wages. Daily client billing uses approved worker-days at the separate client rate. Fixed-price client earnings use approved milestones, independently of daily wages. Billing terms → **Prepare client invoice** creates a native invoice for review; submitting posts it. Choose its currency and review the exchange rate (accounting currency per one invoice unit). The latest published rate is suggested; an agreed rate can be entered, including when quotes are unavailable. Approved agreement/work/milestone amounts stay in company accounting currency and are converted into invoice items. Native currency-specific receivables and Payment Entries handle invoice settlement. Project cash and balances report converted company-currency amounts. Worker payments and spending budgets remain in company currency.

Help sits in the top action bar. The overview's inbox and Updates reflect saved business conditions on open/refresh. They are not outgoing email, live push or online signature notifications. Contracts and attachments are native records; a complete online signing workflow is not part of this increment.

## Venue maps and addresses

Venue country and city are separate searchable/filterable fields. The map uses the framework’s bundled Leaflet library and attributed OpenStreetMap tiles, loaded only when Choose from map is selected. Clicking or dragging the pin fills latitude/longitude; it does not guess a street address or silently change the country. Map tiles require Internet access. If the provider cannot load, enter the address and optional coordinates manually; the rest of onboarding still works. No geocoding service, browser location permission, external database or API key was added. Country/city/address and chosen coordinates are saved in the local PP Site record.

## Editing saved onboarding details

Choose any completed sidebar step to revisit it. The server keeps the furthest completed step, so reviewing an earlier screen does not lock later completed steps. Client contact/address and agreement edits save into their original native records. A changed client or project resets dependent setup selections; it does not delete earlier projects. Once assignments or earnings exist, native billing-term changes stay protected. Existing planned event date changes use the event plan to keep staffing and reservations consistent. Country corrections remain allowed, but existing agreement/stock/ledger currencies and amounts are never silently converted.

Employee CSV/XLSX imports accept new worker names as profile labels, not required login IDs. Keep external_id stable for retries and later updates. Employee IDs can explicitly select existing records; name matches require a unique profile and matching date of birth. The expanded template includes required identity/dates/status plus optional contact, address, emergency and passport information. The original nine-column template remains accepted. Optional columns that are absent in an older file are preserved during updates. No staff login is created.

## Select crew throughout the app

The same picker powers onboarding, event-plan Choose crew and Assign workers on the allocations list. Workers lists/profiles and event-site forms also provide Assign workers. The ordinary allocation flow collects project, site, agreement, dates and rates, then creates one native assignment per checked worker in one transaction. Selected tags can be removed before saving. Availability is checked again under employee locks, including fresh employment status and overlapping bookings, so stale previews cannot double-book a worker. New onboarding staffing starts with the chosen headcount; later per-site requirements remain explicit. Saved allocations with attendance retain native release/history protection.

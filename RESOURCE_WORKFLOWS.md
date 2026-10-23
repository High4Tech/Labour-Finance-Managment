# Inventory and transport

Warehouses and Vehicles use the same native lists as Workers: selection, search, filters, sorting, import and contextual quick actions. The one company is resolved automatically; resource dialogs hide the company field. Warehouse ownership uses the existing Warehouse Type field, with Owned and Rented choices.

Warehouse inventory uses compact list rows with directly editable On hand quantities. Reserved quantities come from event allocations and remain read-only. Select rows for Bulk update (set, add or reduce quantities), then Save quantities. Up to 200 changes save together in one native Stock Reconciliation. The server records the current date/time and updater, rejects stale quantities, protects current and future reservations and rolls the whole request back if any row fails.

Quantity editing retains each existing warehouse item's unit valuation. Newly attached quantity-only equipment starts with zero value; there is no guessed purchase price or forced valuation input. Existing financial history is preserved. Stock history shows date/time, changes, balance and the updater. Accounting valuation remains available through the underlying ERP stock records and imports.

Vehicle profiles show identity, status, capacity and event assignments together, following the worker profile layout. Assign to event opens the common event/site reservation dialog. Editing and cancelling assignments uses the same reservation component as agreements and event plans; capacity and date conflicts are rechecked on save.

Agreement → Sites and crew → Transport and inventory remains optional. The reservations appear in Event plan → Transport and equipment. Creating the plan includes reservation dates. Current unsigned signing links are revoked when reservations change; signed snapshots retain their original contents.

Resources use current requests on entry/save. Browser page-script compatibility is checked without clearing other preferences. Shared UI observation and stale-response guards remain in place; resources have no background polling loop.

Verification: `plus_point.testing.run_events` checks actual rollback stock postings, unchanged valuation, bulk atomicity, stale data, ownership and reservation protection. `scripts/browser-resources.cjs` checks native list navigation, company-free dialogs, single-page profiles and inline/bulk request payloads (stock writes are intercepted in the UI test; real posting is covered by backend tests). Set `PP_TEST_BROWSER=msedge` when Chrome is unavailable. `scripts/browser-resource-cache.cjs` checks old page-cache recovery.

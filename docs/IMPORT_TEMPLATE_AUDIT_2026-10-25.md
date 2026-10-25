# Upload template audit — 25 October 2026

All **15 company-app templates passed** real browser file upload, row review, explicit confirmation, native record creation and duplicate replay checks. Each current CSV template was downloaded from the app, filled with dummy data and uploaded. The same data was then uploaded as an Excel workbook with actual spreadsheet date cells: it was marked **Skip**, without creating duplicate records.

## Repaired failures and missing fields

- **Agreement client creation:** a new client name was previously resolved as a required existing Customer. New names now show **Create client** in review and create the client only after confirmation. Optional client contact/address columns were added. Existing clients retain their profiles.
- **Site creation:** a new name in the `site` column was previously treated as a required database ID. A new site name now creates a site in the selected event project. Explicit missing `import:` references still show instructions to upload the prerequisite first.
- **Stock counts:** an empty quantity could be interpreted as zero. Review now requires an explicit quantity, including an explicit `0` when that is intended. Event reservations remain protected.
- **Agreement completeness:** added crew phase and optional vehicle type/quantity, in addition to client contact details. Conditions and vehicle requirements were verified in the resulting agreement. Labour wages remain an event-assignment choice.
- **Worker completeness:** added department, employment type and branch alongside the existing daily/monthly pay, leave and loan settings. New named organisation references are listed in review and created after approval; departments are company-scoped. Loan eligibility accepts `0/1` or `Yes/No`; fractional loan-wait months and unsupported boolean values are rejected during review.
- **Site address completeness:** added country, city, street/address lines, state and postal code. Older address-only templates still work.
- **Upload interface:** added the requested dashed drag-and-drop area, Upload file button, selected filename/size, Remove action and inline format/size/multiple-file errors. Replacing a file discards prior review and approval. Closing the dialog removes its file references and event handlers.
- **Accessibility and recovery:** labelled the template selector, checked light/dark mobile layouts, and replaced raw network-failure text with instructions to review again. Posting is never retried automatically. Saved rows are individually labelled Created, Updated or Skipped.

## Template coverage

Every row below passed CSV creation, invalid-required-field review and Excel duplicate replay. Counts refer to the current downloaded headers; not every field is mandatory.

| Template | Fields | Important data and creation behaviour |
| --- | ---: | --- |
| Workers | 30 | Identity, birth/joining dates, status, contact/emergency/passport details, category, worker number, daily/monthly rates, pay basis, leave allowance, loan eligibility/wait/recovery, department, employment type and branch. New workers and named organisation references are created after review. |
| Clients | 13 | New/existing client name, type, contact, email/phone and address. Currency is chosen on agreements. |
| Warehouses | 4 | Name, Owned/Rented type and Active/Inactive status. Company is automatic. |
| Inventory catalog | 5 | Equipment code, name, stock unit and status. New equipment is created; stock counts are a separate import. |
| Vehicles | 9 | Plate, make/model, crew seats, cargo capacity/unit, fuel and status. New plates create vehicles; existing plates update them. |
| Events | 24 | Client and optional full profile, event/site, dates, crew category/count, Daily/Fixed pricing, client rate or fixed amount, agreement text and currency. Creates an event and its agreement, without assigning workers or inventing attendance. |
| Agreements | 29 | Client and optional full profile, title, dates, status, currency, billing type/value, scope, individual conditions, site/category/count/client rate, phase and optional vehicle requirement. |
| Event sites | 12 | Existing project, new/existing venue identity, status and structured address. A missing new site name creates the site; the project must exist. |
| Warehouse stock counts | 4 | Existing equipment and warehouse, explicit absolute quantity. Server date/time and current valuation are automatic; reservations cannot be edited. |
| Approved daily work | 4 | Existing assignment, work date and units. Rates are taken from the assignment. Creates approved work, not a payment. |
| Fixed milestones | 5 | Existing active fixed agreement, title, date and amount. Creates approved milestone earnings within the contract cap. |
| Project expenses | 7 | Existing project, supplier and non-stock service item, date, amount and description. Posts an unpaid native supplier invoice. |
| Client invoices | 9 | Existing project/client/service item, date, amount, optional approved source type/reference and description. Posts the native invoice. |
| Client receipts | 5 | Existing submitted invoice, date, amount and cash/bank ledger. Posts the receipt and allocates it to the invoice. |
| Worker payments | 6 | Existing event project and worker, date, amount and cash/bank ledger. Posts the historical payment and settles approved outstanding wages. |

`external_id` is included in every count. Keep it stable to recognise reuploads. Existing-record references are still required for historical financial sources; missing assignments, invoices, suppliers or accounting ledgers are not fabricated. Exact names and supported `import:external_id` references resolve only within the applicable permissions/company rules.

Older worker, agreement, event, site, warehouse and stock-value template versions remain accepted. Columns absent from an older template are preserved; deliberately blank optional columns in a current profile template retain the documented clearing behaviour. One agreement/event and one site/category per row remains the supported flat-file layout; extra child rows can be added in the saved editor. Tax-bearing or multi-currency historical invoices require the full native invoice form rather than this net company-currency upload.

## Evidence

- **39/39 database regression tests passed.** These cover native saves/postings, new-name handling, preview without writes, stale review protection, permissions/company boundaries, duplicate prevention, atomic rollback and legacy templates.
- **15/15 template types; 92 browser file-flow checks passed.** Browser uploads were committed to an isolated, ownership-marked audit database; resulting records and immutable import receipts were read back from the database.
- The invoice/receipt cases were rerun after a development HTTP connection interruption. The initial failures and successful retests are retained separately; this was not one uninterrupted green browser run.
- **14/14 upload-interface checks passed**, including real keyboard file-picker use, DataTransfer drops, removal, invalid formats, oversized/multiple files, approval reset, cleanup, mobile containment and **four scoped automated WCAG AA scans** across light/dark desktop/mobile.
- The legacy five-worker browser scenario passed actual creation, per-row Created/Skipped labels, identical-file replay, one import dialog and fresh consent after simulated HTTP and network failures. Its disposable QA fixture was restored.
- Six read-only working-site checks passed: released assets, the three expanded template downloads, a new-worker file review without saving, and dialog cleanup. Test browsers suppress the unrelated native Administrator software-release notice so it cannot obscure the upload controls.
- Dummy accounting results were checked against native records: 15 import receipts, eight ledger rows, PKR 3,500 revenue, 2,000 labour cost, 500 worker payments, 1,500 wages outstanding, 200 supplier cost, 500 client receipts, 2,500 client invoice outstanding and 1,300 operational contribution.

Scripts: `browser-all-import-templates.cjs`, `browser-import-upload-ui.cjs`, `browser-import-confirmation.cjs`, `import-audit-site.py` and `import-audit-data.py`. Raw evidence/screenshots are local under ignored `.local/qa/`. The audit-site helper creates a separate database from the QA snapshot; cleanup checks the exact run, site path and database ownership marker before dropping only that disposable site. No dummy postings were made in the working company.

Backup tag: `backup/pre-import-audit-20261024` → `44d6a20`. Upload assets: `20261025-upload-audit-2`.

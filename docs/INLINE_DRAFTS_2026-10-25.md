# Drafts within Client agreements and Events

Drafts are now rows in their respective native lists, with a Draft status and Resume draft action. The separate Drafts navigation item is removed. A Record status filter offers All records, Draft and Created. Existing drafts are preserved; no incomplete contract, project or event is created just to display a list row.

`planning_list.py` projects the existing planning drafts into each native list's requested fields. Native records retain the framework's field/row permissions and company scope; drafts are scoped to company and owner, with the existing System Manager exception. Queries apply filters, sort and pagination across both sources. Search, date spans, numerical filters and totals include matching draft rows. Fetches are bounded by the selected native page size and search offset; payloads are not sent to the list browser. No polling or extra framework is introduced.

Namespaced draft IDs carry their source through selection/deletion. The protected delete review checks the actual record type and permissions again; scheduled creation must be cancelled before deletion, and completed draft evidence cannot be deleted from a stale selection. Native bulk actions for created records remain available; incompatible actions direct the user to finish/edit the draft. Completion removes the draft projection automatically. Scheduled and failed event drafts remain in Events with their scheduling/review details. Saving/cancelling a schedule returns to Events. Old Drafts list bookmarks redirect into the corresponding product workflow.

The native list component and saved field layouts are reused, with a Status column guaranteed in each. Accessible labels are supplied for selection/filter/sort/navigation icon controls, and header/pagination contrast follows the current theme. Two bounded list adapters share the existing UI observer; hidden lists do not run label updates. Draft saves invalidate cached list arguments so returning to a list fetches current data.

Validation:

- Rollback-only `scripts/audit-workflows.py qa.localhost --inline-drafts`: combined sources, totals, status/search/date/numeric filters, ordering/pagination, native title aliases, tenant boundaries, navigation, scheduled/completed states, source-aware/mixed deletion, plus existing draft/autosave/scheduler/invoice regressions.
- `scripts/browser-inline-drafts.cjs`: real native list rows, resumed draft save, status filters/totals, creating an agreement, resuming event drafts, deleting a draft, desktop/mobile light/dark automated AA scans, no browser errors, exact QA cleanup.
- Read-only inspection of the working account confirms its existing agreement and event drafts appear in the correct lists and the separate Drafts sidebar link is absent. Existing business data is preserved.

Backup: `backup/pre-inline-drafts-20261025` at `c01d94f`.

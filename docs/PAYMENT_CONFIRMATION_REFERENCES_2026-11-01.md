# Bulk wage confirmation and references

Bulk wage confirmation now requires confirmation that the money was actually paid, a paying account and the actual payment date. The external payment reference is optional. A reference entered during bulk confirmation applies to all selected payments; individual references can be added later.

Every confirmation has an internal ID independent of the optional reference. Retrying that confirmation returns the existing native payments rather than posting them again. The entire multi-event batch posts together or rolls back when a reviewed balance changes.

In **Worker payments → Payment history**, select one or several confirmed payment records, then choose **Add / change reference**. This updates the settlement's tracked reference field through native write permissions and update-after-submit validation. It does not edit payment amounts, repost accounting entries or change paid status. Internal accounting confirmation IDs remain intact. Native Payment Entry reference fields and their protections remain unchanged.

The optional `payment_reference` field was added to PP Wage Settlement, with native update-after-submit permission for that field only. Existing fields, financial values and records were preserved. Reference editing uses the same project/worker/settlement lock order as payment posting, and company/document permissions are checked before updating.

## Interface

Worker balances use the shared compact listing component with normal list headers, consistent worker identities, checkboxes, bulk actions, horizontal scrolling and a pinned icon action column. Compact density is the shared default; a comfortable variant remains available. Amount-column headers identify the displayed currency. The Approved wages, Paid, Loan deductions and Outstanding card headings and values are bold.

## Verification

- 70 rollback-only QA tests passed, including no-reference confirmation, required consent, multi-event posting, retry protection after a later reference edit, bulk reference changes, company access, guest denial, stale-balance rollback and existing wage/dashboard/draft workflows.
- 8 focused browser checks passed: shared table and typography; blank-reference submission with consent; selecting actual history rows to edit references; light/dark layouts at 390px and 1600px; WCAG AA checks; and no browser exceptions.
- 49 existing dashboard/shortcut/payment regression checks passed after the shared listing update.
- Browser payment and reference-save requests were intercepted. No live wages were marked paid or payment references changed during browser verification. Actual posting and reference changes were exercised only in rollback-only QA tests, with accounting entries compared before and after reference changes.

## Backup and rollout

Both QA and the company site migrated successfully. Database, site configuration and public/private file backup completed before the company migration:

`sites/high4tech-events-fd166a217c.localhost/private/backups/20261101_232228-high4tech-events-fd166a217c_localhost-database.sql.gz`

The file archives share the same timestamp. Source rollback tag: `backup/pre-payment-references-20261101` at `b2e8537`.

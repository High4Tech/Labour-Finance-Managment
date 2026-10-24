# Category-specific crew availability

New requirement rows select Event crew. The availability banner uses the selected category and date range, including that category's active worker total and peak demand. Changing category, count or dates refreshes the banner; a stale response cannot overwrite a newer category. The original company-wide demand/hiring checks remain separate from the category display. Existing allocations to the same agreement are credited; overlapping external bookings, leave and employment dates still affect availability.

When the selected category has fewer available workers than required, Add crew opens a form inside the current dialog. Its category is preselected and fixed to the requirement's category. Save creates an active worker through native permissions and validation, refreshes availability, and restores the unchanged requirement fields. Cancel returns without creating a worker. Creating a worker does not allocate them or post wages. The same quick worker component is reused by the existing event crew picker. New workers without an explicitly selected category default to Event crew; requests cannot create workers outside the current company or invent new categories.

## Verification

- All 21 planning backend cases passed, including category/date filtering, inactive workers, credit for an agreement's own bookings, default category, contact validation, company access, and creation without allocation.
- The category browser journey passed 11 checks, including three scoped automated WCAG A/AA scans through 2.2 on desktop, mobile and dark mobile. It verified one available driver is displayed as one, empty categories offer Add crew, errors appear inline, the carried category is saved, and the count refreshes without navigating away. The existing crew picker also created and selected a worker through the shared form. The disposable QA company was restored.
- An older form-controls script stopped before reaching its picker because it invokes the retired assign-workers shortcut, which now opens the event editor. This was not counted as a pass. The current picker component was tested directly in the passing category journey.
- Syntax and whitespace checks passed. Evidence stays private under `.local/qa/crew-category-*`.

The asset revision is `20261024-crew-categories-1`. Working and demo caches were refreshed; a read-only working-site check verifies both new scripts, default category, category-scoped API response and agreement opening. No customer business records were created by deployment checks.

The previous source is preserved as `backup/pre-category-availability-20261024`. Docker needed a local startup repair before testing: its broken temporary socket folder was preserved as `run.stale-20261024-2043`, and a fresh temporary run folder was created. No containers, database files or storage volumes were deleted.

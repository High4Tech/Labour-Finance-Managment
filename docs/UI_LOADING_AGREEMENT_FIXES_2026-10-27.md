# Loading, agreement and billing fixes — 27 October 2026

The invoice list failed because its additional project field was appended as a string to a list of field/doctype pairs. The framework interpreted that string as a field on “DocType r”. It now uses the correct pair, and the browser regression opens Billing and finances through the sidebar, agreement selector and billing page.

## Delivered changes

- Content-only skeleton loading with a centered green Freddy logo. Loading never becomes a speech bubble. No pause/play buttons. Important contextual feedback animates for at most 4.5 seconds and respects reduced motion.
- Brand-green page actions; dark primary actions scoped to forms. Save draft remains green before agreement review, then amber. Review has one top Create agreement action and a disabled footer Next alongside Previous.
- Consistent 40px desktop / 44px mobile input and choice controls. Start/end dates share a row; the historical-date checkbox sits immediately below. Removed the future-occurrences note from this form without clearing stored legacy values.
- Site-name suggestions immediately follow the name input, include Add new site first, filter as the user types, and support Enter for a new name.
- Missing daily client prices identify their actual field. Modal validation stays in the modal; other wizard errors reveal the affected step or appear in its active section.
- Compatible repeated site/category requirements combine headcounts and phases. Different client rates require correction before the new row is accepted. The flow explains this combination before adding crew. Imported compatible duplicates are normalized as well.
- Daily milestone rows expose Edit milestone and Generate invoice. Future or unearned periods explain why generation is disabled. Approved-work and immutable invoice checks remain enforced. Fixed milestone actions use the same labels. Generated PDFs open in the existing preview and remain in Documents.
- Edited daily milestone names survive schedule regeneration and subsequent agreement-date changes. Invoiced periods retain their protected values.
- Desktop dialogs center within the viewport; tall bodies scroll inside the dialog. Wider navigation, larger text, green/white current-page selection, grey detail-page backgrounds, white elevated outer sections and tinted inner headings.
- Updated cache versions for every changed script/style and avatar reference.

## Verification

| Suite | Result |
| --- | --- |
| Architecture, profiles/billing, event start, drafts, sharing, currency backend regression | 70 passed |
| Component validation unit tests | 11 passed |
| Focused loading/layout/billing browser regression | 13 passed |
| Agreement creation, crew combination, sharing, invoice PDF and guest signing browser flow | 12 passed |
| Typing, initial paint, selection/deletion cleanup, worker controls, responsive/signing browser regression | 11 passed |

Total: **81 backend tests and 36 browser checks passed**. Browser checks include scoped automated WCAG AA scans at desktop/mobile sizes in light/dark themes, exact radio/input alignment, actual delayed loading, absence of runtime errors, successful PDF downloads and persisted document records. This is automated coverage of the tested views, not an accessibility certification of every screen.

All mutation tests used exact disposable QA fixtures and restored them. No test email was sent. The working-account smoke check opened the real agreement profile and the repaired billing sidebar → agreement selector → invoice page without saving records: 4 agreement/commercial terms, 2 events, 50 workers and 1 planning draft were available, with no browser runtime errors. These counts include activity performed by the user; this release performs no data reset or schema migration.

## Recovery

Previous source release: `216bcd1ea874032bb3c23c6bbabae4b49efc0a58`, retained as recovery tag `backup/pre-ui-20261027`.

Full working-site backup (database, public/private files and private configuration) completed successfully under:
`/home/frappe/frappe-bench/sites/high4tech-events-fd166a217c.localhost/private/backups/20261027_015840-high4tech-events-fd166a217c_localhost-*`

Backups and private QA artifacts are excluded from Git. Local QA evidence is under `.local/qa/`, including `ui-20261027.json`, `ui-backend-20261027.log`, `ui-components-20261027.log`, `ui-sharing-20261027.log`, `ui-stability-20261027.log`, and loading/profile/billing screenshots.

# Saved agreement layout

The saved agreement profile now follows the supplied visual reference: a dark teal header, four summary cards, a compact main document and a focused collaboration sidebar. Creation and the explicit full editor keep their existing guided flow.

## Components and actions

- Header: back link, title, reference, lifecycle status, Edit agreement, Send and sign and the existing guarded Delete action.
- Summary: client, inclusive agreement period, billing model and fixed contract value in the agreement currency. Daily agreements show their currency and category pricing context instead of an invented fixed total.
- Details: client, dates/name, separate scope, conditions, pricing/milestones, sites/crew and optional vehicles. Section edits reuse the native popup editor and existing scoped save API.
- Tabs: Details, Milestones, Documents, Comments and Activity. Tabs support arrow keys, Home and End. The pricing component moves between Details and Milestones rather than being duplicated.
- Sidebar: event handoff and finance link, document upload, one comments composer and a concise activity timeline. The other tabs expose full saved files, comments and available activity.
- Signing: one on-demand popup retains the existing link, preview, email availability checks and request history. Rapid clicks share its pending render. Generating a link never sends email automatically.
- Documents: the native uploader creates private Contract attachments. Both upload entry points use the same handler and refresh the document list after success.

No financial calculations, posting rules, permission checks, business statuses or schema changed. Existing data is read through the same agreement/activity APIs. There are no new packages, remote services, polling loops or persistent form caches. Tab preservation is one refresh only.

## Verification

- Existing profile regression: **15 checks passed**, including real section saves, daily payment cadence, nested crew editing, event/full-editor regressions, creation-to-signing and automated accessibility checks.
- New layout regression: **13 checks passed**, including a real planned milestone, scope edit, comment validation/posting, keyboard tabs, native private dummy upload, signing link generation, delete-review cancellation and four light/dark desktop/mobile automated AA scans. It asserts that the hero title and every action remain inside the header after resizing. The exact disposable QA company and upload were removed afterward.
- Agreement import handoff: **10 checks passed**, covering automatic editor handoff, duplicate replay, batch choices and preservation of the previous partial draft. The exact QA fixture was restored.
- Working-site smoke: **8 read-only checks passed** for the saved layout, section popup, signing controls, five tabs, responsive resizing, event profile, full editor and browser errors. No business data was changed or email sent.

Local evidence is under `.local/qa/`, including `agreement-layout-20261025.json`, `agreement-layout-working.json`, `agreement-layout-regression.log`, `agreement-layout-import.log` and screenshots for light/dark desktop/mobile. Visual review found and corrected a resize-dependent clipped hero; automated contrast checks alone did not catch it. Automated A/AA checks supplement visual and keyboard review and are not a full WCAG certification.

Code backup before this change: `backup/pre-agreement-layout-20261025` at `12484fc`. Native business records and the existing private backup remain unchanged.

# Freddy feedback

Freddy replaces generic presentation for company-app field errors, action errors, snackbars, message/confirmation dialogs, import issues, loading/empty states, setup guidance, information popovers and client-signing feedback. It appears inside the relevant field, section, dialog or existing snackbar rather than as a permanent floating chat panel.

Messages use a deterministic local copy layer: common date, email, phone, number, crew, access and connection errors explain the problem and a next step. Other server errors retain their details instead of inventing a diagnosis. Rich error messages retain record links, tables and button callbacks. Validation, permissions, confirmation requirements, accounting and signing acceptance checks are unchanged.

## Avatar and behavior

- Source: the app owner's `freddy-avatar.zip`, SHA-256 `a09e252be68959ef85a956607dfc75906b6db6a440d38363823c49ddb08f1c09`.
- The supplied 23-expression procedural SVG runtime is adapted to native JavaScript; React, blob modules, eval, external avatar services and new UI frameworks are not needed.
- Still SVG expressions are used for the usual inline render. Errors use **confused**, connection failures **sad**, warnings **surprised**, guidance **listening**, information/empty states **curious**, loading **thinking**, and success **happy**.
- Hovering or focusing the helper's field can play a short expression. Only one avatar animates at a time, for at most 3.4 seconds. Automatic animations are limited to one per five seconds. Hidden tabs, route changes and removed hosts stop animation. Reduced-motion mode stays still.
- Existing error-to-control descriptions, focus, native toast handles/actions/dismissal, and dialog review links remain available. Generic "review highlighted fields" banners are suppressed when local field errors already explain the problem.
- The existing bounded UI observer decorates messages in batches of at most 80 changed nodes. Already decorated text is skipped. Initializing the script twice does not add duplicate hooks. No polling loop or remote inference request is introduced.
- Public signing-page errors sit outside the input's label and are linked with `aria-describedby`; fixing an input removes only Freddy's own error description. Consent still blocks acceptance until the client explicitly agrees.

## Source and integration

The reusable component is `public/js/feedback.js`, styled by `public/css/feedback.css`. Use `plus_point.freddy_feedback(element, { message, tone, solution, rich })` or mark a message with `data-freddy-feedback` / `data-feedback-tone`. The app's existing feedback surfaces are adapted automatically. Platform administration screens are excluded.

Rebuild the reviewed avatar with `scripts/build-freddy.py <source.zip>`, then `scripts/build-freddy-images.cjs` using the bundled Node/Playwright runtime. The build is pinned to the reviewed archive hash. Static SVGs contain a proper XML namespace and stable clip identifiers. Changes to the source export require a fresh review and source-hash update.

## Verification

Local evidence is in `.local/qa/` and is excluded from Git:

- `freddy-feedback-20261025.json`: **20 browser checks passed**, including actual email/required constraints and clearing, correct expressions, image decoding, native action callbacks, rich dialog updates, untrusted error text, duplicate initialization, animation cleanup, reduced motion, and unsigned client-signing validation.
- Four automated WCAG A/AA scans passed at desktop/mobile widths in light and dark modes. These automated checks are not a complete WCAG certification.
- `freddy-profile-regression.log`: **15 existing agreement/event profile checks passed**, including saves, crew popup editing, recurring-payment configuration, draft comments, signing handoff and five automated AA scans.
- `freddy-import-regression.log`: **10 agreement-import checks passed**, including upload/review, editor handoff, duplicate replay, draft preservation, batch selection and two automated AA scans.
- `freddy-working-smoke.json`: **5 working-site checks passed** for local runtime loading, actual image decoding, contextual error/clearing, public signing recovery and zero business-record writes/browser errors. A native dialog preview was used; no real client form was saved.

Screenshot review caught and corrected missing namespaces in the first still-SVG export. Image decoding is now asserted in the browser test, rather than inferring success from markup alone. No signed agreement, email, payment or financial posting is created by these tests; exact QA fixtures are restored.

Total for this change: **50 browser checks passed**, including 11 automated AA scans. No server business logic or database schema was changed. Working, QA and demo asset caches were refreshed.

Code backup: `backup/pre-freddy-feedback-20261025`.

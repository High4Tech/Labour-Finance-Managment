# Customer workspace design

The customer workspace prioritizes frequent tasks while keeping native ERPNext records available. These are practical applications of relevant UX principles, not a claim that every UX law applies or that usability has been validated with real customers.

| Principle | Applied change |
| --- | --- |
| Reduce competing choices ([Hick's law](https://lawsofux.com/hicks-law/)) | Attendance is the prominent home action; three grouped rows cover workers/sites, client billing and worker payments. Setup records sit in collapsed Business setup. |
| Reveal detail when needed ([progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)) | The six-step guide and Business setup sidebar group begin collapsed. Screen explanations and field tips remain available; longer field text appears on focus. |
| Group related controls ([proximity](https://lawsofux.com/law-of-proximity/)) | The sidebar separates Daily work, Clients and billing, Payments and costs, and reports. Each home task keeps its explanation and links together. |
| Prefer recognition ([recognition rather than recall](https://www.nngroup.com/articles/recognition-and-recall/)) | Plain-language list titles/actions, named link titles and shorter purpose text reduce the need to remember internal DocType names or IDs. |
| Make targets easier to reach ([Fitts's law](https://lawsofux.com/fittss-law/)) | Home buttons and task links have a minimum 44px height, visible keyboard focus and a stacked mobile layout. This is not a whole-app accessibility certification. |
| Feedback, consistency and error prevention ([usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)) | Existing Desk dialogs, lists and validation remain familiar. Attendance shows progress, keeps selections after errors, reopens saved registers, and requires explicit review/submission before approving earnings. |

Financial distinctions remain explicit: earnings, invoices and payments are different events. Simplifying navigation does not change rate snapshots, billing rules, document permissions or approval behavior. Broad upstream HR/accounting screens retain their native complexity; dedicated supervisor roles and field privacy remain separate release work.

Verification uses real browser interactions at desktop and 390px mobile widths, including attendance creation/reopening and temporary-record cleanup. Screenshots and detailed results are recorded in VERIFICATION_STATUS.md. Customer usability sessions, assistive-technology acceptance and large-scale performance testing remain unrun.

High4Tech has its own task home for software customers, pricing, support and finances. App/module switching and unrelated workspaces are hidden, including command suggestions. Related native accounting/employee records remain available; backend permissions still apply.

The overview now leads with a company-scoped dashboard, with the original links underneath. A single metric strip provides the primary hierarchy, followed by attendance/sales history and a project/customer table. Desk typography and theme variables retain the product identity; tabular numbers and explicit period/currency labels make figures comparable. The only chart accent uses the existing brand's amber family. Panels stack on mobile and the metrics use two columns. Empty financial periods display actual zero totals and explain the absence of posted sales. Refresh and company switching are explicit actions; loading/error states never replace the work tools.

Spending and workflow states now pair red/amber/green/neutral treatment with a plain-language reason and an action. Near-budget submissions pause for explicit acknowledgement; over-budget approvals stop without discarding the draft. Existing overruns preserve history and link to budget review. Only two priority notices lead the dashboard; More next actions reveals additional conditions. Empty and failed loads offer setup/retry while preserving normal work tools.

Guided setup uses the existing white/gray Desk surfaces, #171717 text, #626b75 secondary text and native focus/semantic colors. Native typography and left-aligned labels stay consistent with daily work. Its single active step and progress bar express the actual worker → site → agreement → assignment sequence. The rest of Desk is blurred and inert only while the guide is open; a persistent Skip setup and explore action returns control without losing saved records. The guide uses native form validation and handles missing prerequisites within the relevant step.

Imports separate file selection, review and posting. Help changes with the selected template; reference IDs reduce recall. The preview labels Create, Update, Skip and Fix explicitly, pairs spending colors with text, and provides downloadable row errors. File/company/type changes invalidate the preview. Confirmation is a distinct action after review. Results show saved record links and a next action, and the table scrolls within the mobile dialog rather than widening the page.

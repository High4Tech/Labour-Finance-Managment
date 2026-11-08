# React interface checkpoint — November 3, 2026

For the later resource, attendance, accounting and D: storage checkpoint, see the [November 9 migration ledger](REACT_MIGRATION_2026-11-09.md). The remaining-scope paragraph below describes this older checkpoint.

The company dashboard uses one React loading layout. Local saves, currency changes and realtime notifications share one refresh queue, and dashboard updates preserve the mounted controls and charts. Agreements, Jobs & Events, Clients, Workers and Worker Payments take their full main width on the first ready frame. The agreement editor and its footer span the main area.

Worker Payments allows selection for review even when no balance is payable. Recording still requires permission, an approved outstanding balance and explicit confirmation; payment references can be supplied later. React tables share a square checkbox. In forms and dialogs, long tables scroll within their section, with sticky headings and horizontally scrollable data. Schedule rows include agreement context and show a single date plus configured hours for daily work. Historical schedules without hours are labelled accordingly.

All 15 product import types use the shared React upload and review dialog. Native advanced imports and existing server permissions, validation and transaction handling remain available. No database schema change was needed.

- TypeScript check, production build and 22 frontend state tests passed.
- 165 browser checks passed across dashboard, layout, lists, agreements, payments, workers, clients, imports and shared components. Browser tests intercepted financial writes.
- The isolated backend architecture suite passed 321 tests; the separate planning and import suite passed 83 tests. These suites overlap.
- Three final performance runs measured warm list navigation medians of 136–143 ms and cold readiness of 2.55–2.83 seconds. The warm-route loop retained one React root and one list listener, with zero duplicate native list queries. Cold startup still decodes about 9.4 MB including native Desk assets. This does not establish a cold-start improvement.

Remaining native screens include event create/edit/detail, staffing and calendar, attendance, warehouse/equipment/vehicle workflows, remaining finance and reports, the public client portal and the standalone company shell. The migration is incomplete; these workflows still use their existing interfaces and backend.

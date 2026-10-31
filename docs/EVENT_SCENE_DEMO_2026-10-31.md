# On-demand event scene demo

Implemented October 31, 2026, as a supporting preview in the existing company Event Overview. Select **View event scene** to open it; **Back to event details** returns to the original interface.

## Component and visual contract

- One fixed isometric conference pavilion, teal/white architecture, landscaped edge and vehicle lane. The same component serves every preview.
- Existing event name/reference, venue, dated staffing demand, unique available assignments and dated vehicle reservations supply the changing information. Equipment is excluded.
- Walking figures during Working hours; dimmed lights and still figures After hours. Now checks the current site timezone and event dates against the temporary demo schedule. Overnight shifts belong to their starting work date.
- Preview hours default to 09:00–18:00 and can be adjusted inside the dialog. They are explicitly unsaved demo settings: existing records have no persistent shift-hours fields. The scene is scheduled activity, not live location/attendance tracking.
- Exact numeric totals accompany representative populations capped at 36 workers and 6 vehicles. No false assignments or bookings are created for presentation.
- Native accessible dialog, labelled keyboard controls, zoom/rotate/reset, motion pause, light/dark themes and mobile layouts. Unsupported graphics show event counts and retain navigation.

## Loading and lifecycle

The ordinary app includes only a lightweight entry action and feature definitions. The scene component, its CSS and Three.js are downloaded only after the explicit action. Three.js r180 is pinned, bundled locally and MIT-licensed; no CDN or model service is contacted at runtime.

The local engine is 495,266 source bytes / 125,306 gzip bytes. It is cached across openings. No separate venue files, texture downloads or animation packages are requested. Workers use instanced meshes; the measured 15-person preview uses 134 draw calls, 5 geometry buffers and 1 generated sign texture.

The active scene has one animation loop capped at 30 FPS and a maximum pixel ratio of 1.5. Paused, reduced-motion and off-hours states render only on change. Hidden tabs stop the loop. One boundary timeout updates the Now state at the next start/end/midnight; it is not an API polling loop. One local resize observer is disconnected on close. Replacement, closing and route navigation release all GPU resources, renderer context, canvas, listeners and timer. A partially initialized scene is also cleaned up if graphics fail.

## Supplied library findings

The complete listing of the user's [SimReady asset bucket](https://huggingface.co/buckets/radio-basen55/simready-assets-bucket) was inspected: 16,900 files comprise 9,158 JSON, 5,915 MDL, 1,815 TXT, 10 CSV, one Markdown and one extensionless file. No model geometry, texture images or character animations are in that snapshot. No incomplete models were added to the app. This demo uses original procedural models; suitable complete models can replace the centralized template later. See [asset references](ASSET_LIBRARY_REFERENCES.md).

## Verification

- `node tests/event-scene-state.cjs`: eight checks of site timezone, shift boundaries, overnight work dates, venue/date counts, deduplication, invalid hours, inactive events, demo isolation and bounded graphic populations.
- `node scripts/browser-event-scene.cjs`: 15 read-only company checks of zero initial scene requests, explicit local loading, animation pause, off-hours, hidden-page pause, reduced motion, desktop/mobile light/dark AA accessibility, cleanup, cached reopening, 50-person/two-vehicle reuse, graphics fallback, navigation cleanup and interrupted-download recovery. Company Event Plan, Contract Terms, Assignment, Daily Register, Sales Invoice and File counts are unchanged before/after.
- QA `audit-workflows.py --crew-regression`: all 118 tests passed, zero errors or skipped cases (211.986 seconds). Includes planning, hierarchy and event/resource workflows, including reservation kind/site identifiers. All fixtures roll back.
- The initial QA run passed 117 of 118 cases. The remaining leave-allowance test assumed tomorrow stayed in the current month, which is false on October 31. Its date now stays in the same month; no leave business rule was changed.

Browser evidence and private screenshots remain ignored under `.local/qa/`. Local runs measured 1.4–2.2 seconds for cold opening and 0.3–0.8 seconds for cached reopening. These are local-machine measurements, not production/mobile guarantees. Ordinary dashboard and event opening made zero scene/engine requests.

References: official Three.js [rendering on demand](https://threejs.org/manual/pages/rendering-on-demand.html), [resource cleanup](https://threejs.org/manual/pages/cleanup.html), and [WebGL renderer](https://threejs.org/docs/pages/WebGLRenderer.html).

No schema migration, emails, live-company data mutation or accounting/stock posting is needed. Native Frappe permissions and advanced views remain intact.

# Dashboard chart bundle

Build-only dependencies for the shared PLUS POINT chart component. The app serves the committed bundle from its own asset directory; it does not contact a CDN or require npm in production.

From the repository root:

```sh
npm ci --ignore-scripts --prefix scripts/chart-bundle
npm run build --prefix scripts/chart-bundle
```

The lockfile pins Apache ECharts 6.1.0 and esbuild 0.28.2. Only Line, Bar, Pie, Grid, Tooltip, Aria and SVG rendering modules are registered. The build writes the minified engine, license/notice file and size/SHA-256 manifest to `apps/plus_point/plus_point/public/js/vendor/`.

After an upgrade, bump the engine version in `public/js/lazy_features.js`, review licenses and run `scripts/browser-dashboard.cjs`. The shared adapter is `public/js/charts.js`, with its visual tokens in `public/css/charts.css`. Native Frappe chart capabilities remain intact.

# Supplied design assets

Source: the user's `Downloads.zip`, supplied on 29 October 2026. These third-party visual assets retain their original ownership; the app's MIT license does not relicense them.

The app uses 27 file-type variants, 239 rectangular country flags, the existing Google Drive integration icon and the upload symbol extracted from the supplied default upload composition. `manifest.json` records each archive member, byte count and SHA-256 digest.

The interactive upload layout is implemented as HTML/CSS and real native controls. Exported SVG text/layout screenshots are not used as replacement controls. Selection, drag/drop, review, errors, progress and private upload behavior remain functional. General navigation and action icons keep the existing Tabler contract.

Social, payment-provider, cursor and unused integration variants are not downloaded or initialized on app startup. Add a matching asset through the same shared map when the corresponding supported interface is introduced. Brand images must not imply an integration exists.

To reproduce the imported vectors, run `scripts/install-design-assets.py` with the original archive path; run `scripts/check-design-assets.py` to verify integrity, local-only references and absence of active content. Assets are displayed through local `<img>` URLs, never untrusted inline SVG markup.

# Local storage audit — 9 November 2026

The reported 13 GB was the shared Docker virtual disk, not the company database. This audit measured database metadata/indexes, site/upload directories, runtime dependencies, Docker image/volume use and diagnostic logs without reading business-record contents into the report.

## Findings

| Category | Measured size before cleanup | Interpretation |
| --- | --- | --- |
| Company tables and indexes | 60.69 MiB | Includes all installed framework metadata; the largest table is native field definitions, about 12.58 MiB. |
| Company uploaded files | 1,843,446 bytes | About 1.8 MB, not gigabytes of business documents. |
| Company site directory | About 6.3 MiB | Includes logs/configuration and a previous compressed database/file backup, as well as uploads. |
| Demo database | 65.78 MiB | Separate development/demo site, retained. |
| Platform database | 57.59 MiB | Existing platform administration/provisioning site, retained. |
| QA database | 125.72 MiB | Separate regression site, including native search and deletion history, retained. |
| MariaDB data volume | About 913 MB reported by Docker | All databases plus engine tablespaces, redo/undo/system files and allocated pages. Not equivalent to business-row size. |
| Bench persistent volume | About 2.919 GB reported by Docker | Mostly installed framework source, Node build dependencies, Python runtime and Chromium. |
| Installed images | About 4.341 GB reported by Docker | Bench/development image, MariaDB and Redis; all currently in use. |
| Bench diagnostic logs | 311 MiB | Unbounded supervisor/worker shell redirects were a real avoidable growth source. |
| Docker VHD file | 12,386,828,288 bytes initially | Includes installed software, filesystem allocation and unused blocks; not a database dump. |

Docker image/volume totals and filesystem usage have different accounting boundaries and should not be treated as an exact additive breakdown of VHD physical size. Four isolated local databases are expected for this development/testing setup. They are not four copies of customer transactions.

## Applied changes

- All four containers now use Docker's `local` logging driver with 10 MB maximum files, three retained files and compression enabled. Existing containers were recreated with their original data volumes; no volume/image prune was run.
- The local supervisor sends its console output and worker output to that bounded logger. The generated local Procfile no longer redirects worker output indefinitely into persistent files.
- The five known bench diagnostic logs have an 8 MiB rotation threshold and three compressed archives. The existing supervisor loop checks these once per minute, with no new polling service. Native Frappe log handlers, financial audit/deletion history and business tables were not replaced.
- Existing diagnostic logs were preserved in a compressed archive on D: before rotation. Bench log storage measured **20 MiB afterward**, a reduction of about **291 MiB** inside the Docker volume.
- All four sites received fresh native compressed database and public/private file backups. Sixteen backup files total about 16 MB; gzip streams were read to completion to validate readability. This is not a certified restore drill. Backups and diagnostic archives are private and ignored by Git under `.local/backups/storage-cleanup-20261109/`.
- Filesystem trim returned about 1.7 GiB of unused blocks to the virtual-disk layer. This does not by itself prove that Windows reclaimed the same amount of physical file space.

## Compression and retention decisions

MariaDB binary, general and slow-query logs were already off. InnoDB per-table files and the native Dynamic row format were enabled. Native Deleted Document storage already uses compressed rows. Blanket table compression or OPTIMIZE/rebuild was not applied: the main database is only about 61 MiB, and its small potential savings do not justify a CPU/I/O-heavy rewrite of working framework tables. Database backups, file backups and rotated diagnostics are compressed instead.

The upload audit found small files lacking a direct File URL registration (about 0.44 MB in the company site and 3.34 MB on QA). Missing a File row alone does not establish that a document is unused: links can be stored in rich text or other fields. They were preserved rather than deleting possible document evidence. No company record, upload, ledger, native DocType or installed capability was deleted to save space.

## Pending Windows compaction

Both Windows administrator prompt attempts were canceled before the elevated helper started, including the user-requested retry. Offline VHD compaction therefore **has not run**. After container recreation the VHD length was 12,420,382,720 bytes; unused blocks may remain inside it despite lower live log usage. Do not report the full VHD as reduced yet.

`scripts/compact-local-docker.ps1 -Apply` is a prepared operator helper requiring administrator approval. It checks the explicit D: disk and backup set, trims, stops Docker cleanly, confirms exclusive disk access, invokes DiskPart compaction and restarts Docker in a finally block. It does not terminate unrelated Ubuntu distributions or delete Docker volumes/images. Its PowerShell syntax was validated; elevated compaction remains unverified until approved and run. Review the generated `.local/storage-compaction/result.json`, then repeat health and record-count checks.

Microsoft documents that dynamic virtual disks grow but do not automatically shrink when files are deleted, and that compaction requires a detached/read-only disk: [compact vdisk](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact-vdisk). Docker documents rotation/compression and the need to recreate existing containers for new logging settings: [local logging driver](https://docs.docker.com/engine/logging/drivers/local/).

## Verification

Four storage-maintenance tests passed: compressed archive fidelity and open-file inode preservation; bounded retention and small-log preservation; failed archive leaves the original intact; only the known local worker redirect is changed. Compose configuration validation and Python source compilation passed. PowerShell parsing passed. The app and MariaDB containers are healthy, native HTTP ping responds, and the six-check migration browser smoke suite passed after the restart with no unhandled browser errors.

Exact before/after counts matched on all four sites for companies, clients, workers, agreements/contracts, events, assignments, attendance/work entries, payments/settlements, sales/purchase invoices, loans/recoveries and File records. Counts and detailed test artifacts remain in the private `.local/` audit files. This storage-only change does not rerun or recertify the prior full UI/business regression suite.

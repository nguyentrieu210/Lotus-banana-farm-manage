# Lotus Work PWA deployment — 2026-10-17

- Image: `lotus-work-review:v1-20261017`, built from running image `lotus-mobile-rbac:v1-20261017` using `deployment/Dockerfile.work-review-v1`.
- Compose override: `deployment/compose.work-review-v1.override.yaml`, used as final overlay after existing Lotus runtime configuration.
- Site: `frontend`, external route `/work`.
- Backup taken before schema migration: `sites/frontend/private/backups/20261017_210003-*` (database, public and private files, site configuration; retained inside Docker volume).
- Migration ran using an ephemeral container with the new image; 6 review fields confirmed in `tabDaily Work Result`.
- Backend/frontend/queue-short/queue-long/scheduler switched to the new image; Frappe cache cleared and maintenance mode switched off.
- Smoke: public `/work` -> login HTTP 200, compiled Work JS 200, manifest and work service-worker 200, warehouse and buying routes accessible. Backend role abilities loaded.
- Still **not UAT accepted**: do not treat tests or smoke as proof of multi-role review/offline/actual payroll/stock workflows; field validation remains mandatory.
- For rollback: previous image is `lotus-mobile-rbac:v1-20261017`. Rolling back the image alone does not revert the DB schema; restore site backup only if a full database rollback is required, after stopping writes and assessing subsequent transactions.

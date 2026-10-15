# Local Lotus Stock deployment — both containers must use the same image

## Issue reproduced on 15/10/2026

Stock Vue bundle was updated in **frontend container**, but the request to `/lotus/kho` is rendered by Frappe's **backend container**. The route `lotus_farm/www/lotus.py` reads the Vite `.vite/manifest.json` from the **backend** app filesystem.

When backend was running `lotus-stock-audit:20261015`, it referenced `stock-agVkqIUa.js` (old dashboard), even though frontend's asset directory contained `stock-CCKkt0Tq.js` (new table-only screen). Nginx served both asset URLs, so HTTP 200 checks alone were not evidence of correct deployment.

## Fixed

Both `lotus-backend-1` and `lotus-frontend-1` now run **`lotus-stock-table-only:20261015`**. The local Windows runtime `compose.yaml` was also updated for backend and frontend images, so running plain `docker compose -p lotus -f compose.yaml up -d` does not silently revert to `lotus-erpnext:local`.

Do **not** deploy a new frontend bundle to only the frontend container. Run both services with the same image tag and clear the Frappe page cache:

```powershell
docker compose -p lotus -f compose.yaml up -d --no-deps --force-recreate backend frontend
docker exec lotus-backend-1 sh -lc "cd /home/frappe/frappe-bench && bench --site frontend clear-cache && bench --site frontend clear-website-cache"
powershell -NoProfile -ExecutionPolicy Bypass -File deployment/verify_stock_8080.ps1
```

The above compose file is the *local runtime* compose at `C:\Users\ADMIN\Documents\ChatGPT\a\lotus-runtime\compose.yaml`, not a file in this repository. When using a different compose file, include the override `deployment/compose.stock-table-only.override.yaml` alongside the appropriate base compose file. Only the app services should be recreated; do not recreate MariaDB or delete persistent volumes.

## Validation

- Confirmed backend and frontend Vite manifests both reference `stock-CCKkt0Tq.js` and `stock-B0YzyWov.css`.
- Called Frappe's `lotus.get_context()` as an authenticated user against the live site and verified the routed script and CSS are the new asset hashes.
- `GET /assets/lotus_farm/frontend/assets/stock-CCKkt0Tq.js` and CSS both returned HTTP 200.
- `/lotus/kho` redirects guests to login, as designed. A guest redirect or HTTP 200 for a static asset does **not** confirm the authenticated page's bundle.
- No warehouse data or schema changed to fix this deployment issue.

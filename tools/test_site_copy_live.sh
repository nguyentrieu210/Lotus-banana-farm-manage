#!/bin/bash
# Runs on the VPS. Builds mua.test inside the disposable stack lotus-003-proc from the latest existing backup of the
# live site (read only on the live side: one backup file and the private files are copied out). No mail, no scheduler.
set -euo pipefail
LIVE=lotus-vps-backend-1
TEST=lotus-003-proc-backend-1
B=/home/frappe/frappe-bench
W=/opt/lotus-003-test/live-copy
mkdir -p "$W"
backup=$(docker exec $LIVE bash -lc "ls -1t $B/sites/frontend/private/backups/*-frontend-database.sql.gz | head -1")
echo "backup: $(basename "$backup")"
docker cp "$LIVE:$backup" "$W/db.sql.gz"
rm -rf "$W/files"; docker cp "$LIVE:$B/sites/frontend/private/files" "$W/files"
# The push key stays on the live site only: the copy can never send a real notification.
rm -f "$W/files/lotus-push-vapid.pem"
docker exec $LIVE bash -lc "cd $B && python3 - <<'PY'
import json
src = json.load(open('sites/frontend/site_config.json'))
print(json.dumps({k: src[k] for k in ('lotus_purchase_flow_company', 'lotus_purchase_flow_since') if k in src}))
PY" > "$W/flow.json"
docker cp "$W/db.sql.gz" "$TEST:/tmp/live-db.sql.gz"
admin=$(head -c 18 /dev/urandom | base64 | tr -d '/+=')
docker exec $TEST bash -lc "cd $B && bench new-site mua.test --force --db-root-password procurement-test-only --admin-password '$admin' --mariadb-user-host-login-scope='%' --source-sql /tmp/live-db.sql.gz" > "$W/new-site.log" 2>&1
docker cp "$W/flow.json" "$TEST:/tmp/flow.json"
docker exec $TEST bash -lc "cd $B && python3 - <<'PY'
import json
path = 'sites/mua.test/site_config.json'
dst = json.load(open(path))
dst.update(json.load(open('/tmp/flow.json')))
dst.update(mute_emails=1, pause_scheduler=1, host_name='http://mua.test')
json.dump(dst, open(path, 'w'), indent=1)
PY
mkdir -p sites/mua.test/private/files && rm -f /tmp/live-db.sql.gz"
docker cp "$W/files/." "$TEST:$B/sites/mua.test/private/files/"
docker exec -u root $TEST bash -lc "chown -R frappe:frappe $B/sites/mua.test/private/files" || true
docker exec $TEST bash -lc "cd $B && bench --site mua.test migrate --skip-search-index" > "$W/migrate.log" 2>&1 || { echo MIGRATE-FAILED; tr '\r' '\n' < "$W/migrate.log" | grep -v '^Updating\|^Migrating\|^$' | tail -25; exit 1; }
tr '\r' '\n' < "$W/migrate.log" | grep -v '^Updating\|^Migrating\|^$' | tail -3
rm -f "$W/db.sql.gz"
echo "mua.test ready"

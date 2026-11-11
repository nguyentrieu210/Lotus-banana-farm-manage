#!/usr/bin/env bash
# Bộ thử dùng-rồi-bỏ `procurement.test` cho các script tests/integration/verify_procurement*.py,
# verify_purchase_flow.py, verify_receipt_reason.py, verify_erp_workbench.py (dữ liệu giả, CSDL riêng).
# Dùng deployment/compose.procurement-test.yaml với image có sẵn trên máy; mã lấy từ worktree này (chỉ đọc).
#
#   tools/test_site_procurement.sh up            # chạy db, redis, backend
#   tools/test_site_procurement.sh site          # tạo site procurement.test (erpnext, hrms, lotus_farm)
#   tools/test_site_procurement.sh migrate       # migrate lại sau khi đổi schema
#   tools/test_site_procurement.sh run <script>  # chạy một script, vd: run verify_purchase_flow
#   tools/test_site_procurement.sh drop          # xóa container và volume của bộ thử
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${PROJECT:-lotus-003-proc}"
IMAGE="${IMAGE:-lotus-local-test:20261104}"
BENCH=/home/frappe/frappe-bench
OVERRIDE="$HERE/.local/compose.procurement-image.yaml"   # .local/ bị git bỏ qua

compose() { docker compose -p "$PROJECT" -f "$HERE/deployment/compose.procurement-test.yaml" -f "$OVERRIDE" "$@"; }
in_box() { MSYS_NO_PATHCONV=1 docker exec -i "$PROJECT-backend-1" bash -lc "cd $BENCH && $*"; }

up() {
  mkdir -p "$HERE/.local"
  printf 'services:\n  backend:\n    image: %s\n' "$IMAGE" > "$OVERRIDE"
  compose up -d db redis backend
}

site() {
  up
  in_box "bench set-config -g db_host db && bench set-config -gp db_port 3306 \
    && bench set-config -g redis_cache redis://redis:6379 && bench set-config -g redis_queue redis://redis:6379 \
    && bench set-config -g redis_socketio redis://redis:6379"
  local admin; admin=$(head -c 18 /dev/urandom | base64 | tr -d '/+=')
  in_box "bench new-site procurement.test --force --db-root-password procurement-test-only --admin-password '$admin' \
    --mariadb-user-host-login-scope='%' --install-app erpnext --install-app hrms --install-app lotus_farm"
  in_box "bench --site procurement.test set-config mute_emails 1 && bench --site procurement.test set-config pause_scheduler 1"
}

migrate() {
  in_box "bench --site procurement.test migrate --skip-search-index && bench --site procurement.test clear-cache"
}

run() {
  local script="${1:?tên script, vd verify_purchase_flow}"; shift || true
  MSYS_NO_PATHCONV=1 docker exec -i -e LOTUS_PROCUREMENT_TEST_ONLY=1 "$PROJECT-backend-1" bash -lc \
    "cd $BENCH/sites && ../env/bin/python ../apps/lotus_farm/tests/integration/${script%.py}.py $*"
}

drop() { compose down -v; }

cmd="${1:-up}"; shift || true
"$cmd" "$@"

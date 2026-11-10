#!/usr/bin/env bash
# Spec 003: dựng site thử riêng `mua.test` trong bộ lotus-vps-test, chạy bằng mã của worktree này.
# Không đụng site `frontend` (chỉ đọc bản sao lưu của nó) và không chạy `bench build` (sites/assets dùng chung).
#
#   tools/test_site_mua.sh up        # tạo container lotus-003-test (nếu chưa có) và chạy nó
#   tools/test_site_mua.sh site      # tạo mua.test từ bản sao lưu mới nhất của frontend, rồi migrate
#   tools/test_site_mua.sh migrate   # migrate lại mua.test sau khi đổi schema
#   tools/test_site_mua.sh serve     # chạy web server của mua.test ở 127.0.0.1:8098
#   tools/test_site_mua.sh drop      # xóa mua.test và container
set -euo pipefail

WT="${WT:-C:/code/lotus-003-mua-hang}"
NAME="${NAME:-lotus-003-test}"
SITE="${SITE:-mua.test}"
NET=lotus-vps-test_frappe_network
VOL=lotus-vps-test_sites
BENCH=/home/frappe/frappe-bench
SECRET_DIR="${SECRET_DIR:-$WT/.local}"   # mật khẩu admin của site thử; thư mục này bị git bỏ qua

in_box() { MSYS_NO_PATHCONV=1 docker exec -i "$NAME" bash -lc "cd $BENCH && $*"; }

up() {
  local image
  image=$(docker inspect lotus-vps-test-backend-1 --format '{{.Config.Image}}')
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
    MSYS_NO_PATHCONV=1 docker run -d --name "$NAME" --network "$NET" \
      -v "$VOL:$BENCH/sites" -v "$WT:$BENCH/apps/lotus_farm" \
      -p 127.0.0.1:8098:8000 --entrypoint sleep "$image" infinity >/dev/null
  fi
  docker start "$NAME" >/dev/null
  echo "container $NAME chạy từ $image"
}

site() {
  up
  local root backup
  root=$(docker exec lotus-vps-test-db-1 printenv MARIADB_ROOT_PASSWORD)
  # Đường dẫn tuyệt đối: bench chạy lệnh nạp từ thư mục sites/.
  backup=$(in_box "ls -1t $BENCH/sites/frontend/private/backups/*-frontend-database.sql.gz | head -1")
  [ -n "$backup" ] || { echo "không có bản sao lưu của frontend" >&2; exit 1; }
  mkdir -p "$SECRET_DIR"
  [ -f "$SECRET_DIR/mua-admin.secret" ] || head -c 18 /dev/urandom | base64 | tr -d '/+=' > "$SECRET_DIR/mua-admin.secret"
  local admin; admin=$(cat "$SECRET_DIR/mua-admin.secret")
  echo "tạo $SITE từ $backup"
  in_box "bench new-site $SITE --force --db-root-password '$root' --admin-password '$admin' --source-sql '$backup'" >/dev/null
  # Giữ các khóa cấu hình nghiệp vụ của frontend; tắt thư, tắt lịch chạy (worker dùng chung chạy mã cũ).
  in_box "python3 - <<'PY'
import json
src = json.load(open('sites/frontend/site_config.json'))
path = 'sites/$SITE/site_config.json'
dst = json.load(open(path))
for key in ('encryption_key', 'lotus_purchase_flow_company', 'lotus_purchase_flow_since', 'max_file_size'):
    if key in src:
        dst[key] = src[key]
dst.update(mute_emails=1, pause_scheduler=1, host_name='http://127.0.0.1:8098')
json.dump(dst, open(path, 'w'), indent=1)
PY"
  # The database refers to signature images and attachments: copy the files too (frontend is only read).
  in_box "mkdir -p sites/$SITE/private/files sites/$SITE/public/files && cp -an sites/frontend/private/files/. sites/$SITE/private/files/ && cp -an sites/frontend/public/files/. sites/$SITE/public/files/"
  migrate
}

migrate() {
  in_box "bench --site $SITE migrate --skip-search-index"
  in_box "bench --site $SITE clear-cache"
}

serve() {
  up
  MSYS_NO_PATHCONV=1 docker exec -d "$NAME" bash -lc "cd $BENCH && bench --site $SITE serve --port 8000 --noreload > /tmp/mua-serve.log 2>&1"
  echo "http://127.0.0.1:8098 (site $SITE)"
}

drop() {
  local root; root=$(docker exec lotus-vps-test-db-1 printenv MARIADB_ROOT_PASSWORD)
  in_box "bench drop-site $SITE --force --no-backup --db-root-password '$root'" || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}

"${1:-up}"

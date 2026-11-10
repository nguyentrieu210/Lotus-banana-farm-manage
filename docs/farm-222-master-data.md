# Nông trường Farm 222 Thuận Phú

## Khu và diện tích lô đã đối chiếu ngày 17/10/2026

64 lô chăm sóc có sẵn đã khớp toàn bộ diện tích bảng PDF/ảnh chủ vườn gửi.
Trường `Farm Block.farm_zone` (Khu) gán A–E cho đúng các lô; không tạo lô trùng
hoặc thay số diện tích nguồn. Trường Khu dùng để lọc/nhóm, độc lập với trường
khu tưới `irrigation_zone`.

| Khu | Lô chăm sóc | Diện tích ha |
|---|---:|---:|
| A | 13 | 45,45 |
| B | 12 | 42,44 |
| C | 14 | 45,57 |
| D | 12 | 42,43 |
| E | 13 | 39,27 |
| Tổng | 64 | 215,16 |

Nguồn đối chiếu được lưu tại `data/farm222-care-zones.json`, kèm SHA của PDF.

Đã nhập vào site `frontend`, công ty `Lotus Agritech`, mã vườn `LOTUS-222`:
Farm (diện tích danh nghĩa 222 ha), 64 Farm Block (tổng diện tích ghi trên PDF
215,16 ha) và 64 ranh lô `Farm Block Geometry` nháp, chưa xác minh GPS. Đây là
dữ liệu danh mục lấy từ bản đồ 222, không dùng seed demo và không bao gồm bản đồ
HTT 170 ha. Các số nguồn được lưu trong File riêng tư đính kèm Farm
(`farm-222-map-source.json`, `farm-222-import-report.json`).

## Thửa tưới và công cụ nhập cũ

Lô là đơn vị nhỏ nhất của vườn (spec 002). 210 thửa tưới (`Farm Plot`), ranh thửa
và các công cụ nhập một lần (`tools/import_farm_222.py`,
`tools/resolve_farm_222_parcels.py`, `tools/sync_farm222_zones.py`,
`tools/import_farm_222_work_catalog.py`) đã gỡ ở US7; dữ liệu thửa được lưu trữ ra
tệp trước khi xóa bảng (`lotus_farm/legacy_purge.py`). Mã thửa tưới chỉ còn trong
gói bản đồ nguồn, xem [lotus-map-draft-import.md](lotus-map-draft-import.md).

Đội, tổ, việc và cách trả của vườn lập ở **Việc hằng ngày → Thiết lập**, xem
[FIELD_REPORT.md](FIELD_REPORT.md).

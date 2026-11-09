# Implementation Plan: Dự thu chuối từ số liệu chăm sóc buồng hằng ngày

**Branch**: `nghien-cuu/du-thu` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-du-thu-cham-buong/spec.md`

## Summary

Đưa số liệu chăm sóc buồng thật vào dự thu. Tổ báo hằng ngày theo lô trên màn báo cáo hiện có; đội trưởng xác nhận theo ngày; số đã xác nhận được ghi vào sổ buồng theo lô (`Lotus Bunch Event`). Toàn bộ chỉ quản lý đến lô, không dùng thửa tưới. Một engine duy nhất tính dự thu theo dòng chảy buồng của từng lô: đã cắt bắp theo màu, đã chích chờ cắt, phần còn lại theo số cây. Sổ cắt bắp 593 buồng được nhập làm đầu kỳ. Các cách tính dự thu khác được gỡ sau khi engine mới chạy đúng.

## Technical Context

**Language/Version**: Python 3.14 (backend), JavaScript ES2022 với Vue 3 (frontend)

**Primary Dependencies**: Frappe/ERPNext v16, app `lotus_farm`; Vue 3, Vant 4 (điện thoại), shadcn-vue trên reka-ui (máy tính)

**Storage**: MariaDB 11.8 qua DocType Frappe

**Testing**: `node --test` (frontend, mount bằng happy-dom), unit test Python cho module thuần, integration trong `tests/integration` chạy bằng bench

**Target Platform**: Web máy tính và PWA điện thoại, máy chủ Docker

**Project Type**: Ứng dụng web

**Performance Goals**: Mở màn dự thu toàn vườn dưới 3 giây với 64 lô và khoảng 50.000 bản ghi một năm; lưu báo cáo một lô dưới 1 giây

**Constraints**: Dùng chung báo cáo ngày, không nhập hai nơi; chưa cần offline; không sửa quy tắc tiền khoán

**Scale/Scope**: 64 lô, 530.373 cây, khoảng 10 tổ, khoảng 13.000 đến 25.000 buồng cắt bắp một tháng lúc cao điểm

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Số thực, không suy diễn | Đạt. Mỗi dòng dự thu có nguồn và mức tin cậy; tuổi cây ghi rõ ước tính theo khu |
| II. Một nguồn sự thật | Đạt khi hoàn tất, có một ngoại lệ về tạo bảng mới (xem Complexity Tracking). Giai đoạn chuyển tiếp còn engine cũ, được gỡ ở phase cuối (FR-022) |
| III. Truy vết và kiểm soát | Đạt. Dùng bộ tham số đã có phiên bản; xác nhận theo ngày; sửa có lý do |
| IV. Quy tắc tách riêng, có kiểm thử | Đạt. Engine là module thuần |
| V. Giao diện theo chuẩn chung | Đạt. Mở rộng màn hiện có |
| Ràng buộc vận hành | Đạt. Nhập sổ cắt bắp có xem trước, chạy lại không trùng |

Đánh giá lại sau Phase 1: không phát sinh vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/001-du-thu-cham-buong/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md             # do /speckit-tasks tạo
```

### Source Code (repository root)

```text
lotus_farm/
├── bunch_flow_rules.py        # mới: tính dòng chảy buồng, module thuần
├── bunch_forecast_engine.py   # mới: dự thu theo tầng, module thuần
├── bunch_posting.py           # mới: xác nhận, ghi sổ buồng
├── bunch_opening_import.py    # mới: đọc sổ cắt bắp, xem trước, nhập
├── forecast_snapshot.py       # mới: chốt bản dự thu, đối chiếu thực tế
├── block_forecast.py          # sửa: API board trả dự thu theo tầng
├── block_forecast_engine.py   # giữ: tính phần theo số cây
├── field_report.py            # sửa: xác nhận theo ngày, việc mới
├── field_report_rules.py      # sửa: trần, số nguyên, công đoạn mới
├── field_report_seed.py       # sửa: việc chọn chồi, thu hoạch
└── lotus_farm/doctype/
    ├── lotus_work_entry/      # sửa: thêm trường
    ├── lotus_bunch_event/     # mới: sổ buồng theo lô
    └── lotus_forecast_snapshot/ # mới

frontend/src/
├── BlockForecastApp.vue       # sửa: dự thu theo tầng, truy nguồn
├── WorkMobile.vue, components/field/  # sửa: nhập và xác nhận
└── components/field/WorkBunchConfirm.vue  # mới

tests/integration/verify_bunch_forecast.py  # mới
```

**Structure Decision**: Giữ cấu trúc một app Frappe và một frontend hiện có.

## Complexity Tracking

| Vi phạm | Vì sao cần | Phương án đơn giản hơn bị loại vì |
|---|---|---|
| Tạo bảng sổ buồng mới thay vì dùng `Bunch Operation` và các bảng liên quan | Chủ vườn chỉ quản lý đến lô; các bảng cũ bắt buộc có thửa và vụ | Gắn vào thửa lớn nhất trái quyết định; nới kiểm tra sửa nhiều chỗ dùng chung. Các bảng cũ chưa có dữ liệu |
| Ghi hai bước: báo cáo ngày rồi sổ buồng | Báo cáo ngày gắn với công và tiền khoán; sổ buồng gom cả số đầu kỳ và buồng loại | Dự thu đọc thẳng báo cáo ngày thì không có chỗ cho số đầu kỳ và buồng loại |

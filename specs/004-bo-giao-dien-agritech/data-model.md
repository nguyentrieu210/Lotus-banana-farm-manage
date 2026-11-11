# Data Model: bộ giao diện Lotus

Không có bảng dữ liệu mới. Các "thực thể" dưới đây là dữ liệu giao diện: token CSS, lựa chọn của người dùng lưu trên máy, và các bảng tra cứu thuần trong JS.

## Giá trị nền (token)

- **Nơi lưu**: `frontend/src/lotus-tokens.css`, biến CSS `--lotus-*`.
- **Tầng**:
  - Dải gốc `--lotus-<họ>-<bậc>`: họ `primary`, `neutral`, `success`, `warning`, `danger`, `info`, `earth`; bậc 50–900, `neutral` thêm 0, 25, 950. Cùng giá trị ở mọi chế độ.
  - Ngữ nghĩa: bề mặt (`page`, `surface`, `raised`, `sunken`, `sidebar`, `soft`, `hover`, `active`, `selected`, `topbar`, `topbar-end`), chữ (`text`, `text-strong`, `text-secondary`, `muted`, `subtle`, `disabled`, `link`), viền (`border-subtle`, `border`, `border-strong`, `border-control`, `focus-ring`), tông `--lotus-tone-<neutral|primary|success|warning|danger|info>-<solid|on|soft|text|border>`, trạng thái lô `--lotus-lot-<state>[-on]`, biểu đồ `--lotus-chart-1..8`, `--lotus-seq-1..7`, `--lotus-div-1..7`.
  - Thành phần: `--lotus-control-*`, `--lotus-table-*`, `--lotus-chip-*`, `--lotus-card-*`, `--lotus-touch*`.
- **Ràng buộc**:
  - Giá trị màu là hex hoặc `rgb()`.
  - Mọi tên cũ còn định nghĩa.
  - `--lotus-primary-600:#c43224`, `--lotus-primary:var(--lotus-primary-600)` và `--primary:5 69% 45%` giữ nguyên (test cũ khóa).
  - Chế độ và mật độ chỉ ghi đè tên đã có ở `:root`.

## Chế độ hiển thị và mật độ

| Trường | Giá trị | Khóa lưu | Mặc định |
|---|---|---|---|
| theme | `light`, `dark` | `lotus-theme` (giữ từ trước) | chưa chọn: máy tính sáng; điện thoại theo máy |
| outdoor | `1`, `0` | `lotus-outdoor` (mới) | `0` |
| density | `compact`, `comfortable` | `lotus-desktop-density` (giữ từ trước) | `compact` |

- Trên `<html>`: lớp `.dark` hoặc `.lotus-outdoor` (không bao giờ cả hai), `data-theme`, `data-mode`, `data-density`, `color-scheme`.
- Máy tính không dùng ngoài trời.
- Đổi ở tab khác thì tab này đổi theo (sự kiện `storage`).

## Trạng thái nghiệp vụ (`ui-status.js`)

- **Loại** (23): `draft`, `pending`, `to_sign`, `waiting`, `sent`, `in_progress`, `partial`, `approved`, `done`, `active`, `returned`, `reopened`, `cancelled`, `locked`, `due`, `overdue`, `quarantine`, `warning`, `critical`, `present`, `absent`, `half_day`, `on_leave`. Mỗi loại có `label`, `tone`, `icon`.
- **Mã gốc → loại**: khoảng 80 mã ERPNext/HRMS/Lotus (`Draft`, `Submitted`, `To Receive`, `Rework`, `Voided`, `0/1/2`…). Mã lạ: không loại, tông trung tính, không biểu tượng.
- **Nhãn**: nhãn của nơi gọi (thường là `stateLabel(code)`) nếu khác mã gốc, nếu không thì nhãn của loại, cuối cùng là chính mã.
- **Hạn** (`dueState`): `upcoming`, `due` (hôm nay hoặc trong `soon` ngày), `overdue`, tính theo ngày lịch.

## Màu dây (`ribbon-colors.js`)

- **Màu gốc** (7): `DO` Đỏ, `TRANG` Trắng, `TIM` Tím, `CAM` Cam, `DEN` Đen, `XANH_DUONG` Xanh dương, `XANH_LA` Xanh lá. Mỗi màu một token `--lotus-ribbon-*`.
- **Mã ghép**: hai màu nối bằng `_` (`XANH_LA_DO`), hiện nửa mỗi màu. Tên tiếng Việt gõ tay cũng đọc được.
- Mã lạ: không màu (trong suốt), không nhãn.

## Trạng thái lô (`lot-states.js`)

| Trạng thái | Nhãn | Biểu tượng |
|---|---|---|
| `empty` | Chưa nhập | (không; viền nét đứt) |
| `entered` | Đã nhập, chưa gửi | `edit` |
| `sent` | Đã gửi | `send` |
| `confirmed` | Đã xác nhận | `tick` |
| `ok` | Chưa đến hạn | `tick` |
| `due` | Đến hạn | `clock` |
| `overdue` | Quá hạn | `alert` |
| `quarantine` | Đang cách ly | `shield` (nền gạch chéo) |

- **Chỉ tiêu tô lưới lô**:
  - `report` (Báo cáo hôm nay): empty, entered, sent, confirmed.
  - `care` (Đến hạn chăm sóc): ok, due, overdue.
  - `harvest` (Đến tuổi thu): empty, ok, due.
  - `quarantine` (Cách ly thuốc): ok, quarantine.
- **Khu**: chữ đầu mã lô (`A5` → A). Khu A–F dùng sáu màu bản đồ cố định. Mã lô sắp tự nhiên (A2 trước A10).

## Tuần ISO (`agri-format.js`)

- `{year, week}`; tuần bắt đầu thứ Hai; tuần 1 chứa thứ Năm đầu năm; 2026 có 53 tuần.
- Khóa `YYYY-Www` cho bản đồ theo tuần (tuần thu, màu dây cắt trong tuần, dự thu).

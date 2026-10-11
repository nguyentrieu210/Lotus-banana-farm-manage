# Giao việc nhanh trên điện thoại — Lotus

## Mục tiêu

Một màn hình cho đội trưởng trên điện thoại, **không cần mở biểu mẫu Frappe**. Chọn nông trường, ngày, tổ, vị trí **lô HOẶC thửa**, loại việc, số lượng. Có thể thêm nhiều công việc trong một lần. Xem trước từng thửa rồi xác nhận.

**Đường dẫn sau khi triển khai, build và migrate: `/lotus/giao-viec`.** Phải đăng nhập Frappe và có vai trò Lotus Farm Manager với quyền của nông trường. Không có chế độ gửi phiếu ẩn danh.

### Quy tắc lô / thửa

- Chọn **thửa**: backend tự lấy lô cha + một vụ cây đang hoạt động; không bắt chọn thêm cấp cha.
- Chọn **lô**: vì Daily Work Plan Line vẫn yêu cầu Thửa, hệ thống **chia số lượng theo diện tích các thửa đang hoạt động**. Ví dụ lô 80 ha có bốn thửa bằng nhau, 800 buồng → 200 buồng/thửa. **Có màn hình xem trước** và chưa ghi dữ liệu trước khi bấm “Xác nhận giao việc”.
- Không tự đoán nếu thửa có 0/nhiều vụ đang hoạt động hoặc vụ chồi có 0/nhiều đợt chồi đang áp dụng. Yêu cầu người quản lý chuẩn hóa dữ liệu.
- Nhiều công việc/nhiều vị trí: chỉ một tổ nhận việc trong một lượt giao. Nếu khác tổ, bấm giao lượt khác. Việc trùng cùng thửa/công việc trong một lượt sẽ gộp lượng; nếu đã giao cho cùng tổ trong ngày thì chặn tạo trùng.
- Định mức lao động trong `Work Type` dùng để lập kế hoạch, không phải danh sách công nhân. Không có công nhật/KPI/phiếu nghiệm thu nằm trong màn hình giao việc này.

## Dữ liệu thử nghiệm đầy đủ

**Không chạy tự động trên hệ thống thật**. Lệnh chỉ cho phép chạy khi site ERPNext v16 đã bật `allow_tests=true` và đăng nhập là Administrator.

```sh
# Trên site THỬ NGHIỆM đã cài ERPNext + lotus_farm:
bench --site lotus.test set-config allow_tests true
bench --site lotus.test migrate
bench --site lotus.test execute lotus_farm.mobile_demo_seed.seed
# Nếu site thử có nhiều công ty, chỉ rõ một công ty đã tồn tại:
bench --site lotus.test execute lotus_farm.mobile_demo_seed.seed --kwargs '{"company":"Tên công ty trên site thử"}'
# Sau khi build frontend:
npm ci --prefix apps/lotus_farm/frontend
npm run --prefix apps/lotus_farm/frontend build
# Truy cập https://HOST/lotus/giao-viec?farm=LOTUS-DEMO-222
```

Seed gắn nhãn rõ là **DỮ LIỆU MẪU**, gồm:

| Nhóm dữ liệu | Số lượng |
|---|---:|
| Nông trường Lotus 222 ha | 1 |
| Lô: A01 80 ha, A02 72 ha, A03 70 ha | 3 |
| Thửa: 4 thửa/lô | 12 |
| Vụ chuối hoạt động: 1 vụ/thửa | 12 |
| Tổ nhận việc | 4 |
| Loại việc: bao buồng, chống buồng, cắt bắp, cắt lá, cắt lá bệnh, phát cỏ, trồng dặm, bón phân | 8 |
| Phiếu kế hoạch có nhiều việc | 3 |
| Dòng kết quả thực tế mẫu hôm qua | 2 |
| Báo cáo số công tổng ngày hôm qua | 1 |

Định mức 100 buồng/công, 80 cây/công… chỉ là **số minh họa để thử**. Không phải định mức đã duyệt của Lotus. Seed không thêm phiếu trả tiền, không thanh toán và không sửa dữ liệu thật.

Lệnh `seed` gọi lại trên một nông trường mẫu đã tồn tại sẽ báo `already_seeded` và không ghi đè.

## Kiểm thử

- `python -m unittest discover -s tests -v` (chia khối lượng theo diện tích và bảo toàn tổng).
- `npm run --prefix frontend test` (form nhập theo lô hoặc thửa).
- `npm run --prefix frontend build` (có cả `index.html` và `assign.html` trong manifest).
- `bench --site lotus.test run-tests --module lotus_farm.tests.test_brd` (site test seed, tạo kế hoạch thực, chặn trùng và chặn thửa sai farm).

## Giới hạn còn lại

- Seed chỉ có trên site thử; **chưa nạp bất kỳ dữ liệu mẫu nào lên site mà người dùng đang mở qua tunnel**.
- UI hiện tại giao **một tổ mỗi lượt**, nhưng thêm nhiều công việc và nhiều lô/thửa mỗi lượt.
- Nếu một lô có nhiều thửa mà thực tế muốn chia chỉ tiêu không theo diện tích, cần sửa số từng thửa trong kế hoạch sau khi tạo hoặc làm tính năng phân bổ thủ công trước khi giao. **Không dùng phân bổ diện tích làm xác nhận sản lượng thực tế.**
- Việc gửi phiếu cần có mạng; chưa cung cấp hàng chờ giao việc ngoại tuyến.
- Các dạng phiếu công nhật và nghiệm thu tiền khoán thuộc những luồng riêng, không xuất hiện trên màn hình giao việc.

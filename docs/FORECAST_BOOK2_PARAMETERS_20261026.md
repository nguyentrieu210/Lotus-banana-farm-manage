# Đối chiếu thông số Excel Lotus 26/10/2026

## Nguồn
- `Lotus_Lich_Tro_2_Vu_Don_Gia_Nhan_Cong_2026_2028.xlsx`
- Các sheet `TS_DU_TRO`, `DM_THONG_SO`, `DM_CONG_VIEC`, `DATA_LO` và `DU_LIEU_CAN_CHOT`.
- Tham chiếu chéo bản `Lotus_BAN_DE_HIEU_Ke_Hoach_2026_2028.xlsx`, sheet `07_THONG_SO`.

## Đã triển khai trong nhánh này
1. `lotus_farm/forecast_book2_reference.py` khai báo 16 giá trị tương ứng đúng 16 trường mà bộ dự thu chặt mẹ hiện có thể tính, theo nguồn Excel 26/10.
2. `lotus_farm.cut_forecast.board` trả về đề xuất, chênh lệch với bộ thông số **đã duyệt** và nhóm 23 thông số cần tích hợp ở bước tiếp theo.
3. Trên `/lotus/forecast` → **Thông số & lần nhập** có thể đọc chênh lệch; chọn **Nạp vào biểu mẫu (chưa lưu)** chỉ sửa state phía trình duyệt. Người quản lý phải kiểm tra và bấm **Lưu thành phiên bản mới** theo luồng có sẵn để áp dụng.
4. Không cập nhật `DEFAULTS` của động cơ cũ, không sửa hồ sơ đã duyệt, không thay dữ liệu lịch sử, không tự phát hành `Harvest Forecast` hoặc bút toán kế toán.

## 16 giá trị có thể nạp vào mô hình hiện tại
- Chặt mẹ lần 2 → trổ lần đầu **180 ngày** (giả định; code cũ 120).
- Cửa sổ trổ 4 đợt **17/40/25/18**; mỗi đợt 30 ngày, bước 30 ngày, ngày đại diện +14.
- Trổ → chích **+5 ngày** (giả định; thao tác thực tế theo trạng thái bắp).
- Chích → cắt bắp **+16 ngày** (quy trình tính ngày chích là ngày 1; code cũ +15).
- Cắt bắp → thu **+65 ngày** (tạm chốt, có thể dời theo đo trái).
- Cắt bắp/cây: 90%; thu/cắt: 97%; đóng gói/thu: 98%; kg thành phẩm/buồng đạt của vụ 2: 20.
- Chồi trên mỗi cây mẹ **giữ 1** trong mô hình hiện tại, do đầu vào là số cây hiện hữu; **không** âm thầm nhân 0,97.

## Các thông số còn thiếu công năng
- Chọn chồi → trổ khoảng 6 tháng; chọn chồi → dự thu vụ kế tiếp 8 tháng; phải gắn ngày theo **vụ, lô và đợt chồi**, không tính từ ngày chặt mẹ.
- Khối lượng thành phẩm 19/20/19 kg/buồng theo vụ 1/2/3+; động cơ chặt mẹ hiện chỉ có một `kg_per_bunch` và chưa biết `cycle_no`.
- Dự phóng chồi thế hệ kế tiếp 97%, **chỉ** áp khi dự báo từ cây mẹ; không nhân lại khi đã có cây kiểm kê.
- Lặt hoa sau chích +7/+10/+13; phun buồng 4 lần; đo trái từ thu-10 đến thu-7; chống đổ +3 tới +10 ngày, mục tiêu +5.
- Công nhật 290.000 VND/ngày; phụ cấp buồng có điều kiện 20.000 VND; nghỉ dự phòng 10%; lịch 6 ngày/tuần. **Không cộng giá khoán với công nhật.**
- Tần suất Book2: kiểm tra béc 2 lần/tháng, cắt lá 1 lần/tháng, làm cỏ gốc 2 tháng/lần, bón hóa học 1 lần/tháng, drone 2 lần/tháng, chặt mẹ lần 2 sau lần 1 2 tháng lịch.
- Danh mục 43 công việc, định mức và 64 lô phải đồng bộ bằng mã công việc và mã lô sau khi đối chiếu dữ liệu trùng. Chưa tạo/sửa master data trong nhánh này.

## Lưu ý sai lệch
**Mốc chọn chồi +6 tháng đến trổ** khác hoàn toàn **chặt mẹ lần 2 +180 ngày đến trổ** dù cùng độ dài ước tính. Không chuyển thành cùng một trường hoặc mặc định có thể cộng dồn.

**Tỷ lệ trổ 17/40/25/18** chỉ chia lượng cây trổ thành bốn đợt, không nhân thêm một đường cong thu tháng khác.

**Ngày chọn chồi 01/11/2026 của khu A → dự thu vụ chồi từ 07/2027** là kịch bản cấp khu, không phải ngày đã đo được cho toàn bộ 13 lô khu A.

## Chưa làm trong nhánh này
- Đã bổ sung chế độ **mô phỏng Book2 4 đợt** (30 ngày/đợt) trên trang `plan-norm`; chế độ mô phỏng 3 đợt cũ vẫn được giữ tương thích trong API. Chưa hợp nhất các bộ tính dự thu cũ hoặc phát hành `Harvest Forecast` từ kết quả mô phỏng.
- Chưa thay schema nhật ký chặt mẹ để lưu `farm_block`/`crop_cycle`/`cohort`.
- Mô phỏng kế hoạch Book2 giờ tính **số công, công định biên và 2 kịch bản tiền công nhật/khoán riêng biệt** theo Work Type đã có năng suất. CHƯA tự tạo `Daily Work Plan`, lịch làm theo mốc chích bắp/thu hoạch, hay yêu cầu xuất vật tư từ dự thu.
- Chưa chạy migrate, chưa đổi cấu hình live.

## Kiểm thử
`python -m unittest tests.test_forecast_book2_reference tests.test_cut_forecast`

### Cập nhật phần kế hoạch hiện có
- Backend `plan_norm.board` cung cấp `book2_plan_reference` read-only.
- Trên `/lotus/plan-norm` có tab **Đối chiếu Book2** (43 mã, tần suất, mã ERP tương ứng, năng suất; tránh tự ghi khi chưa được duyệt).
- Tab **Thử tính 36 tháng** dùng bốn đợt 17/40/25/18, bước 30 ngày khi chọn chế độ Book2; hiển thị số công định biên dự phòng và tiền công nhật dự kiến 290.000đ/công khi Work Type cho công nhật.
- Công nhật và công khoán là hai kịch bản độc lập, không cộng; phụ cấp buồng, thuốc và thưởng chuyên cần vẫn tính riêng theo điều kiện thực tế.
- Các bài test mới: `tests/test_plan_book2_reference.py` và `frontend/tests/plan-book2-simulation.test.js`.

Bước tiếp theo phải là bài kiểm tra đầu-cuối cho một lô cụ thể: cây hiện hữu → 4 đợt trổ → công chăm sóc → công nhật/vật tư → dự thu đã duyệt → đối chiếu thu thật.

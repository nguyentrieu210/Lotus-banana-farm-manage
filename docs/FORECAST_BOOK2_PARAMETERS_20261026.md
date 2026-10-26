# Lotus — Dự thu và kế hoạch theo LÔ/VỤ (Book2, 26/10/2026)

## Quyết định kiến trúc
Không sử dụng **nhật ký chặt cây mẹ lần 2** làm đầu vào tính toán nữa.
Đường `/lotus/forecast` dùng `BlockForecastApp.vue` và `lotus_farm.block_forecast.board`, không gọi các API nhập nhật ký, không đối chiếu khu→lô từ nhật ký.

Các tệp chạy luồng nhập nhật ký cũ (API, UI, mô phỏng và kiểm thử liên quan) đã được loại khỏi nhánh. **Ba DocType lịch sử** (`Lotus Cut Journal Entry`, `Lotus Cut Journal Import`, `Lotus Cut Forecast Profile`) chỉ còn **lưu trữ đọc**, bị ẩn khỏi Desk và khóa quyền ghi. Không tự xóa lịch sử trong cơ sở dữ liệu khi chưa xuất bản sao lưu kiểm chứng được.

## Nguồn dự thu chính
1. Theo từng **Farm Block (lô lớn)**: `lotus_tree_count` từ kiểm kê và `lotus_estimated_flowering_date` nếu có. Không lấy diện tích × mật độ để tự sinh số cây.
2. Nếu lô có **Plan Cohort đã duyệt**, dùng phiên bản mới nhất theo `(lô,mã đợt)` và **không cộng kiểm kê lô lần nữa**. Plan Cohort yêu cầu mã lô, vụ (nếu có), số cây/chồi/buồng, mốc `Shooting` (trổ) hoặc `Selection` (chọn chồi).
3. Plan Cohort dạng chọn chồi → bắt đầu trổ dự kiến sau **6 tháng lịch**; một lô có thể có nhiều đợt/vụ kế tiếp **được khai báo và duyệt riêng**. Không tự sinh cây vụ sau từ vụ hiện tại nếu chưa có số chồi.
4. Lô thiếu số cây hoặc ngày trổ thì báo **chưa có căn cứ**, không tự đặt số.
5. Tất cả đều là **dự phóng**, không biến thành `Harvest Forecast` phát hành hoặc tồn kho được phép bán.

### Công thức Book2 đang dùng
- Chia bốn đợt **17 / 40 / 25 / 18%** bằng ROUND Excel, phần còn lại ở đợt cuối; bước cách nhau **30 ngày**.
- Ngày mốc dự phóng là **ngày bắt đầu mỗi đợt trổ**, không dời +14 ngày vì mốc khu A 01/11 được khai là ngày bắt đầu và cần giữ lịch.
- Trổ → chích **+5 ngày**; chích → cắt bắp **+16 ngày**; cắt bắp → thu **+65 ngày**. Tổng trổ → thu: **86 ngày**.
- Buồng đạt cắt bắp: **90%**; từ cắt bắp tới thu: **97%**; đạt đóng gói: **98%**. Trọng lượng thành phẩm: vụ 1 **19 kg**, vụ 2 **20 kg**, vụ 3+ **19 kg/buồng đóng gói**. Đây là giả định kỹ thuật từ Book2, cần UAT ngoài vườn.
- Ví dụ đợt cây **chọn chồi 01/11/2026** → bắt đầu trổ **01/05/2027** → thu đợt trổ đầu **26/07/2027**. Các đợt tiếp theo dịch 30 ngày.
- Không áp tỷ lệ 97% tạo chồi vào số cây đã kiểm kê; số lượng đầu vào phải có nguồn theo lô.

## Kế hoạch công việc
- `lotus_farm.block_forecast.preview_care_plan` sinh lịch cho một cửa sổ tối đa 46 ngày, theo **lô/vụ/đợt**.
- Có chích, chống đổ (chỉ cảnh báo khảo sát), vén lá, lặt hoa **3 lần**, phun buồng **4 lần**, cắt bắp, cột dây, xốp, bao buồng, đo trái `thu-10..thu-7`, cắt/vác và vận chuyển buồng.
- Cùng ngày/lô/mã công việc chỉ có một dòng, nguồn là ID đợt trổ. Không lấy nhật ký làm căn cứ.
- Chỉ cho tạo `Daily Work Plan` **nháp (`docstatus=0`)** từ một ngày/lô do quản lý chủ động chọn. Không tự submit/duyệt, chấm công, giữ vật tư, mua/xuất kho hoặc ghi kế toán.
- Phải có `Work Type.work_code` duy nhất, cho phép công nhật, năng suất/công dương, UOM khớp.
- Phun, cột dây, xốp và bao buồng yêu cầu `Material Norm Profile` **Approved**, còn hiệu lực, có dòng và quy đổi hợp lệ. `DINH_MUC_VT_CV` Book2 chỉ là số liệu tham khảo, không được tự nhập/phê duyệt phác đồ.
- Công việc chống đổ **CV021** bắt buộc khảo sát chính xác số cây cần chống. Không tự lập nháp bằng toàn bộ số cây trổ.
- `Daily Work Plan Line.lotus_forecast_sources` lưu mã đợt/vụ/các đợt trổ để truy nguồn; fingerprint kiểm tra dữ liệu đầu vào không đổi khi xác nhận.

## Kế hoạch & định mức hiện có
- Tab `/lotus/plan-norm` đối chiếu danh mục 43 mã công việc CV001–CV043, năng suất, hình thức công và định mức.
- Mô phỏng 36 tháng có chế độ 4 đợt. Chi phí công nhật **290.000 VND/công** và chi phí khoán **là hai kịch bản**, không cộng cả hai. Dự phòng vắng mặt 10% chỉ cho định biên, không tự làm tăng lương thực trả.
- Chức năng này không tự tạo chứng từ. Màn dự thu theo lô mới là nguồn xem lịch bốn đợt phục vụ tạo nháp.

## Kiểm thử, triển khai và giới hạn
- Unit tests: `tests/test_block_forecast_engine.py` và `tests/test_block_forecast_integration.py`; frontend mount `frontend/tests/block-forecast.mount.test.js`.
- Thêm `lotus_forecast_sources` vào `Daily Work Plan Line` và ẩn quyền ghi của DocType cũ cần **bench migrate** trước vận hành.
- Phải kiểm thử trên **bản sao ERPNext**, đặc biệt lô A, số cây thực, số chồi tương ứng, mốc trổ, Work Type/định mức, trùng kế hoạch ngày, quyền duyệt và sản lượng.
- Không tự gán mốc trổ A cho tất cả lô/khu chưa có dữ liệu; không phát hành phiếu dự thu bán hàng chỉ từ mô phỏng.
- Chưa merge hoặc deploy production khi chưa nghiệm thu site/migrate và dự phòng rollback.

Nguồn tham chiếu: `Lotus_Lich_Tro_2_Vu_Don_Gia_Nhan_Cong_2026_2028.xlsx`, `TS_DU_TRO`, `DM_CONG_VIEC`, `TS_NHAN_LUC`, `DINH_MUC_VT_CV`.

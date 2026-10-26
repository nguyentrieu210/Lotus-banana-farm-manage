# Audit bộ dự thu Lotus theo lô/vụ – 26/10/2026

## Nguồn và quyết định không quay lại nhật ký chặt cây mẹ
Nguồn chính: `Lotus_Lich_Tro_2_Vu_Don_Gia_Nhan_Cong_2026_2028.xlsx` (DM_THONG_SO, TS_DU_TRO, DM_CONG_VIEC, KIEM_TRA_MO_HINH), `Lotus_Master_Data_Ap_Dung_Book2_2026-10-26.xlsx`.
Bộ máy hiện hành: `lotus_farm.block_forecast_engine`; đầu vào `Farm Block` hoặc `Plan Cohort` Approved theo lô/vụ. Không đọc `Lotus Cut Journal Entry` hoặc suy từ ngày chặt mẹ.

## Kiểm kê dữ liệu
- Vườn 222: 64 lô lớn (A13+B12+C14+D12+E13), diện tích lô 215,16 ha; D13 lớn đã loại khỏi tập dữ liệu sản xuất; mã tưới D13 ở D12 không xóa.
- **Quyết định vận hành mới:** sử dụng **530.373 cây trong bộ chốt đợt trước** làm số cây gốc chính thức để chạy dự thu/kế hoạch theo từng lô. Bộ số liệu có nguồn là Master Excel đợt trước (nguồn cây 518.296 và điều chỉnh mô hình ở thời điểm chốt). Không nhân thêm +2,33% lần thứ hai; không tự đổi số cây đã chốt. Trạng thái sử dụng là `Planning Baseline`, không cần xác nhận kiểm đếm lại để lập kế hoạch.
- Bản phân bổ trổ 17/40/25/18 cho **vụ chồi 2+**. Nếu không có mốc/cơ sở sản lượng vụ 1, không suy từ tỷ lệ vụ chồi ra sản lượng vụ 1 như số liệu đã xác nhận.

## Bảng thông số dự thu (bản tham chiếu Book2)
| Thông số | Giá trị | Phân loại / lưu ý |
|---|---:|---|
| 4 đợt trổ | 17/40/25/18% | Chia một lần, không nhân thêm đường cong thu |
| Cửa sổ/bước | 30/30 ngày | Trải sản lượng từng đợt lên **30 ngày** bằng phân bổ số nguyên; chưa phải đường cong thực tế theo ngày |
| Chọn chồi → trổ | 6 tháng lịch | Không phải chặt cây mẹ → trổ |
| Trổ → chích | 5 ngày | Giả định kỹ thuật; quan sát trổ/chích thực tế mới dùng giao việc cứng |
| Chích → cắt bắp | 16 ngày | Ngày chích tính là ngày 1 của quy trình ngày 17 |
| Cắt bắp → thu | 65 ngày | Giả định; điều chỉnh theo đo trái và thu thực tế |
| Tỷ lệ trổ/cây hữu hiệu | 100% **TRẦN** | Thiếu tỷ lệ thực tế; profile Approved phải có nguồn kỹ thuật xác nhận |
| Cắt bắp / cây | 90% | Không đồng nghĩa tỷ lệ trổ hoặc chích; nếu lớn hơn số đã trổ thì giới hạn và cảnh báo |
| Cắt bắp / buồng đã trổ | 100% **TRẦN** | **Tách riêng** khi đầu vào là số buồng, không áp lại 90% trên cây |
| Thu / cắt bắp | 97% | Giả định Lotus |
| Buồng đạt đóng gói / buồng thu | 98% | Không phải phần trăm hao hụt kg |
| Thành phẩm / buồng vụ 1/2/3+ | 19/20/19 kg | Phải biết số vụ, không tự mặc định dữ liệu vụ chưa có |
| Kg thành phẩm/thùng | 13 kg | Chỉ xuất thùng tương đương; chưa phải số thùng đóng thực tế |
| Số thùng/container 40ft | 1320 | Chỉ tính cont lý thuyết; chưa chốt logistics |
| Hệ số chồi hữu hiệu | 97% tham khảo | **Không bao giờ nhân** vào cây/chồi đã kiểm kê hoặc có số thực |
| Ngày bắt đầu trổ khu A | 01/11/2026 (dự kiến) | Chỉ dùng nếu nguồn lô gắn mốc rõ, không ép tất cả lô trổ cùng ngày |

Một ví dụ: chọn chồi 01/11/2026 → trổ từ 01/05/2027 → thu từ 26/07/2027; mỗi đợt có cửa sổ thu kéo dài 30 ngày, không toàn bộ buồng thu vào 26/07.

## Vấn đề đã sửa trong mã
1. Không dồn 30 ngày trổ thành một ngày: bốn đợt 17/40/25/18 vẫn đúng tổng; `daily_rows` bảo toàn số cây, buồng trổ/cắt/thu/đóng; `monthly` cộng theo **ngày thu từng phần**, không ghi tất cả vào một tháng chỉ vì ngày đầu đợt.
2. Tách đơn vị nguồn: `Trees` và `Selected Suckers` dự phóng tỷ lệ trổ/cây rồi cắt; `Bunches` tại Shooting là số buồng và dùng hệ số cắt **trên buồng đã trổ**; không áp 90% trên cây lần hai. Bunches ở mốc Selection bị từ chối.
3. `Plan Cohort` mới có `forecast_distribution_mode`: `Four Waves` hoặc `Single Wave`; buồng tại ngày trổ mặc định một đợt. Chọn Single Wave cho đợt thực tế không phân bổ thêm bốn lần.
4. `Farm Block.forecast_count_source` mặc định `Planning Baseline`. Tất cả số cây hợp lệ đang lưu theo lô, kể cả trạng thái nguồn cũ `Unverified`/`Source File`/`Estimated`, được sử dụng như **số cây gốc đã chốt** để lập kế hoạch khi bộ thông số và mốc trổ hợp lệ. `Census Confirmed` chỉ dành cho bản ghi có nguồn kiểm đếm thực địa riêng; không cần chuyển trường nguồn lịch sử để tính kế hoạch.
5. `Lotus Block Forecast Profile` được tạo mới với 22 tham số versioned, cấp vườn hoặc lô, thời hạn hiệu lực, nguồn/căn cứ duyệt. Profile đã duyệt bất biến; profile mới không được chồng thời gian cùng vườn/lô. Không có Approved thì dự thu chỉ là **Unapproved Book2 scenario** và không cho tạo kế hoạch.
6. Có kiểm tra `Crop Cycle.cycle_no`; nếu thiếu vụ thì trọng lượng 19/20 chỉ là giả định hiển thị và **không cho lập phiếu nháp**.
7. `Bunch Operation` Submitted trổ/chích/cắt bắp hiển thị riêng làm số thực tế đã ghi nhận; KHÔNG nhân vào dự thu lần hai, không tự nhận thuộc một đợt nếu chưa có quan hệ nguồn xác thực.
8. Phân bổ công việc theo ngày, 3 lần lặt hoa và 4 lần phun buồng, đo trái `thu-10` (cửa sổ đến `thu-7`), thu/cắt buồng. Phun lần 4 theo buồng đã cắt bắp, không theo toàn bộ cây.
9. Nhu cầu công/ngày, công định biên cộng dự phòng vắng 10%, công nhật 290.000 đ/ngày chỉ là **kịch bản tham chiếu**, không kết chuyển sang lương/giá thành. Công khoán là một phương án khác, không cộng vào công nhật.
10. Vật tư chỉ lấy profile định mức `Approved` còn hiệu lực; thiếu liều thì không tự tạo kế hoạch công việc đó, không mua hoặc xuất kho; chống đổ chờ khảo sát thực tế.
11. Chỉ tạo phiếu `Daily Work Plan` **Draft**, một lô/ngày với fingerprint; chỉ lấy dòng đủ điều kiện, trả danh sách mã bị bỏ qua; không tự duyệt. Dòng mới là cấp lô **không nhập Crop Cycle trực tiếp nếu không có Farm Plot**, nhưng lưu vụ trong `lotus_forecast_sources` để tuân thủ validator hiện tại.

## Các phần CHƯA thể coi là hoàn tất
- Tỷ lệ trổ thực tế chưa được nghiệm thu; mặc định 100% là trần và phải gắn nhãn giả định.
- Số cây bộ trước đã được **chốt làm đầu vào vận hành**. Chỉ yêu cầu bổ sung ngày trổ/chọn chồi của lô nếu chưa có mốc; không lấy việc chưa có biên bản kiểm đếm mới làm lý do chặn kế hoạch. Không cộng lặp 2,33% vào bộ đã chốt.
- Liều vật tư/thuốc, năng suất của 19 công việc và lịch phun theo kỹ thuật phải được người phụ trách xác nhận. Hệ thống không được chế ra nguồn còn thiếu.
- Chưa có liên kết duy nhất từng `Bunch Operation` đến `Plan Cohort` dự báo, nên actuals chỉ hiển thị riêng, không tự hiệu chỉnh forecast hay forecast snapshot đã phát hành.
- Phân bổ đều 30 ngày là giả định vận hành để tránh đỉnh công ảo; khi có số trổ theo tuần/ngày thực tế phải thay bằng phân bố đo đếm.
- `/forecast-onedrive` còn để tra cứu kịch bản cũ, được gắn nhãn **Dự thu tham khảo cũ**. `/forecast` là màn chính. `Harvest Forecast` Released là chứng từ riêng, chưa tự phát hành từ số dự kiến.
- Chưa nghiệm thu Frappe site UAT và migration; cần backup, `bench migrate` trên clone, phân quyền, phiếu nháp, form profile, xác nhận UOM, rồi mới merge/deploy live.

## Kiểm thử tối thiểu
```sh
python -m unittest discover -s tests -p 'test_block*.py'
cd frontend
node --test tests/block-forecast.mount.test.js tests/plan-book2-simulation.test.js tests/plan-norm-engine.test.js tests/plan-norm-safety.test.js
npm run build
```

## Quyết định tiếp nhận số cây cũ làm số cây chốt (26/10/2026)
- Giá trị `Farm Block.lotus_tree_count` từ dữ liệu đợt trước là **số cây chính thức phục vụ dự thu và kế hoạch**, không cần phân loại “chưa kiểm kê”. Nếu có số cây hợp lệ, bộ dự thu trả trạng thái `Planning Baseline`, cho phép sinh phiếu kế hoạch nháp khi đáp ứng các điều kiện thông số/Work Type/vật tư.
- Giao diện Vườn & lô và Dự thu dùng nhãn **“Số cây gốc đã chốt”**, không hiển thị số cây đợt trước như một vấn đề thiếu kiểm kê.
- Thông tin nguồn/giá trị cũ vẫn được bảo tồn, tránh tạo bản ghi sai rằng đã đếm thực địa. Chỉ khi số cây hoàn toàn trống/0 mới yêu cầu dữ liệu nguồn theo lô.

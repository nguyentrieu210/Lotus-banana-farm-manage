# Research: Làm lại chăm sóc vườn, chăm sóc buồng, thu hoạch, báo cáo và dự thu

Hiện trạng code kiểm ngày 10/11/2026 trên nhánh tách từ main `df7bd70`.

## R1. Dòng sổ lô dựng trên bảng nào

- **Decision**: Dùng `Lotus Work Entry` làm dòng sổ lô. Mỗi dòng là một việc ở một lô, của một tổ, trong một ngày. Với việc buồng, mỗi dòng còn tách theo đợt màu và lý do hủy. Bỏ bắt buộc `assignment`. Chuyển phần sổ của `Lotus Bunch Event` vào: trạng thái, khóa nguồn, vụ, lý do và giai đoạn hủy, kg, diện tích, hủy dòng có lý do.
- **Rationale**: `Lotus Work Entry` đã có lô, việc, số lượng, màu dây, cờ xong lô, người làm theo buổi, vật tư kèm thời gian cách ly và phiếu xuất kho. Bảng này cũng đã nối với tiền khoán (`month_piece`), bảng lương (`hr_period`), chi phí công theo lô (`finance/payroll._work_rows`) và nhãn "Khoán" ở chấm công. Engine dự thu nhận các dòng đã chuẩn hóa, nên chỉ phải đổi phần nạp dữ liệu.
- **Alternatives**:
  - Mở rộng `Lotus Bunch Event` cho mọi việc: phải chuyển toàn bộ tiền khoán, buổi công, vật tư, cách ly sang bảng đó, đụng vào bảng lương.
  - Giữ hai bảng như spec 001 (xác nhận Work Entry rồi ghi sang Bunch Event): hai nơi lưu cùng một số, trái FR-001 và FR-003.

## R2. Báo cáo ngày của tổ

- **Decision**: Thêm bảng `Lotus Daily Report`, duy nhất theo vườn, tổ và ngày. Bảng này giữ:
  - trạng thái Nháp → Đã gửi → Đã xác nhận, mở lại phải có lý do;
  - người nhập, nhập hộ hay không, nguồn (điện thoại, phiếu giấy, ảnh);
  - ảnh phiếu và bản máy đọc;
  - người và giờ xác nhận.

  Mỗi dòng sổ lô trỏ về báo cáo của nó.
- **Rationale**: FR-005, FR-006, FR-009 và FR-036 cần trạng thái, tệp và người xác nhận ở cấp tổ-ngày.
- **Quy tắc xác nhận**: người xác nhận không được là người nhập. Đội trưởng nhập hộ thì quản lý vườn xác nhận.
- **Alternatives**: Gom theo khóa tổ-ngày, không có bảng, như spec 001. Cách này không có chỗ giữ ảnh, bản máy đọc và trạng thái đã gửi.

## R3. Người làm theo buổi

- **Decision**: Mặc định người làm là người của tổ có lượt máy chấm công buổi đó, giữ như hiện nay. Không có lượt máy thì không ghi được (giữ luật cũ).
  - Một người được có tên ở nhiều dòng trong cùng một buổi. Buổi đó chia cho các dòng: cùng việc thì chia theo khối lượng, khác việc thì chia đều. Tổng của một người trong một buổi luôn bằng 1.
  - `Lotus Work Session` thêm `weight`. Khóa duy nhất đổi từ người × ngày × buổi thành người × ngày × buổi × dòng.
- **Rationale**: Một tổ thường làm một việc trên nhiều lô trong một buổi. Luật cũ "mỗi buổi chỉ thuộc một phiếu" buộc gán mỗi người vào một lô: hoặc sai công theo lô, hoặc thêm thao tác. Chia theo trọng số thì tổng công và tổng tiền không đổi.
- **Hệ quả**: `split_by_sessions`, `month_piece` và `work_rows` cộng trọng số thay vì đếm dòng. Đây là thay đổi cách chia tiền và công, cần chủ vườn biết khi duyệt tasks.

## R4. Vòng chăm sóc và giao việc

- **Decision**: Dùng `Work Schedule Rule`, bảng này đã có phiên bản, trạng thái duyệt, ngày hiệu lực và `repeat_days`.
  - Rút gọn thành luật vòng: bỏ các trường của định mức cũ (`anchor`, `offset_days`, `offset_months`, `repeat_months`, `quantity_basis`, `norm_profile`), thêm trường khu (tùy chọn). Mùa được biểu diễn bằng khoảng hiệu lực.
  - Các luật định mức cũ đang có được lưu trữ rồi xóa cùng phần định mức (R14).
  - Ngày đến hạn = ngày xong gần nhất + vòng. Lô chưa từng làm thì đến hạn từ ngày áp dụng.
  - Giao việc: đội trưởng chọn nhiều lô trong danh sách đến hạn và một tổ. Hệ thống tạo các `Lotus Work Assignment` loại `Round` (một lô, một việc, một vòng), chụp lại cách trả và đơn giá như hiện nay.
  - Khi tổ báo xong lô trong báo cáo ngày, Round chuyển sang `Reported`. Khoán cả lô thì đi tiếp nghiệm thu (`Lotus Work Inspection`); các cách trả khác khóa khi báo cáo được xác nhận.
  - Giao cố định cho tổ chăm buồng giữ loại `Bunch` như hiện nay.
- **Rationale**: Dùng lại bảng có sẵn. "Lịch chăm sóc theo lô" hiện tính từ cách dự thu cũ nên bỏ.
- **Lưu ý**: `plan_norm` và màn định mức cũ bị xóa (R14), nên bảng này chỉ còn một nghĩa là vòng chăm sóc.
- **Alternatives**: Thêm trường vòng trên `Work Type`: không có phiên bản, ngày hiệu lực hay người duyệt (FR-012).

## R5. Bảng màu dây

- **Decision**: Tính trực tiếp từ sổ lô, không lưu thêm bảng.
  - Nhóm theo lô và `Bunch Tag` (tuần và lần cắt; mỗi tuần một mã nên hai chu kỳ màu không lẫn).
  - Mỗi nhóm có: cắt bắp, bao, hủy sau cắt, đã thu, còn trên cây, tuổi tính bằng tuần.
  - Đợt đến tuổi thu theo bộ tham số dự thu đang hiệu lực (cắt bắp đến thu 60 đến 70 ngày).
  - Dùng lại phép tính dòng chảy của `bunch_flow_rules`.

## R6. Cách ly thu hoạch

- **Decision**:
  - Khi xác nhận dòng phun có vật tư mang thời gian cách ly, cập nhật `Farm Block.lotus_quarantine_until` lấy ngày muộn nhất (giữ cách tính `quarantine_until`).
  - Khi một dòng phun bị hủy, tính lại ngày hết cách ly từ các dòng phun đã xác nhận còn lại.
  - Dòng thu hoạch bị chặn khi lưu, gửi, xác nhận và sửa nếu ngày thu chưa qua ngày hết cách ly.
- **Rationale**: Sửa lỗ hổng đang có: dòng thu hoạch ghi qua `Lotus Bunch Event` không kiểm cách ly; chỉ `Harvest Actual` cũ có `harvest_guard`.

## R7. Dự thu

- **Decision**: Giữ nguyên `bunch_flow_rules`, `bunch_forecast_engine` và `block_forecast_engine`; chỉ viết lại phần nạp để đọc dòng đã xác nhận của sổ lô theo công đoạn của việc.
- Mọi màn có số dự thu (Tổng quan, kế hoạch tài chính, cung ứng) gọi chung một API.
- Gỡ 9 nơi đang đọc cách tính cũ (danh sách T040 của spec 001): `App.vue`, `reporting.py`, `onedrive_supply.py`, `finance/planning.py`, `console.py`, `forecast_calendar.py`, `vip126_timeline.py`, `vip126_trial.py`, `Vip126RollingForecast.vue`.

## R8. Bản chốt tuần không cần lịch chạy

- **Decision**: Khi có người mở ứng dụng sau 0 giờ thứ Hai mà tuần đó chưa có bản chốt, hệ thống tạo bản chốt theo mốc 0 giờ thứ Hai.
  - Chỉ lấy dòng có giờ xác nhận trước mốc và chưa bị hủy trước mốc (cần thêm `voided_at`).
  - Tham số lấy bản đang hiệu lực tại mốc.
  - Tuần bị bỏ lỡ được tạo bù. Khóa duy nhất vườn × tuần để nhiều người mở cùng lúc không tạo trùng.
  - Quản lý có nút tạo tay.
- **Rationale**: VPS không có container chạy lịch và được giữ như vậy. Phần chấm công cũng đang đồng bộ khi có người mở ngày.
- **Giới hạn**: số cây và ngày trổ của lô lấy theo giá trị hiện tại, không dựng lại theo mốc. Điều này được ghi trên bản chốt.
- **Alternatives**:
  - Cron trên máy chủ: cấu hình nằm ngoài repo, dễ mất khi chuyển máy.
  - Thêm container chạy lịch: trái quyết định vận hành hiện tại.

## R9. Phiếu giấy và đọc ảnh

- **Decision**:
  - **Phiếu in:** mỗi tổ-ngày một trang, gồm mã báo cáo (để máy nhận đúng tổ và ngày), bảng lô × việc đến hạn, ô số to và màu dây in sẵn cho cắt bắp.
  - **Đọc ảnh:** ảnh chụp gửi `document_ai`, dùng model đọc ảnh và khóa Groq đang dùng, với khuôn trả về cố định. Số máy đọc vào dòng Nháp có cờ "máy đọc".
  - **Đánh dấu dòng nghi ngờ:** dùng kiểm tra cố định, không dựa vào độ tự tin của model. Dòng bị đánh dấu khi lô hay việc không có trên phiếu, số buồng không nguyên, số vượt trần, hoặc ô trống mà phiếu in có.
  - Còn dòng máy đọc chưa có người kiểm thì không gửi được.
- **Rationale**: Phiếu in sẵn giúp máy đọc đúng hơn giấy viết tự do. Dùng lại khóa, giới hạn lượt và cách xử lý lỗi của phần đọc chứng từ.
- **Rủi ro**: chữ viết tay. Phải đo tỷ lệ đọc đúng trên phiếu thật của vườn trước khi bật cho các tổ.

## R10. Xưởng đóng gói

- **Decision**: `Packhouse Shift` thêm bảng con nguồn buồng: lô, đợt màu, số buồng, kg, dòng thu hoạch.
  - Thùng và thành phẩm chia cho các nguồn theo kg nhận (module thuần). Từ đó ra kg/buồng, thùng/buồng và tỷ lệ đóng gói theo lô và đợt màu.
  - Truy vết theo chuỗi: ca → nguồn → dòng thu hoạch → các dòng phun ở lô đó trước ngày thu.
- **Alternatives**: Chuỗi `Harvest Lot` và `Packout Run` cũ cần bật quản lý theo lô hàng và gắn thửa.

## R11. Báo cáo

- **Decision**: Viết một module báo cáo mới với ba API: Sáng nay, Tuần, Tháng.
  - Nguồn đọc: sổ lô, vòng chăm sóc, bảng màu dây, xưởng và dự thu.
  - Kết quả trả về: thẻ và dòng chi tiết; xuất Excel bằng `excel-export.js`.
  - Bản đồ dùng `CareMap` thêm lớp tình trạng lô.
  - Bỏ bốn trang Pivot cùng `bunch_report` và `work_report` sau khi ba màn mới chạy đúng.

## R12. Tiền khoán

- **Decision**:
  - **Khoán số lượng:** tiền bằng số lượng nhân đơn giá chụp lúc xác nhận dòng, khóa ngay.
  - **Khoán cả lô:** tính một lần khi Round nghiệm thu đạt.
  - **Công nhật:** không tính ở đây.
  - Tiền chia theo trọng số buổi (R3). Phần bù lương tối thiểu giờ giữ nguyên.
  - Màn "Tôi" hiện số tạm tính của tổ và của từng người.
  - Bắt đầu tính khi bản mới chạy; không có mốc 01/12/2026.

## R13. Menu

- **Decision**:
  - **Máy tính:** một nhóm 7 mục: Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu, Báo cáo (ba tab), Thiết lập. Thiết lập gồm đội tổ lô, việc và cách trả, bảng giá, vòng chăm sóc, màu dây, tham số dự thu.
  - **Điện thoại:** Hôm nay, Giao việc, Xác nhận, Tôi.
  - Vườn & lô (đất, bản đồ) giữ riêng.

## R14. Dữ liệu cũ và bảng cũ

- **Decision**:
  - Sao lưu, rồi chuyển 593 dòng sổ cắt bắp và mọi dòng `Lotus Bunch Event` đã xác nhận sang sổ lô, giữ nguyên khóa nguồn. Chạy lại không ghi trùng.
  - Dòng `Lotus Work Entry` và phiếu của bản thử chuyển sang trạng thái hủy với lý do "Bản thử trước sổ lô", không xóa, vì chúng nằm trong bảng được giữ.
  - Xóa hẳn 76 bảng đời cũ (18 bảng con), cùng màn hình, mục menu, mã, tool và test của chúng. Danh sách và các chỗ phải sửa ở [cleanup.md](cleanup.md).
- **Rationale**: Ngày 10/11/2026 chủ vườn yêu cầu xóa hẳn cho sạch, làm luôn trong spec này. Mảng này mới là bản thử. Còn giữ đồ cũ thì lần sửa nào cũng phải giữ tương thích với ba lớp cách làm.
- **Rủi ro**: Nhiều bảng bị kho, tài chính, lương tham chiếu: `Crop Cycle` 35 file, `Harvest Forecast` 34, `Harvest Actual` 27, `Daily Work Result` 26, `Bunch Operation` 26; `Daily Work Plan` nằm trong luồng xuất kho. Vì vậy phải chuyển các phần đó sang nguồn mới trước (R15, R16), và phải đếm, lưu trữ dữ liệu trên bản thật trước khi xóa (R18).

## R15. Giá thành và nhập kho thành phẩm

- **Decision**:
  - Bỏ chiều kế toán "Vụ" (`lotus_crop_cycle`, trỏ `Crop Cycle`). Chi phí dở dang tập theo lô; số vụ ghi kèm trên dòng giá thành dưới dạng số.
  - Nhập kho thành phẩm theo ca đóng gói. Mỗi ca một phiếu nhập kho chuẩn ERPNext (thành phẩm và phụ phẩm theo kg), lập ở trạng thái nháp để kế toán duyệt. Giá trị chuyển từ chi phí dở dang của các lô có buồng trong ca, chia theo kg nhận của từng nguồn.
  - Sản lượng dự kiến dùng trong giá thành và kế hoạch tài chính lấy từ API dự thu chung.
- **Rationale**: Cách cũ nhập kho theo `Harvest Lot` cần bật quản lý theo lô hàng và gắn thửa, và chưa từng chạy trên bản thật. Ca đóng gói đã có nguồn buồng theo lô và đợt màu (R10), nên chia giá trị theo lô được.
- **Alternatives**: Nhập kho buồng tươi theo từng dòng thu hoạch rồi xuất sang xưởng. Cách này thêm một bước kho, và kg buồng tươi khác kg thành phẩm.
- **Đã duyệt**: chủ vườn duyệt ngày 10/11/2026.

## R16. Kho

- **Decision**:
  - Phiếu xuất bỏ chế độ "Theo kế hoạch đã duyệt" (dựa trên `Daily Work Plan`); chỉ còn "Thủ công" và "Theo yêu cầu đã duyệt".
  - Màn "Nhu cầu cấp cho công việc" chỉ còn nhu cầu từ yêu cầu vật tư (`Material Request`).
  - Gỡ `Material Consumption`, `Material Recovery`, các trường cũ trên phiếu kho, và phần cầu nối `Packout Run`/`Harvest Lot` trong `stock_bridge.py`. Các kiểm tra phiếu kho khác giữ nguyên.
  - Báo cáo Tháng đối chiếu vật tư xuất kho với vật tư báo dùng theo lô (US5), thay cho liên kết giữa phiếu xuất và kế hoạch ngày.

## R17. Sâu bệnh

- **Decision**: "Kiểm tra sâu bệnh" là một việc trong nhóm phun bón của báo cáo ngày. Dòng sổ lô ghi bệnh (danh mục `Disease`), số cây bị và mức độ. Xóa `Disease Observation` và mục "Kiểm tra sâu bệnh" trên menu điện thoại cũ.
- **Rationale**: Vẫn ghi được sâu bệnh mà không cần thêm bảng, và báo cáo phun bón đọc chung một sổ.

## R18. Cách xóa

- **Decision**: Viết `legacy_purge.py`, chạy bằng bench, gồm hai bước:
  - `preview` (chỉ đọc):
    - đếm số dòng từng bảng;
    - đếm giá trị khác rỗng của các trường sẽ gỡ trên chứng từ: chiều Vụ, `lotus_work_plan`, `lotus_harvest_lot`, trường trỏ `Material Requirement`;
    - liệt kê kỳ lương đã hạch toán có dùng `Labor Allocation`.
  - `commit`:
    - sao lưu;
    - xuất từng bảng ra JSON, kèm số dòng và mã kiểm;
    - xóa theo thứ tự: dữ liệu → trường tùy chỉnh và chiều kế toán → DocType;
    - file mã được xóa trong cùng bản phát hành.
  - Nếu `preview` thấy giá trị nằm trên chứng từ đã ghi sổ thì `commit` dừng, chờ chủ vườn quyết.
  - Thêm một test quét mã để chặn tên bảng đã xóa quay lại.
- **Rationale**: Theo ràng buộc vận hành của hiến chương: sao lưu trước, chạy lại không lỗi, không sửa thẳng sổ kế toán.
- **Lưu ý triển khai**: Ảnh phát hành mới không được còn thư mục DocType đã xóa, nếu không migrate sẽ tạo lại bảng. `Dockerfile.release` đã có bước xóa `lotus_farm/lotus_farm` trước khi COPY.

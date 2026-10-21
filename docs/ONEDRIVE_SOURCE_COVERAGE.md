# Kiểm kê nguồn OneDrive và phạm vi ERP

Kiểm kê này dùng bằng chứng đã lưu trong `lotus_farm/data/onedrive_protocol_v1.json`
và `lotus_farm/data/onedrive_form_headers.json`. Tên ô dưới đây là **ô tiêu đề**;
không phải xác nhận toàn bộ dữ liệu bên dưới đã được nhập. Các phiên bản nguồn
giữ SHA-256 riêng trong protocol. Không đổi BP/ER thành Lotus bằng cách thay tên.

Trạng thái:

- **Đã nhập bàn giao**: nhật ký LOTUS-222, 301 đợt khu/ngày, 430.871 cây cũ đã chặt;
  giữ file private, SHA-256 và ô nguồn. Không phải cây trồng/chồi/cắt bắp thực tế.
- **Đã nạp tham chiếu**: thư viện có phiên bản; phải duyệt áp dụng cho từng vườn.
  Lịch, hệ số và dự phóng không tạo số thực tế, tồn kho hay cam kết bán.
- **Vận hành có sẵn**: chứng từ/API thực thi nghiệp vụ, có nhập tay hoặc ghi hiện
  trường. Generic importer hỗ trợ DocType không đồng nghĩa đã có mapping nguồn
  được duyệt, khóa nghiệp vụ, đơn vị và ánh xạ tổ chức cho từng file.
- **Cần ánh xạ/xác minh**: chưa có đủ bằng chứng để nhập tự động. Giữ trống/thiếu;
  không điền định mức, ngày trồng, số cây hoặc đơn vị bằng suy đoán.

## Master, bàn giao và kế hoạch

| File / bảng hoặc sheet | Cột/ô nguồn đã xác minh | Đơn vị / ý nghĩa | Đích ERP và trạng thái |
| --- | --- | --- | --- |
| `#100.1_11062025_File master data chuối - MĐ2600.xlsx` / `tsSXKD` | 57 bộ, 19 vườn × năm 1/2/3+; tên nguồn, số dòng và hệ số giữ trong protocol | mật độ cây/ha; CB/cây, TH/CB, SC/TH; kg nguyên buồng và kg sơ chế/buồng | `Lotus Process Adoption`; **đã nạp tham chiếu**, duyệt riêng theo vườn; không phải năng suất Lotus đã đo |
| `FILE MASTER DATA CHUOI - THONG SO.xlsx`, `FILE MASTER DATA CHUOI.xlsx` | các bảng `tsSXKD6`, `tsKHTH_R/C`, `tsPC_C`, `tsRaHoa`; bản tháng 7/2025 có SHA-256 riêng | tỷ lệ/khối lượng theo tên cột trong bảng tham chiếu; không trộn kg nguyên buồng và sơ chế | thư viện tham số/đường cong; **đã nạp tham chiếu**. Ánh xạ chi tiết giữ theo tên cột nguồn, không giả định chữ cột Excel |
| Nhật ký chặt cây cũ LOTUS-222 | ngày/khu/số cây, tọa độ cụ thể giữ ở `Lotus Handover Cohort.source_cells` | cây cũ đã chặt; ngày được người dùng quy ước tương đương chọn chồi | **đã nhập bàn giao**; không phân bổ ngầm xuống lô/thửa, không tạo `Sucker Selection Batch` |
| `Báo cáo Chọn chồi.xlsx` / `Tổng hợp` | `K6:U6`; công thức `EDATE(K6,4)` dọn chồi, `EDATE(K6,6/12/…/42)` chọn | tháng lịch từ mốc gốc, giữ ngày cuối tháng | lịch chọn chồi trong workspace / `Work Schedule Rule`; **đã nạp tham chiếu**, chưa phải ngày làm thực tế |
| `Báo cáo Chọn chồi.xlsx` / `NL_Chọn chồi` | `B` vụ, `C` ngày làm, `Y` số cây chọn | số vụ; ngày; chồi kiểm đếm | `Crop Cycle` + `Sucker Selection Batch`; **vận hành có sẵn**, nhập thực tế cần mapping tổ chức/lô/vụ được duyệt |
| `Chăm sóc buồng và thu hoạch.xlsx` / `DmMauDay` | `B1` mã màu, `D1` màu dây, `E:F` kỳ cắt bắp, `G:H` kỳ chích, `N:O` cửa sổ thu | 17 mã; 183 kỳ lịch sử; ngày; chích sớm 14 ngày, thu E+55/F+70 | `Bunch Tag` + adoption; **đã nạp tham chiếu**, lịch sau 01/01/2026 là lịch kéo dài có phiên bản; phát hành lịch không tạo buồng |

## Chăm sóc và đo đếm

Các sheet nhập liệu có `Id`, ngày, tổ chức, lô/thửa cũ và lô/thửa quy hoạch mới.
Mapping phải chọn một hệ lô/thửa đã đối soát, phân giải `Legacy Organization Map`
và `Crop Cycle`, không tự nối hai cột chỉ vì tên giống nhau. Ngày trồng trong file
tham chiếu không được dùng để lấp lịch sử chưa biết của một lô Lotus.

| File / sheet | Cột/ô tiêu đề | Đơn vị / điều kiện | Đích ERP và trạng thái |
| --- | --- | --- | --- |
| `NL_Chăm sóc vườn.xlsx` / `1. Chọn chồi_Tagging` | `B2` vụ, `C2` ngày TH, `K:L` lô/thửa, `M:N` lô/thửa mới, `Y2` số cây chọn, `Z:GC` L1…L160, `GD2` DT chọn chồi | Y là số cây/chồi; U ghi ha. Ý nghĩa/đơn vị từng L và DT cần xác minh trước khi unpivot | `Sucker Selection Batch`; **vận hành có sẵn**. Không thay Y bằng tổng cây cũ hoặc tự suy từ mật độ |
| cùng file / `2. Cắt chồi_Sucker Prunning` | `B2`, `C2`, `K:N`, `W2` số gốc cắt chồi, `X2` số công nhân LĐ, `Y2` ghi chú | gốc; X là số người theo nhãn, chưa đủ để coi là công/ngày | `Daily Work Plan/Result`, `Labor Allocation`; **vận hành có sẵn**, cần mapping công việc/UOM và thời lượng lao động |
| cùng file / `3. Bón phân_Fertilizer` | `B2`, `C2`, `K:N`, `W2` mục đích, `X2` khối lượng CV cây, `Y:AN` vật tư, `AO2` số công, `AQ2` số công nhân, `AS:BC` liều theo nhãn | cây; `AI` kg, `AK` lít; `AS:AZ`, `BC` grams; `BA:BB` kg. Các cột không ghi đơn vị cần xác minh; số công và số người giữ riêng | `Daily Work Result`, `Material Consumption`, ERP `Stock Entry`; **vận hành có sẵn**. Vật tư thực dùng không tự thành `Material Norm Profile`; phải có mẫu số/cơ sở định mức và phiên bản duyệt |
| cùng file / `4. Cắt lá_Leaf Pruning` | `C2` ngày, `K:N` phạm vi, `U2` công việc, `V2` khối lượng TH cây, `W2` số công nhân | cây; người; R ghi ha | `Work Type`, `Daily Work Result`, `Labor Allocation`; **vận hành có sẵn**, cần phân giải công việc và lao động |
| cùng file / `5. Làm cỏ_Manual Weeding ` | `C2`, `K:N`, `U2` công việc, `V2` khối lượng TH gốc, `W2` số công nhân | gốc; người; R ghi ha | cùng luồng công việc; **vận hành có sẵn**; không đổi gốc thành ha bằng hệ số giả định |
| cùng file / `6. Phát cỏ_Grass Cutting` | `C2`, `K:N`, `U2` công việc, `V2` khối lượng TH ha, `W2` số công nhân | ha; người | cùng luồng công việc; **vận hành có sẵn**; chưa chứng minh mapping nhập file được duyệt |
| `Chăm sóc buồng và thu hoạch.xlsx` / `ChichBap` | `B2` vụ, `C2` ngày, `K:N` phạm vi, `U:V` thuốc, `W2` định mức/búp, `X2` thuốc dùng, `Z2` số công, `AA2` số lượng, `AB:AD` dự tính cắt bắp/màu | số lượng chích bắp; thuốc cần UOM đã đối soát. Các cột dự tính là kế hoạch | `Bunch Operation` loại `Bud Injection`, `Bunch Tag`; vật tư/công qua chứng từ tương ứng; **vận hành có sẵn** |
| cùng file / `CatBap` | `B2`, `C2`, `K:N`, `U:V` mã/màu, `X2` số công, `Y2` số lượng cắt bắp, `Z2` xưởng, `AA:AB` kỳ CB | buồng cắt bắp; ngày; mã màu theo phiên bản | `Bunch Operation` loại `Cut Bud`; **vận hành có sẵn**. Cắt bắp thực tế là nguồn truy xuất, không tạo từ lịch màu |
| cùng file / `PhunBuong` | `A2` vụ, `B2` ngày, `J:M` phạm vi, `U:AC` thuốc/định mức/lượng dùng, `AD2` công, `AE2` số buồng, `AF2` code | buồng; UOM thuốc và ý nghĩa code cần duyệt mapping | `Bunch Operation` loại `Spray` + `source_cut_operation`; vật tư dùng qua ERP; **vận hành có sẵn** |
| cùng file / `BaoBuong`, `ChongDoNga` | `B2` vụ, `C2` ngày, `K:N` phạm vi, `R:S` mã/màu, `T2` số lượng | số buồng; giữ màu của đợt cắt gốc | `Bunch Operation` loại `Bag`/`Care` + nguồn cắt; **vận hành có sẵn**, không ghép nguồn chỉ bằng tên màu lặp |
| cùng file / `HuyChuoi` | `B2`, `C2`, `K:N`, `R:S` mã/màu, `T2` số hủy, `U:V` nguyên nhân gốc/đã sửa, `W2` nhóm lỗi; `Sheet2 B:D,F:G` danh mục | số buồng; cần ngày dự thu và đợt cắt gốc để trừ đúng nguồn/kỳ | `Bunch Cancellation`, `Cancellation Reason/Group/Alias`; **vận hành có sẵn**, danh mục/alias và khóa nguồn cần duyệt |
| `FM ĐO TRÁI - luống.xlsx` / `ĐoTrai` | `B2` vụ, `C2` ngày, `K:N` phạm vi, `R:S` mã/màu, `T2` người đo, `U2` số lượng đo, `V:FE` L1…L140 | nhãn L chưa chứng minh chiều đo/UOM. Mapping phải ghi rõ luống, mã mẫu, Length/Diameter và đơn vị; không tự coi số là cm hoặc mm | `Fruit Measurement` + `Fruit Measurement Sample`; **vận hành có sẵn**, generic importer unpivot qua mapping duyệt. Server tính số mẫu/bình quân; giữ mẫu gốc, không lấy bình quân làm từng mẫu |

## Thu hoạch, xưởng, kho và báo cáo

| File / sheet | Cột/ô tiêu đề | Đơn vị / điều kiện | Đích ERP và trạng thái |
| --- | --- | --- | --- |
| `Chăm sóc buồng và thu hoạch.xlsx` / `ThuHoach` | `B2` vụ, `C2` ngày, `K:N` phạm vi, `S:T` mã/màu, `U2` xưởng nhận, `V2` số lượng thu | số buồng; xưởng phải ánh xạ đúng Warehouse; cần nguồn cắt đã xác nhận | `Harvest Actual`; **vận hành có sẵn**, không yêu cầu chồi giả cho vụ kế thừa |
| cùng sheet | `W2` số hủy XĐG, `X2` SL sơ chế, `Y2` NS sơ chế, `Z2` SL tấn, `AA2` NS TH, `AB2` tổng SL | Z ghi tấn (×1.000 để thành kg nếu mapping đã xác nhận giá trị); các SL/NS khác chưa đủ bằng chứng về mẫu số/UOM | `Harvest Lot`, `Incoming Quality Inspection`, `Packout Run`; **cần ánh xạ/xác minh**. Không dùng X/Z/AB thay lẫn nhau hoặc coi năng suất là kg cân thực tế |
| cùng sheet | `AC:AK` A456/A789/B456/B789/CL/CP/CNB/NB13/NB18; `AL:AO` chuối A/B/C/bò | mã phân loại; chưa xác minh là kg, thùng hay số đơn vị cho từng cột | `Product Grade`, `Item`, `Pack Specification`, `Packout Output`; **vận hành có sẵn**, nhưng cần Item/UOM/quy cách và mapping được duyệt trước nhập |
| Cân/nhận buồng | Không có cột gross/tare/device/reading ID đã chứng minh trong header snapshot | cân dùng kg; ngày giờ thiết bị, mã đọc và bì phải là bằng chứng thực | `Scale Device/Reading`, liên kết `Harvest Actual`/`Harvest Lot`; **vận hành có sẵn** qua API. Chưa có adapter đã chứng minh cho file nguồn; không suy gross/tare từ sản lượng kế hoạch |
| `PHIẾU BC XĐG.xlsx` / `BC` | snapshot tiêu đề rỗng; không đủ cột để mapping | **chưa xác minh** đơn vị, vùng biểu mẫu và dòng lao động/sơ chế/đầu ra | `Packhouse Shift`/labor/preprocessing + `Packout Run`; **vận hành có sẵn**, **mapping nguồn còn thiếu**. Generic importer hiện không hỗ trợ Packhouse Shift |
| Nhận/QC/ERP kho | Không có bảng QC hoặc stock ledger riêng đã xác minh từ header snapshot | kg nhận/đạt/loại; nguyên nhân giải thích kg loại; Item/Warehouse/Batch thật | `Harvest Lot` → `Incoming Quality Inspection` → `Packout Run` → ERP `Stock Entry`; **vận hành có sẵn**. Receipt nguyên liệu và Repack phải ghi sổ ERP; không nhập sổ kho từ số kế hoạch |
| `FM BÁO CÁO KẾT QUẢ CB - TH -SC - ĐG CHUỐI.xlsx` / `Sheet1` | `A1` TT, `B1` nội dung, `E1` ĐVT, `F:H` NTR, `I1` XN | E là đơn vị cho từng dòng; snapshot không có tên dòng/chỉ tiêu để ánh xạ chi tiết | `Cycle Closing Report`; **báo cáo tính từ chứng từ thực tế có sẵn**, **mapping đối chiếu từng dòng còn thiếu**. Không nhập tổng báo cáo thành các giao dịch giả |
| Báo cáo ngày / kết vụ | `ttKetVu` trong master và biểu mẫu kết vụ là bằng chứng tham chiếu; không phải chứng từ Lotus đã duyệt | tổng thực ghi nhận; diện tích ha; tấn/ha; công. Vụ kế thừa giữ tình trạng thiếu lịch sử trước tiếp quản | `Daily Production Close` / `Cycle Closing Report`; **vận hành có sẵn**, chỉ chốt khi truy nguồn/QC/kho/công việc hoàn tất. Generic importer không hỗ trợ nhập hai báo cáo chốt |

## Kiểm chứng và phần còn thiếu

`lotus_farm.importing.IMPORT_FIELDS` là danh sách DocType/trường được phép nhập,
không phải tập mapping hoàn chỉnh của AnhDung. Một mapping nhập thực tế phải có
source registry + SHA-256, sheet/vùng, khóa nghiệp vụ ổn định, tổ chức/lô/vụ,
đơn vị/chuyển đổi, khóa nguồn và bản duyệt; chạy preview rồi tạo chứng từ nháp.

Các phần cần bổ sung từ nguồn trước khi tự động nhập: vùng dữ liệu `BC` của phiếu
xưởng; chiều đo và đơn vị L1…L140; đơn vị/mẫu số các cột SL/NS và phẩm cấp; số người
so với công thực tế; đơn vị thuốc/phân chưa ghi trên nhãn; nội dung từng dòng báo
cáo kết vụ. Không bổ sung bằng chuẩn định mức hoặc hệ số của một vườn nguồn khác.

Acceptance tích hợp nằm trong `lotus_farm.tests.test_onedrive_takeover`, chạy trên
testsite dùng một lần: vụ kế thừa không ngày trồng/vụ mẹ/chồi giả → cắt bắp thật có
tag → mẫu đo/hủy/thu cùng nguồn → cân/nhận/QC → ca xưởng/đóng gói/kho ERP → chốt
ngày/kết vụ; vụ kế tiếp phải có parent và đợt chồi kiểm đếm. Các số trong test là
fixture riêng, không đại diện giao dịch thật đã nhập từ OneDrive.

# Sổ tay vận hành Tài chính – Kế toán Lotus (Thông tư 99)

Cùng nội dung với tab **Hướng dẫn** trên màn Tài chính – Kế toán (`/lotus/tai-chinh`). Sổ kế toán duy nhất là sổ cái ERPNext (GL Entry); mỗi nghiệp vụ nhập một lần ở module Lotus, kế toán không nhập lại.

## 1. Ai làm gì

| Người | Việc |
|---|---|
| Thủ kho / nhân viên kho | Phiếu nhập (chọn đúng lý do nhập), phiếu xuất (mã lô ở ô "Khu vực / lô sử dụng"), kiểm kê; duyệt phiếu nhập kho thành phẩm nháp mà kế toán lập theo ca đóng gói. |
| Mua hàng | Đề xuất mua → đơn mua → nhận hàng. Mua không qua đơn: kho nhập lý do "Mua ngoài" và chọn nhà cung cấp. |
| Nhân sự | Chấm công; khai số người phụ thuộc và cam kết 08/CK-TNCN trong hồ sơ nhân viên; chốt và gửi ký bảng công, bảng lương. |
| Kế toán | Hóa đơn mua (có thuế GTGT), hóa đơn dịch vụ, hóa đơn bán, phiếu thu, phiếu chi / ủy nhiệm chi, tạm ứng lương, nộp bảo hiểm và thuế, ghi sổ lương. |
| Kế toán trưởng | Ký phiếu chi bước 2, đảo bút toán, bút toán điều chỉnh, kết chuyển chi phí, giá thành, kết chuyển 911, khóa / mở kỳ, cấu hình. |
| Giám đốc | Ký bước cuối phiếu chi (chữ ký cuối làm phiếu chi ghi sổ). |
| Quản trị hệ thống | Gán vai trò ở Thiết lập › Người làm kế toán. |

## 2. Bắt đầu (một lần)

1. Gán vai trò Kế toán trưởng, Kế toán (và Kiểm soát nếu cần).
2. Áp dụng hệ thống tài khoản Thông tư 99; kiểm tra tài khoản theo nghiệp vụ (gồm 3335, 3382, 131, 511, 33311, 1331, 911, 4212).
3. Chọn ngày bắt đầu ghi sổ (đầu tháng). Chứng từ trước ngày này thuộc số dư đầu kỳ.
4. Nhập số dư đầu kỳ bằng file mẫu.
5. Chọn vùng lương tối thiểu (trần BHTN); nhập giá thành kế hoạch chuối thu hoạch (đ/kg).
6. Xem "Tham số lương theo pháp luật" (giảm trừ, biểu thuế, bảo hiểm, nguồn văn bản).
7. Khóa các tháng trước ngày bắt đầu. Bật "Ghi sổ kế toán từ Lotus".

## 3. Việc hằng ngày

- **Kho**: phiếu nhập chọn lý do (Mua ngoài / Thu hồi vật tư / Thừa kiểm kê); phiếu xuất gõ mã lô; kiểm kê thừa và thiếu lập hai phiếu.
- **Xưởng / kế toán – chuối thành phẩm**: ca đóng gói đã đóng hiện ở Chờ hạch toán › Ca đóng gói đã đóng, chưa nhập kho → Lập phiếu nhập kho (cũng lập được ở màn Xưởng). Phiếu là bản nháp theo giá thành tạm tính (Nợ 155 / Có 154 theo lô): kế toán kiểm, Kho duyệt. Ca vẫn nằm trong danh sách (cột Phiếu nhập kho ghi phiếu nháp, nút Mở phiếu nháp) cho đến khi phiếu được duyệt. Không lập phiếu nhập chuối bằng tay trong Desk. Bao bì xuất với mục đích "Xuất bao bì đóng gói".
- **Kế toán – mua hàng**: Chờ hạch toán › chọn phiếu nhận cùng nhà cung cấp → Lập hóa đơn (số, ngày, thuế suất GTGT).
- **Kế toán – bán hàng**: Bán hàng – Phải thu › Lập hóa đơn bán (khách hàng, hàng trong kho thành phẩm, số lượng, đơn giá, thuế suất, ký hiệu và số hóa đơn điện tử). Hóa đơn xuất kho luôn.
- **Kế toán – thu tiền**: Thu tiền ở dòng khách hàng; ghi sổ ngay.
- **Kế toán – trả tiền**: Công nợ phải trả › Lập phiếu chi, chọn người ký; ghi sổ khi Giám đốc ký xong.
- **Kế toán – dịch vụ**: Hóa đơn dịch vụ / chi phí; chi phí cho lô chọn "Sản xuất" và vườn / lô.

## 4. Cuối tháng (đúng thứ tự)

Thiết lập › **Đóng tháng — danh sách kiểm tra** tự đánh dấu từng bước:

1. Phiếu nhận hàng trong tháng đã có hóa đơn.
2. Phiếu xuất kho đã gắn lô.
3. Ca đóng gói trong tháng đã nhập kho thành phẩm: mọi ca đã đóng có phiếu nhập kho và Kho đã duyệt. Còn ca chưa lập phiếu hay phiếu nhập kho nháp trong tháng thì chưa tính giá thành, chưa kết chuyển 911 và chưa khóa tháng được.
4. Bảng lương ký đủ và ghi sổ; lập phiếu chi lương (Lotus trừ tạm ứng), tải danh sách chuyển khoản.
5. Phiếu chi trong tháng ký xong hoặc hủy.
6. Nộp BHXH, BHYT, BHTN, KPCĐ, thuế TNCN của tháng trước.
7. Kết chuyển chi phí 621 / 622 / 627 → 154 theo lô.
8. Tính giá thành chuối (khi có thu hoạch): Thiết lập › Giá thành, xem bảng từng lô (dở dang, chi phí, kg thu, kg dự thu còn lại, giá / kg) rồi Ghi sổ giá thành. Chênh lệch với giá tạm tính của phần đã bán vào 632; phần của hàng còn tồn cuối tháng ở lại 154. Phiếu nhập kho của tháng thêm hay hủy sau khi tính thì danh sách kiểm tra báo: đảo bút toán giá thành (nếu có) rồi tính lại.
9. Kết chuyển kết quả kinh doanh: doanh thu, chi phí → 911 → 4212.
10. Đối chiếu: mọi dòng "Khớp"; B01 tài sản = nguồn vốn; bảng kê thuế GTGT khớp sổ.
11. Khóa sổ tháng.

**Giá thành chuối tính thế nào.** Mỗi lô: (dở dang 154 đầu tháng + chi phí kết chuyển trong tháng) × kg thu ÷ (kg thu + kg dự thu còn lại).

- Kg thu là kg nhập kho trong tháng (thành phẩm + phụ phẩm).
- Kg dự thu còn lại là kg thành phẩm dự thu chung (màn Dự thu) còn chờ ở lô sau ngày cuối tháng, đếm theo ngày đến hết một vòng cây: chồi chọn ngày cuối tháng tới khi thu xong, theo bộ thông số dự thu (mặc định 6 tháng tới trổ, 86 ngày tới thu, thu trong 30 ngày). Quả xa hơn mọc trên cây chưa có, chưa nhận chi phí nào.
- Kg đó quy về kg nhập kho theo tỷ lệ kg nhập / kg thành phẩm của lô trong tháng (lô chỉ có phụ phẩm thì theo cả vườn); cột "Cách tính" ghi hệ số.
- Sổ lô tính theo ngày làm việc của dòng: buồng thu ngày cuối tháng, sáng hôm sau mới xác nhận, vẫn là của tháng.
- Lô không còn kg dự thu thì dồn hết. Chi phí chung của vườn (không gắn lô) chia theo kg của cả vườn. Phần chưa thu nằm lại 154.
- Cột "Vụ số": vụ có nhiều buồng nhất trong các dòng thu hoạch đã xác nhận của lô trong tháng; để trống khi lô không có dòng thu hoạch trong tháng và ở dòng chi phí chung của vườn.

## 5. Lương, bảo hiểm, thuế TNCN

- **Hợp đồng từ 3 tháng**: biểu lũy tiến 5 bậc (5%–35%) sau khi trừ bảo hiểm người lao động, giảm trừ 15,5 triệu bản thân và 6,2 triệu mỗi người phụ thuộc (từ kỳ tính thuế 2026, Luật 109/2025/QH15). Phần lương đêm, tăng ca cao hơn giờ thường không chịu thuế.
- **Thời vụ, thử việc, hợp đồng dưới 3 tháng**: khấu trừ 10% mỗi lần trả từ 2 triệu đồng; có cam kết 08/CK-TNCN thì không khấu trừ. (Ngưỡng 5 triệu từ 01/7/2026 được nêu trong một số bài viết nhưng chưa đối chiếu văn bản gốc, nên chưa áp dụng.)
- **Bảo hiểm**: người lao động 10,5%, doanh nghiệp 21,5% trên lương hợp đồng; trần 20 × lương cơ sở (BHXH, BHYT), 20 × lương tối thiểu vùng (BHTN).
- **KPCĐ**: 2% quỹ lương đóng BHXH, vào chi phí nhân công, ghi Có 3382.
- **Tạm ứng lương**: Thu / Chi › Tạm ứng lương (Nợ 334 / Có 111, 112), ký 3 bước, trừ khi chi lương tháng đó.
- Tham số có ngày hiệu lực trong `lotus_farm/data/payroll_vn.json`, mỗi dòng ghi nguồn văn bản.

## 6. Định khoản

| Nghiệp vụ | Bút toán |
|---|---|
| Nhận hàng theo đơn / mua ngoài | Nợ 152 / Có 3388 |
| Hóa đơn mua | Nợ 3388, Nợ 1331 / Có 331 |
| Hóa đơn dịch vụ cho lô / quản lý | Nợ 6277 hoặc 6427, Nợ 1331 / Có 331 |
| Trả nhà cung cấp | Nợ 331 / Có 111, 112 |
| Xuất vật tư cho lô / thu hồi | Nợ 621 / Có 152 — Nợ 152 / Có 621 |
| Kiểm kê thừa / thiếu | Nợ 152 / Có 3381 — Nợ 1381 / Có 152 |
| Xuất bao bì | Nợ 6272 / Có 152 |
| Nhập kho thành phẩm theo ca đóng gói | Nợ 155 / Có 154 (lô trồng) theo giá tạm tính / kg |
| Hóa đơn bán | Nợ 632 / Có 155 — Nợ 131 / Có 511, 33311 |
| Thu tiền khách hàng | Nợ 111, 112 / Có 131 |
| Lương có công ở lô / gián tiếp | Nợ 622 hoặc 6421 / Có 334, 3383, 3384, 3386, 3382, 3335 |
| Tạm ứng / chi lương | Nợ 334 / Có 111, 112 |
| Nộp BH, KPCĐ, TNCN | Nợ 3383, 3384, 3386, 3382, 3335 / Có 112 |
| Kết chuyển chi phí | Nợ 154 / Có 621, 622, 627 |
| Giá thành | Phần đã bán, thực tế cao hơn tạm tính: Nợ 632 / Có 154; thấp hơn: Nợ 154 / Có 632 (theo lô). Phần còn tồn kho: không ghi, ở lại 154 |
| Kết chuyển kết quả | 5xx, 711 → 911; 911 → 632, 635, 641, 642, 811, 821; 911 → 4212 |

## 7. Báo cáo và sổ sách

- **B01-DN** tình hình tài chính, **B02-DN** kết quả kinh doanh, **B03-DN** lưu chuyển tiền tệ (gián tiếp) theo mẫu Thông tư 99/2025/TT-BTC; tài khoản lấy vào từng chỉ tiêu ở `lotus_farm/data/bctc_tt99.json`. Kế toán trưởng đối chiếu trước khi nộp báo cáo năm (Lotus mặc định ngắn hạn cho 128, 242, 341, 352).
- **Nhật ký chung, sổ cái / sổ quỹ / sổ tiền gửi** (có tài khoản đối ứng), **công nợ theo đối tượng**, **nhập – xuất – tồn**, **thuế GTGT** (bảng kê mua vào / bán ra, số liệu tờ khai 01/GTGT), **đối chiếu ngân hàng** (tải sao kê Excel).
- Mọi báo cáo xuất Excel có chỗ ký.

## 8. Sửa sai

- Chứng từ đã ghi sổ sai: Kế toán trưởng **đảo** (ghi lý do) rồi lập lại; không sửa trực tiếp.
- Bảng lương đã ghi sổ: đảo bút toán lương trước khi mở lại kỳ công.
- Làm lại cuối tháng: đảo theo thứ tự ngược (911 → giá thành → kết chuyển chi phí).
- Tháng đã khóa: mở lại kỳ (bắt buộc lý do), sửa, khóa lại.
- Số dư treo (VD 3381): Thiết lập › Bút toán điều chỉnh.

## 9. Lotus chưa làm

- Nộp tờ khai thuế điện tử, phát hành hóa đơn điện tử (kế toán dùng HTKK / eTax và phần mềm hóa đơn, nhập số hóa đơn vào Lotus).
- Tài sản cố định và khấu hao tự động, thuế TNDN, hàng bán trả lại / chiết khấu thương mại, ngoại tệ.

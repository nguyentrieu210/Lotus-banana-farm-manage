# Công việc ngoài vườn: phiếu giao việc theo lô (Vườn 222)

Làm lại ngày 31/10/2026, thay cho báo cáo ngày theo đội (29/10). Thiết kế dựa trên nghiên cứu
`reports/Thiết kế việc ngoài vườn chuối.md`. Nguyên tắc: **máy chấm công chỉ chứng minh có mặt; tiền khoán chỉ tính
từ lô đã được đối chiếu hoặc nghiệm thu.**

## Phiếu giao (Lotus Work Assignment)
- Mỗi phiếu = một lô × một việc × một tổ × một lượt. Đội trưởng giao, chọn được nhiều lô một lần (mỗi lô một phiếu).
  Một lô + việc chỉ có một phiếu đang mở.
- **Cách trả đi theo việc** trong danh mục (`Work Type.lotus_pay_mode`), quản lý vườn đặt ở "Việc & cách trả":
  - **Khoán số lượng** (Count): buồng, cây, bao. Trần đối chiếu: số buồng đã cắt bắp cùng màu ở lô, hoặc số cây lô.
  - **Khoán lô** (Lot): trả cả lô (ha hoặc cây × đơn giá) một lần, chỉ khi kỹ thuật vườn nghiệm thu đạt.
  - **Công nhật** (Daywork): tiền theo máy chấm công; phiếu chỉ ghi việc đã làm.
  Lúc giao, phiếu chụp lại nhóm việc, cách trả, đơn giá, định mức, trần, diện tích và số cây của lô. Người giao không
  sửa được cách trả.
- Trạng thái: Đang làm → Tổ báo xong → (đội trưởng duyệt) → [khoán lô: Chờ nghiệm thu → Đạt / Không đạt (làm lại)] →
  Đã khoá, tính tiền. Huỷ hoặc đổi tổ phải ghi lý do.

## Báo cáo trên phiếu (Lotus Work Entry, một báo cáo / phiếu / ngày)
- Tổ trưởng chọn **người làm theo buổi**: chỉ hiện người máy chấm công có lượt (sáng trước 7h, chiều sau 17h), mặc
  định người có mặt của tổ.
- Ba luật cứng:
  1. Mỗi buổi của một người chỉ thuộc một phiếu (Lotus Work Session, khoá duy nhất người × ngày × buổi trong DB).
  2. Không có lượt máy buổi đó thì không ghi được.
  3. Khối lượng không vượt trần của lô.
- Ô theo nhóm việc: **Buồng** (số buồng, màu dây: cắt bắp tự lấy màu tuần, bao/tỉa/chống đổ chọn màu, cộng dồn không
  vượt số cắt bắp cùng màu; trước 01/12/2026 chỉ cảnh báo), **Vườn** (khối lượng, báo xong lô), **BVTV / phân bón**
  (bắt buộc vật tư, liều, phiếu xuất kho; thuốc có thời gian cách ly `Item.lotus_phi_days` ghi
  `Farm Block.lotus_quarantine_until` và **chặn Harvest Actual** đến hết cách ly).
- Tick "Đã làm xong cả lô" khi lưu là báo xong.

## Duyệt, nghiệm thu, tiền
- Đội trưởng duyệt phiếu báo xong (không còn xác nhận báo cáo hằng ngày). Khoán số lượng và công nhật: khoá luôn.
- Khoán lô: **kỹ thuật vườn** (vai trò Lotus Field Inspector, hoặc quản lý vườn) nghiệm thu; đội trưởng không nghiệm thu
  đội mình. Cách chọn mẫu do hệ thống đưa ra; mức đạt Buồng 95%, Vườn / BVTV 90% (`field_report_rules.PASS_MARK`).
- Khoá: tiền phiếu chia cho người làm theo số buổi (`split_by_sessions`).
- **Bảng lương** (`hr_period._sheet`): buổi làm trên phiếu khoán **không tính công nhật**; tiền khoán của các phiếu khoá
  trong tháng cộng vào; nếu tiền khoán quy ra giờ thấp hơn lương tối thiểu giờ (Lotus Pay Rate MinimumHourly, vùng II
  22.700 đ) thì bù. Khoán và bù chịu thuế TNCN như lương; phụ cấp công việc vẫn cộng sau thuế.
- **Chi phí theo lô**: `finance/payroll._work_rows` lấy buổi công trên phiếu (0,5 công / buổi) theo lô × việc.
- Màn chấm công hiện nhãn "Khoán" cho buổi đã ghi trên phiếu khoán.

## Màn hình (một bộ component, máy tính và điện thoại)
- `/lotus/cong-viec`: Hôm nay, Giao việc theo lô, Nghiệm thu, Bảng lô × việc, Tiền khoán theo người, Đội-tổ-lô, Bảng giá
  khoán, Việc & cách trả. `/work`: Hôm nay, Giao việc (đội trưởng), Nghiệm thu (kỹ thuật vườn), Tôi.
- Component: `components/field/WorkToday.vue`, `WorkEntryForm.vue`, `WorkTicket.vue`, `WorkAssign.vue`, `WorkInspect.vue`,
  `FieldBoard.vue`; mô hình thuần `field-work-model.js`.

## Mã
- `lotus_farm/field_report.py` (API, quyền), `field_report_rules.py` (quy tắc thuần, `tests/test_field_report_rules.py`),
  `field_report_seed.py` (`MODES`: nhóm và cách trả của 26 việc F222; `apply_modes` cho site đã nạp).
- DocType: Lotus Work Assignment, Lotus Work Entry (+ Person, Material), Lotus Work Session, Lotus Work Inspection,
  Lotus Piece Rate, Lotus Pay Rate.
- Kiểm thử tích hợp: `tests/integration/verify_field_work.py`.

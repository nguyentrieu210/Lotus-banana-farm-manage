<script setup>
// Sổ tay vận hành Tài chính – Kế toán (tab Hướng dẫn). Static content: who does what, the one-time setup, the daily work
// of each department, month-end, payroll and taxes, how each Lotus document posts (Thông tư 99), reports and books, and
// how to correct a mistake. The same text is kept in docs/KE_TOAN_VAN_HANH.md.
import {ref} from 'vue'
const emit=defineEmits(['go'])
const open=ref('roles')
const SECTIONS=[['roles','Ai làm gì'],['start','Bắt đầu (một lần)'],['daily','Việc hằng ngày'],['month','Cuối tháng'],['tax','Lương và thuế'],
 ['entries','Định khoản từng nghiệp vụ'],['reports','Báo cáo và sổ sách'],['fix','Sửa sai'],['faq','Câu hỏi thường gặp']]
const ROLES=[
 ['Thủ kho / nhân viên kho','Lập phiếu nhập (chọn đúng lý do nhập), phiếu xuất (ghi mã lô ở ô "Khu vực / lô sử dụng"), kiểm kê, nhập kho lô chuối thu hoạch. Không cần vào màn kế toán.'],
 ['Mua hàng','Đề xuất mua → đơn mua → nhận hàng. Hàng mua không qua đơn mua thì kho nhập với lý do "Mua ngoài" và chọn nhà cung cấp.'],
 ['Nhân sự','Chấm công, khai số người phụ thuộc và cam kết 08 trong hồ sơ nhân viên, chốt và gửi ký bảng công & bảng lương. Khi bảng lương ký đủ, kế toán ghi sổ ở Chờ hạch toán (không dùng phiếu lương HRMS).'],
 ['Kế toán (Lotus Accountant)','Hóa đơn mua (có thuế GTGT), hóa đơn dịch vụ, hóa đơn bán, phiếu thu, phiếu chi / ủy nhiệm chi, tạm ứng lương, nộp bảo hiểm và thuế, ghi sổ lương; xem mọi báo cáo.'],
 ['Kế toán trưởng (Lotus Chief Accountant)','Ký phiếu chi bước 2, đảo bút toán, bút toán điều chỉnh, kết chuyển chi phí, giá thành, kết chuyển 911, khóa / mở kỳ, cấu hình tài khoản và tham số.'],
 ['Giám đốc (người duyệt mua / Quản lý vườn)','Ký bước cuối phiếu chi — chữ ký cuối mới làm phiếu chi ghi sổ. Chỉ thấy phiếu chờ mình ký.'],
 ['Quản trị hệ thống','Gán vai trò Kế toán / Kế toán trưởng / Kiểm soát ở Thiết lập › Người làm kế toán.'],
]
const START=[
 'Quản trị gán vai trò: ít nhất một Kế toán trưởng và một Kế toán (Thiết lập › Người làm kế toán). Người ký bước Giám đốc cần có vai trò Người duyệt mua hoặc Quản lý vườn và có hồ sơ nhân viên gắn tài khoản.',
 'Kế toán trưởng áp dụng hệ thống tài khoản Thông tư 99 (Thiết lập › Hệ thống tài khoản) và kiểm tra tài khoản cho từng nghiệp vụ (gồm 3335, 3382, 131, 511, 33311, 1331, 911, 4212).',
 'Chọn ngày bắt đầu ghi sổ (cutover) — nên là ngày đầu tháng. Chứng từ trước ngày này nằm trong số dư đầu kỳ, Lotus không ghi sổ lại.',
 'Nhập số dư đầu kỳ bằng file mẫu (tiền, ngân hàng, công nợ từng nhà cung cấp / khách hàng, vốn…). Không nhập lại tồn kho nếu kho đã có giá trị trong Lotus.',
 'Chọn vùng lương tối thiểu (trần BHTN) và nhập giá thành kế hoạch chuối thu hoạch (đ / kg).',
 'Xem "Tham số lương theo pháp luật" ở Thiết lập: giảm trừ gia cảnh, biểu thuế, tỷ lệ bảo hiểm và nguồn văn bản. Dòng ghi "chưa xác nhận" chưa được áp dụng.',
 'Khóa sổ các tháng trước ngày bắt đầu để không ai ghi nhầm vào.',
 'Bật "Ghi sổ kế toán từ Lotus". Từ đó phiếu xuất kho bắt buộc có lô, phiếu nhập bắt buộc có lý do.',
]
const DAILY=[
 ['Kho','Phiếu nhập: chọn lý do — Mua ngoài (chọn nhà cung cấp), Thu hồi vật tư (ghi mã lô thu về), Thừa kiểm kê. Phiếu xuất: gõ mã lô đầu ô lô (VD "A-1 / thửa 2"), danh sách gợi ý có sẵn. Kiểm kê thừa và thiếu lập hai phiếu riêng.'],
 ['Kho / xưởng — chuối thu hoạch','Lô thu hoạch đã xác nhận hiện ở Chờ hạch toán › Lô thu hoạch chưa nhập kho → Nhập kho. Không lập phiếu nhập chuối bằng tay trong Desk. Bao bì đóng gói xuất với mục đích "Xuất bao bì đóng gói".'],
 ['Kế toán — mua hàng','Chờ hạch toán: chọn các phiếu nhận hàng cùng nhà cung cấp → Lập hóa đơn (số, ngày hóa đơn, thuế suất GTGT). Xem "Xuất kho chưa gắn lô" và nhắc kho sửa.'],
 ['Kế toán — bán hàng','Bán hàng – Phải thu › Lập hóa đơn bán: chọn khách hàng, hàng trong kho thành phẩm, số lượng, đơn giá, thuế suất (chuối của vườn: Không chịu thuế), ký hiệu và số hóa đơn điện tử. Hóa đơn xuất kho luôn.'],
 ['Kế toán — thu tiền','Bán hàng – Phải thu › Thu tiền ở dòng khách hàng: nhập số tiền thu từng hóa đơn, tiền mặt hay chuyển khoản (số báo có). Phiếu thu ghi sổ ngay, không cần ký.'],
 ['Kế toán — trả tiền','Công nợ phải trả → Lập phiếu chi: nhập số tiền trả từng hóa đơn, tiền mặt hay chuyển khoản (ghi số ủy nhiệm chi), chọn Kế toán trưởng và Giám đốc ký. Phiếu chỉ ghi sổ khi Giám đốc ký xong.'],
 ['Kế toán — chi phí dịch vụ','Công nợ phải trả → Hóa đơn dịch vụ / chi phí: thuê máy, vận chuyển cho lô chọn "Sản xuất" và vườn / lô; chi phí văn phòng chọn "Quản lý". Chọn thuế suất GTGT theo hóa đơn.'],
 ['Kế toán trưởng / Giám đốc','Thông báo "Đến lượt bạn ký" → Thu / Chi (hoặc trang Phiếu chi chờ ký) → Ký hoặc Trả lại kèm lý do.'],
]
const MONTH=[
 'Mở Thiết lập › Đóng tháng — danh sách kiểm tra, chọn tháng. Lotus tự đánh dấu bước nào đã xong; làm lần lượt từ trên xuống.',
 'Chờ hạch toán trống: mọi phiếu nhận hàng đã có hóa đơn, không còn dòng xuất kho thiếu lô, lô thu hoạch đã nhập kho.',
 'Bảng lương tháng đã ký đủ → Chờ hạch toán › Xem trước bút toán → Ghi sổ. Sau đó lập phiếu chi lương ở Thu / Chi (Lotus trừ phần đã tạm ứng) và tải danh sách chuyển khoản.',
 'Nộp bảo hiểm, kinh phí công đoàn, thuế TNCN của tháng trước: Thu / Chi › Nộp BH, KPCĐ, thuế TNCN.',
 'Phiếu chi trong tháng đã ký xong hoặc đã hủy.',
 'Thiết lập › Kết chuyển CP của tháng: chuyển 621 / 622 / 627 sang 154 theo từng lô.',
 'Thiết lập › Giá thành của tháng: xem bảng giá thành từng lô (dở dang, chi phí, kg thu, kg dự thu còn lại, giá / kg) rồi Ghi sổ giá thành. Chênh lệch với giá tạm tính vào 632.',
 'Thiết lập › KQKD 911: kết chuyển doanh thu, chi phí của tháng sang 911 và lãi / lỗ sang 4212.',
 'Báo cáo › Đối chiếu: mọi dòng "Khớp". Báo cáo › Bảng cân đối phát sinh: Nợ = Có. Báo cáo › B01: tài sản = nguồn vốn. Báo cáo › Thuế GTGT: bảng kê khớp sổ.',
 'Thiết lập › Khóa tháng. Muốn sửa sau khi khóa: Kế toán trưởng mở lại kỳ kèm lý do.',
]
const TAX=[
 ['Thuế TNCN — nhân viên có hợp đồng từ 3 tháng','Tính theo biểu lũy tiến 5 bậc sau khi trừ bảo hiểm người lao động, giảm trừ bản thân 15,5 triệu và 6,2 triệu / người phụ thuộc (từ kỳ tính thuế 2026). Phần lương làm đêm, tăng ca cao hơn giờ thường không chịu thuế.'],
 ['Thuế TNCN — thời vụ, thử việc, hợp đồng dưới 3 tháng','Khấu trừ 10% mỗi lần trả từ 2 triệu đồng. Người đã nộp cam kết 08/CK-TNCN (đánh dấu trong hồ sơ nhân viên) thì không khấu trừ.'],
 ['Người phụ thuộc','Nhân sự nhập số người phụ thuộc đã đăng ký với cơ quan thuế trong hồ sơ nhân viên (mục Giấy tờ & bảo hiểm). Bảng lương lấy số này khi tính.'],
 ['Bảo hiểm','Người lao động 10,5% (BHXH 8%, BHYT 1,5%, BHTN 1%), doanh nghiệp 21,5% (17,5% + 3% + 1%) trên lương hợp đồng, tối đa 20 lần lương cơ sở (BHXH, BHYT) và 20 lần lương tối thiểu vùng (BHTN). Chỉ tính khi nhân viên có số BHXH.'],
 ['Kinh phí công đoàn','Doanh nghiệp trích 2% quỹ lương đóng BHXH, tính vào chi phí nhân công (622 / 6421), ghi Có 3382.'],
 ['Tạm ứng lương','Thu / Chi › Tạm ứng lương: chọn nhân viên, số tiền, tháng lương sẽ trừ; ký 3 bước như phiếu chi. Khi chi lương tháng đó Lotus tự trừ.'],
 ['Tham số thay đổi','Mức giảm trừ, biểu thuế, tỷ lệ bảo hiểm, lương cơ sở là dữ liệu có ngày hiệu lực (lotus_farm/data/payroll_vn.json), xem ở Thiết lập. Khi Nhà nước thay đổi, chỉ cần thêm một dòng mới.'],
]
const ENTRIES=[
 ['Nhận hàng theo đơn mua','Kho','Nợ 152 / Có 3388'],
 ['Nhập mua ngoài không qua đơn mua','Kho','Nợ 152 / Có 3388 (chờ hóa đơn)'],
 ['Hóa đơn mua hàng','Kế toán','Nợ 3388, Nợ 1331 (thuế) / Có 331'],
 ['Hóa đơn dịch vụ cho lô','Kế toán','Nợ 6277 (vườn / lô), Nợ 1331 / Có 331'],
 ['Hóa đơn dịch vụ quản lý','Kế toán','Nợ 6427, Nợ 1331 / Có 331'],
 ['Trả tiền nhà cung cấp','Kế toán → KTT → GĐ','Nợ 331 / Có 111 hoặc 112'],
 ['Xuất vật tư cho lô','Kho','Nợ 621 (vườn / lô / công việc) / Có 152'],
 ['Thu hồi vật tư thừa về kho','Kho','Nợ 152 / Có 621 (lô thu hồi)'],
 ['Kiểm kê thừa / thiếu','Kho','Nợ 152 / Có 3381 — Nợ 1381 / Có 152'],
 ['Xuất bao bì đóng gói','Kho','Nợ 6272 (vườn) / Có 152'],
 ['Nhập kho chuối thu hoạch','Kho / kế toán','Nợ 155 / Có 154 (lô trồng) theo giá tạm tính / kg'],
 ['Hóa đơn bán hàng (xuất kho luôn)','Kế toán','Nợ 632 / Có 155 — Nợ 131 / Có 511, 33311'],
 ['Thu tiền khách hàng','Kế toán','Nợ 111 hoặc 112 / Có 131'],
 ['Lương công nhân có công ở lô','Kế toán','Nợ 622 (theo số công từng lô) / Có 334'],
 ['Lương nhân viên gián tiếp','Kế toán','Nợ 6421 / Có 334'],
 ['Bảo hiểm, KPCĐ','Kế toán','Có 3383 BHXH, 3384 BHYT, 3386 BHTN, 3382 KPCĐ'],
 ['Thuế TNCN khấu trừ từ lương','Kế toán','Nợ 334 / Có 3335 (trong bút toán lương)'],
 ['Tiền khoán đội','Kế toán','Nợ 622 (vườn / công việc) / Có 334'],
 ['Tạm ứng lương','Kế toán → KTT → GĐ','Nợ 334 / Có 111 hoặc 112'],
 ['Chi lương','Kế toán → KTT → GĐ','Nợ 334 / Có 112 hoặc 111 (thực lĩnh trừ tạm ứng)'],
 ['Nộp bảo hiểm, KPCĐ, thuế TNCN','Kế toán → KTT → GĐ','Nợ 3383, 3384, 3386, 3382, 3335 / Có 112'],
 ['Kết chuyển chi phí cuối tháng','Kế toán trưởng','Nợ 154 / Có 621, 622, 627 (giữ vườn / lô)'],
 ['Giá thành cuối tháng','Kế toán trưởng','Thực tế cao hơn tạm tính: Nợ 632 / Có 154; thấp hơn: Nợ 154 / Có 632 (theo lô)'],
 ['Kết chuyển kết quả kinh doanh','Kế toán trưởng','Nợ 511, 515, 711 / Có 911 — Nợ 911 / Có 632, 635, 641, 642, 811, 821 — lãi Nợ 911 / Có 4212'],
]
const REPORTS=[
 ['B01-DN Báo cáo tình hình tài chính','Số dư mọi tài khoản tại ngày "Đến", so với 31/12 năm trước. Công nợ tách theo từng đối tượng: dư Nợ vào tài sản, dư Có vào nợ phải trả. Dòng kiểm tra phải "Khớp" (tài sản = nguồn vốn).'],
 ['B02-DN Báo cáo kết quả hoạt động kinh doanh','Phát sinh trong khoảng Từ – Đến, không tính bút toán kết chuyển 911, so với cùng kỳ năm trước.'],
 ['B03-DN Báo cáo lưu chuyển tiền tệ (gián tiếp)','Từ lợi nhuận trước thuế cộng biến động các tài khoản khác; tiền cuối kỳ (70) phải bằng số dư 111 + 112 + 113.'],
 ['Nhật ký chung, sổ cái','Nhật ký chung: mọi dòng sổ theo ngày. Sổ cái / sổ quỹ / sổ tiền gửi: chọn tài khoản (111 là sổ quỹ tiền mặt, 112 là sổ tiền gửi), có cột tài khoản đối ứng và số dư lũy kế; nhập mã đối tượng để xem sổ chi tiết công nợ.'],
 ['Công nợ theo đối tượng','Bảng tổng hợp chi tiết 131 / 331 / 334 / 141: dư đầu, phát sinh, dư cuối từng khách hàng, nhà cung cấp, nhân viên. Bấm một dòng để mở sổ chi tiết.'],
 ['Nhập – xuất – tồn','Số lượng và giá trị theo từng hàng, từng kho trong kỳ, từ sổ kho.'],
 ['Thuế GTGT','Bảng kê hóa đơn mua vào / bán ra theo tháng, tổng hợp số liệu tờ khai 01/GTGT (tham khảo để khai trên HTKK / eTax), đối chiếu với 1331 / 33311.'],
 ['Đối chiếu ngân hàng','Tải sao kê Excel của ngân hàng: Lotus so với sổ 112 theo số tiền, số tham chiếu và ngày (± 3 ngày), liệt kê giao dịch chỉ có trên sao kê (phí, lãi, tiền về chưa ghi) và chỉ có trên sổ.'],
 ['Mẫu biểu','Mã số và tên chỉ tiêu theo mẫu kèm Thông tư 99/2025/TT-BTC; tài khoản lấy vào từng chỉ tiêu là dữ liệu (lotus_farm/data/bctc_tt99.json). Kế toán trưởng đối chiếu trước khi nộp báo cáo năm.'],
]
const FIX=[
 ['Hóa đơn, phiếu chi đã ghi sổ bị sai','Kế toán trưởng: Thu / Chi hoặc Nhật ký → Đảo (ghi lý do). Lotus hủy chứng từ, sổ cái tự có bút toán đảo, rồi lập lại chứng từ đúng.'],
 ['Bảng lương đã ghi sổ cần sửa','Đảo bút toán lương trước, rồi Nhân sự mới mở lại kỳ công được.'],
 ['Phiếu chi bị trả lại','Người lập xem lý do, hủy phiếu và lập lại.'],
 ['Cần kết chuyển hoặc tính giá thành lại','Đảo theo thứ tự ngược: kết chuyển 911 → giá thành → kết chuyển chi phí, rồi làm lại từ đầu.'],
 ['Tháng đã khóa nhưng cần sửa','Kế toán trưởng mở lại kỳ (bắt buộc lý do, có lưu vết), sửa, rồi khóa lại.'],
 ['Số dư treo cần phân loại lại (VD 3381)','Thiết lập › Bút toán điều chỉnh: xem sổ chi tiết tài khoản, nhập các dòng Nợ / Có, xem trước rồi ghi sổ.'],
 ['Hóa đơn bán sai','Kế toán trưởng đảo hóa đơn (hàng trả lại kho, công nợ và doanh thu giảm) rồi lập hóa đơn đúng; trên hệ thống hóa đơn điện tử lập hóa đơn điều chỉnh / thay thế theo quy định.'],
]
const FAQ=[
 ['Vì sao không lưu được phiếu xuất kho?','Ghi sổ đang bật: mỗi dòng phải có mã lô có trong danh sách để chi phí vào đúng lô.'],
 ['Vì sao Giám đốc không thấy sổ sách?','Người duyệt chi chỉ thấy phiếu chờ mình ký. Muốn xem sổ cần vai trò Kế toán / Kế toán trưởng / Kiểm soát.'],
 ['Ngày nhập ở đâu cũng là dd/mm/yyyy?','Đúng, các ô ngày trong màn kế toán nhập theo ngày/tháng/năm.'],
 ['Chuối bán ra có thuế GTGT không?','Chuối do vườn tự trồng, chưa chế biến hoặc chỉ sơ chế thông thường (rửa, đóng thùng) bán ra không chịu thuế GTGT (Luật 48/2024/QH15 Điều 5): chọn "Không chịu thuế". Hàng khác chọn đúng thuế suất trên hóa đơn.'],
 ['Giá thành chuối tính thế nào?','Mỗi lô: (dở dang 154 đầu tháng + chi phí kết chuyển trong tháng) × kg thu ÷ (kg thu + kg dự thu còn lại của lô). Vụ đã đóng thì dồn hết. Chi phí chung của vườn chia theo kg của cả vườn. Phần chưa thu nằm lại 154.'],
 ['Đã tính giá thành nhưng cần tính lại?','Kế toán trưởng đảo bút toán giá thành của tháng (Nhật ký → Đảo), rồi tính lại. Nếu đã kết chuyển 911 thì đảo bút toán đó trước.'],
 ['Lotus có nộp tờ khai thuế, hóa đơn điện tử không?','Chưa: Lotus lập số liệu và bảng kê; kế toán khai trên HTKK / eTax và lập hóa đơn trên phần mềm hóa đơn điện tử, rồi nhập số hóa đơn vào Lotus.'],
]
</script>

<template>
<section class="fin-guide" aria-label="Hướng dẫn vận hành">
 <nav class="fin-guide__nav" aria-label="Mục hướng dẫn"><button v-for="[id,label] in SECTIONS" :key="id" type="button" :class="{on:open===id}" :aria-pressed="open===id" @click="open=id">{{label}}</button></nav>
 <article v-if="open==='roles'" class="land-card"><h3>Ai làm gì</h3>
  <dl class="fin-guide__pairs"><template v-for="[who,what] in ROLES" :key="who"><dt>{{who}}</dt><dd>{{what}}</dd></template></dl>
  <p class="land-note">Gán vai trò ở <a href="#" @click.prevent="emit('go','settings')">Thiết lập › Người làm kế toán</a>.</p></article>
 <article v-else-if="open==='start'" class="land-card"><h3>Bắt đầu (làm một lần)</h3><ol class="fin-guide__steps"><li v-for="s in START" :key="s">{{s}}</li></ol></article>
 <article v-else-if="open==='daily'" class="land-card"><h3>Việc hằng ngày</h3>
  <dl class="fin-guide__pairs"><template v-for="[who,what] in DAILY" :key="who"><dt>{{who}}</dt><dd>{{what}}</dd></template></dl></article>
 <article v-else-if="open==='month'" class="land-card"><h3>Cuối tháng (theo đúng thứ tự)</h3><ol class="fin-guide__steps"><li v-for="s in MONTH" :key="s">{{s}}</li></ol>
  <p class="land-note">Danh sách kiểm tra tự động ở <a href="#" @click.prevent="emit('go','settings')">Thiết lập › Đóng tháng</a>.</p></article>
 <article v-else-if="open==='tax'" class="land-card"><h3>Lương, bảo hiểm và thuế thu nhập cá nhân</h3>
  <dl class="fin-guide__pairs"><template v-for="[what,how] in TAX" :key="what"><dt>{{what}}</dt><dd>{{how}}</dd></template></dl></article>
 <article v-else-if="open==='entries'" class="land-card"><h3>Định khoản từng nghiệp vụ (Thông tư 99)</h3>
  <div class="fin-guide__grid" role="list"><div class="fin-guide__row fin-guide__row--head" aria-hidden="true"><span>Nghiệp vụ</span><span>Ai lập</span><span>Bút toán</span></div>
   <div v-for="[what,who,entry] in ENTRIES" :key="what" class="fin-guide__row" role="listitem"><b>{{what}}</b><span>{{who}}</span><code>{{entry}}</code></div></div>
  <p class="land-note">Vườn / Lô / Vụ / Công việc là chiều phân tích trên từng dòng sổ cái, không phải tài khoản con. Báo cáo › Chi phí theo vườn / lô đọc từ đó.</p></article>
 <article v-else-if="open==='reports'" class="land-card"><h3>Báo cáo tài chính và sổ sách</h3>
  <dl class="fin-guide__pairs"><template v-for="[what,how] in REPORTS" :key="what"><dt>{{what}}</dt><dd>{{how}}</dd></template></dl>
  <p class="land-note">Mọi báo cáo xuất được Excel (có chỗ ký Người lập, Kế toán trưởng, Người đại diện theo pháp luật) ở <a href="#" @click.prevent="emit('go','reports')">Báo cáo</a>.</p></article>
 <article v-else-if="open==='fix'" class="land-card"><h3>Sửa sai</h3>
  <dl class="fin-guide__pairs"><template v-for="[what,how] in FIX" :key="what"><dt>{{what}}</dt><dd>{{how}}</dd></template></dl>
  <p class="land-note">Không sửa trực tiếp bút toán đã ghi sổ: luôn đảo rồi lập lại để giữ lịch sử.</p></article>
 <article v-else class="land-card"><h3>Câu hỏi thường gặp</h3>
  <dl class="fin-guide__pairs"><template v-for="[q,a] in FAQ" :key="q"><dt>{{q}}</dt><dd>{{a}}</dd></template></dl></article>
</section>
</template>

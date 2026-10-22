<script setup>
// Sổ tay vận hành Tài chính – Kế toán (tab Hướng dẫn). Static content: who does what, the one-time setup, the daily work
// of each department, month-end, how each Lotus document posts (Thông tư 99) and how to correct a mistake.
import {ref} from 'vue'
const emit=defineEmits(['go'])
const open=ref('roles')
const SECTIONS=[['roles','Ai làm gì'],['start','Bắt đầu (một lần)'],['daily','Việc hằng ngày'],['month','Cuối tháng'],['entries','Định khoản từng nghiệp vụ'],['fix','Sửa sai'],['faq','Câu hỏi thường gặp']]
const ROLES=[
 ['Thủ kho / nhân viên kho','Lập phiếu nhập (chọn đúng lý do nhập), phiếu xuất (ghi mã lô ở ô "Khu vực / lô sử dụng"), kiểm kê. Không cần vào màn kế toán.'],
 ['Mua hàng','Đề xuất mua → đơn mua → nhận hàng. Hàng mua không qua đơn mua thì kho nhập với lý do "Mua ngoài" và chọn nhà cung cấp.'],
 ['Nhân sự','Chấm công, chốt và gửi ký bảng công & bảng lương. Khi bảng lương ký đủ, kế toán ghi sổ ở Chờ hạch toán (không dùng phiếu lương HRMS).'],
 ['Kế toán (Lotus Accountant)','Lập hóa đơn mua từ phiếu nhận hàng, hóa đơn dịch vụ, phiếu chi / ủy nhiệm chi, ghi sổ lương; xem mọi báo cáo.'],
 ['Kế toán trưởng (Lotus Chief Accountant)','Ký phiếu chi bước 2, đảo bút toán, bút toán điều chỉnh, kết chuyển chi phí, khóa / mở kỳ, cấu hình tài khoản.'],
 ['Giám đốc (người duyệt mua / Quản lý vườn)','Ký bước cuối phiếu chi — chữ ký cuối mới làm phiếu chi ghi sổ. Chỉ thấy phiếu chờ mình ký.'],
 ['Quản trị hệ thống','Gán vai trò Kế toán / Kế toán trưởng ở Thiết lập › Người làm kế toán.'],
]
const START=[
 'Quản trị gán vai trò: ít nhất một Kế toán trưởng và một Kế toán (Thiết lập › Người làm kế toán). Người ký bước Giám đốc cần có vai trò Người duyệt mua hoặc Quản lý vườn và có hồ sơ nhân viên gắn tài khoản.',
 'Kế toán trưởng áp dụng hệ thống tài khoản Thông tư 99 (Thiết lập › Hệ thống tài khoản) và kiểm tra tài khoản cho từng nghiệp vụ.',
 'Chọn ngày bắt đầu ghi sổ (cutover) — nên là ngày đầu tháng. Chứng từ trước ngày này nằm trong số dư đầu kỳ, Lotus không ghi sổ lại.',
 'Nhập số dư đầu kỳ bằng file mẫu (tiền, ngân hàng, công nợ từng nhà cung cấp, vốn…). Không nhập lại tồn kho nếu kho đã có giá trị trong Lotus.',
 'Khóa sổ các tháng trước ngày bắt đầu để không ai ghi nhầm vào.',
 'Bật "Ghi sổ kế toán từ Lotus". Từ đó phiếu xuất kho bắt buộc có lô, phiếu nhập bắt buộc có lý do.',
]
const DAILY=[
 ['Kho','Phiếu nhập: chọn lý do — Mua ngoài (chọn nhà cung cấp), Thu hồi vật tư (ghi mã lô thu về), Thừa kiểm kê. Phiếu xuất: gõ mã lô đầu ô lô (VD "A-1 / thửa 2"), danh sách gợi ý có sẵn. Kiểm kê thừa và thiếu lập hai phiếu riêng.'],
 ['Kế toán — mỗi ngày','Mở Chờ hạch toán: chọn các phiếu nhận hàng cùng nhà cung cấp → Lập hóa đơn (số, ngày hóa đơn). Xem "Xuất kho chưa gắn lô" và nhắc kho sửa.'],
 ['Kế toán — khi trả tiền','Công nợ phải trả → Lập phiếu chi: nhập số tiền trả từng hóa đơn, tiền mặt hay chuyển khoản (ghi số ủy nhiệm chi), chọn Kế toán trưởng và Giám đốc ký. Phiếu chỉ ghi sổ khi Giám đốc ký xong.'],
 ['Kế toán — chi phí dịch vụ','Công nợ phải trả → Hóa đơn dịch vụ / chi phí: thuê máy, vận chuyển cho lô chọn "Sản xuất" và vườn / lô; chi phí văn phòng chọn "Quản lý".'],
 ['Kế toán trưởng / Giám đốc','Thông báo "Đến lượt bạn ký" → Thu / Chi (hoặc trang Phiếu chi chờ ký) → Ký hoặc Trả lại kèm lý do.'],
]
const MONTH=[
 'Chờ hạch toán trống: mọi phiếu nhận hàng đã có hóa đơn, không còn dòng xuất kho thiếu lô.',
 'Bảng lương tháng đã ký đủ → Chờ hạch toán › Xem trước bút toán → Ghi sổ. Sau đó lập phiếu chi lương ở Thu / Chi.',
 'Phiếu chi trong tháng đã ký xong hoặc đã hủy.',
 'Thiết lập › Kết chuyển CP của tháng: chuyển 621 / 622 / 627 sang 154 theo từng lô.',
 'Báo cáo › Đối chiếu: mọi dòng "Khớp". Báo cáo › Bảng cân đối phát sinh: Nợ = Có.',
 'Thiết lập › Khóa tháng. Muốn sửa sau khi khóa: Kế toán trưởng mở lại kỳ kèm lý do.',
]
const ENTRIES=[
 ['Nhận hàng theo đơn mua','Kho','Nợ 152 / Có 3388'],
 ['Nhập mua ngoài không qua đơn mua','Kho','Nợ 152 / Có 3388 (chờ hóa đơn)'],
 ['Hóa đơn mua hàng','Kế toán','Nợ 3388 / Có 331 (từng nhà cung cấp)'],
 ['Hóa đơn dịch vụ cho lô','Kế toán','Nợ 6277 (vườn / lô) / Có 331'],
 ['Hóa đơn dịch vụ quản lý','Kế toán','Nợ 6427 / Có 331'],
 ['Trả tiền nhà cung cấp','Kế toán → KTT → GĐ','Nợ 331 / Có 111 hoặc 112'],
 ['Xuất vật tư cho lô','Kho','Nợ 621 (vườn / lô / công việc) / Có 152'],
 ['Thu hồi vật tư thừa về kho','Kho','Nợ 152 / Có 621 (lô thu hồi)'],
 ['Kiểm kê thừa / thiếu','Kho','Nợ 152 / Có 3381 — Nợ 1381 / Có 152'],
 ['Xuất bán, xuất hủy (ngoài form kho)','Kho','Nợ 632 hoặc 811 / Có 152, 155'],
 ['Lương công nhân có công ở lô','Kế toán','Nợ 622 (theo số công từng lô) / Có 334'],
 ['Lương nhân viên gián tiếp','Kế toán','Nợ 6421 / Có 334'],
 ['Bảo hiểm (người lao động + doanh nghiệp)','Kế toán','Có 3383 BHXH, 3384 BHYT, 3386 BHTN'],
 ['Tiền khoán đội','Kế toán','Nợ 622 (vườn / công việc) / Có 334'],
 ['Chi lương','Kế toán → KTT → GĐ','Nợ 334 / Có 112 hoặc 111'],
 ['Kết chuyển chi phí cuối tháng','Kế toán trưởng','Nợ 154 / Có 621, 622, 627 (giữ vườn / lô)'],
]
const FIX=[
 ['Hóa đơn, phiếu chi đã ghi sổ bị sai','Kế toán trưởng: Thu / Chi hoặc Nhật ký → Đảo (ghi lý do). Lotus hủy chứng từ, sổ cái tự có bút toán đảo, rồi lập lại chứng từ đúng.'],
 ['Bảng lương đã ghi sổ cần sửa','Đảo bút toán lương trước, rồi Nhân sự mới mở lại kỳ công được.'],
 ['Phiếu chi bị trả lại','Người lập xem lý do, hủy phiếu và lập lại.'],
 ['Tháng đã khóa nhưng cần sửa','Kế toán trưởng mở lại kỳ (bắt buộc lý do, có lưu vết), sửa, rồi khóa lại.'],
 ['Số dư treo cần phân loại lại (VD 3381)','Thiết lập › Bút toán điều chỉnh: xem sổ chi tiết tài khoản, nhập các dòng Nợ / Có, xem trước rồi ghi sổ.'],
]
const FAQ=[
 ['Vì sao không lưu được phiếu xuất kho?','Ghi sổ đang bật: mỗi dòng phải có mã lô có trong danh sách để chi phí vào đúng lô.'],
 ['Vì sao Giám đốc không thấy sổ sách?','Người duyệt chi chỉ thấy phiếu chờ mình ký. Muốn xem sổ cần vai trò Kế toán / Kế toán trưởng / Kiểm soát.'],
 ['Ngày nhập ở đâu cũng là dd/mm/yyyy?','Đúng, các ô ngày trong màn kế toán nhập theo ngày/tháng/năm.'],
 ['Có VAT chưa?','Chưa ở bản này: hóa đơn mua ghi tổng tiền. VAT, bán hàng, giá thành, báo cáo tài chính đang được bổ sung.'],
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
 <article v-else-if="open==='month'" class="land-card"><h3>Cuối tháng (theo đúng thứ tự)</h3><ol class="fin-guide__steps"><li v-for="s in MONTH" :key="s">{{s}}</li></ol></article>
 <article v-else-if="open==='entries'" class="land-card"><h3>Định khoản từng nghiệp vụ (Thông tư 99)</h3>
  <div class="fin-guide__grid" role="list"><div class="fin-guide__row fin-guide__row--head" aria-hidden="true"><span>Nghiệp vụ</span><span>Ai lập</span><span>Bút toán</span></div>
   <div v-for="[what,who,entry] in ENTRIES" :key="what" class="fin-guide__row" role="listitem"><b>{{what}}</b><span>{{who}}</span><code>{{entry}}</code></div></div>
  <p class="land-note">Vườn / Lô / Vụ / Công việc là chiều phân tích trên từng dòng sổ cái, không phải tài khoản con. Báo cáo › Chi phí theo vườn / lô đọc từ đó.</p></article>
 <article v-else-if="open==='fix'" class="land-card"><h3>Sửa sai</h3>
  <dl class="fin-guide__pairs"><template v-for="[what,how] in FIX" :key="what"><dt>{{what}}</dt><dd>{{how}}</dd></template></dl>
  <p class="land-note">Không sửa trực tiếp bút toán đã ghi sổ: luôn đảo rồi lập lại để giữ lịch sử.</p></article>
 <article v-else class="land-card"><h3>Câu hỏi thường gặp</h3>
  <dl class="fin-guide__pairs"><template v-for="[q,a] in FAQ" :key="q"><dt>{{q}}</dt><dd>{{a}}</dd></template></dl></article>
</section>
</template>

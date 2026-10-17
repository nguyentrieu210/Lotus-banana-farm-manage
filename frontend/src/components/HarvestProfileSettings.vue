<script setup>
import {computed} from 'vue'
import SchemaForm from './SchemaForm.vue'

const props=defineProps({
 schema:{type:Object,default:()=>({fields:[],tables:{}})},
 model:{type:Object,required:true},
 scope:{type:Object,default:()=>({})},
 readonly:Boolean,
})

const sections=[
 {
  id:'scope',title:'1. Áp dụng cho vườn nào?',description:'Đặt tên cho bộ hệ số. Chọn vườn; nếu mọi lô của vườn dùng chung thì để ô Lô trống.',
  fields:['profile_name','farm','farm_block','variety','cycle_type','valid_from','valid_to'],
 },
 {
  id:'timing',title:'2. Bao lâu thì đến kỳ thu?',description:'Nhập số NGÀY tính từ từng mốc đến ngày dự kiến thu hoạch. Có mốc nào thì hệ thống lấy mốc đó theo thứ tự ưu tiên.',
  fields:['planting_to_harvest_days','sucker_to_harvest_days','shooting_to_harvest_days','cut_bud_to_harvest_days','ratoon_interval_days'],
 },
 {
  id:'yield',title:'3. Một buồng cho ra bao nhiêu kg?',description:'Các hệ số sau dùng để chuyển số buồng dự kiến thành tấn buồng và tấn thành phẩm.',
  fields:['avg_bunch_weight_kg','bunch_survival_rate_percent','quality_pass_rate_percent','packout_rate_percent','safety_buffer_percent'],
 },
 {
  id:'other',title:'Thiết lập nâng cao',description:'Thông tin quản trị và trạng thái duyệt. Thường không cần thay đổi khi nhập hệ số lần đầu.',
  fields:['approval_state','version','active','notes'],
 },
]
const help={
 profile_name:['Tên bộ hệ số','Ví dụ: Hệ số dự thu Vườn 222. Đây chỉ là tên để dễ nhận biết.'],
 farm:['Vườn áp dụng','Chọn Vườn 222 hoặc Vườn 180. Để trống khi bộ hệ số dùng chung nhiều vườn.'],
 farm_block:['Chỉ áp dụng cho lô (không bắt buộc)','Để trống nếu cùng hệ số cho toàn vườn. Chọn lô khi lô đó có chu kỳ khác biệt.'],
 variety:['Giống chuối (không bắt buộc)','Nếu chỉ áp dụng cho một giống cụ thể thì chọn giống; để trống nếu dùng chung.'],
 cycle_type:['Loại vụ (không bắt buộc)','Vụ trồng mới hoặc vụ chồi; để trống nếu hai loại dùng cùng hệ số.'],
 valid_from:['Bắt đầu áp dụng từ ngày','Bắt buộc nhập ngày bắt đầu áp dụng bộ hệ số, không phải ngày trồng cây.'],
 valid_to:['Ngày hết hiệu lực (không bắt buộc)','Nếu chưa quy định ngày kết thúc, có thể để trống.'],
 planting_to_harvest_days:['Từ trồng đến thu (ngày)','Khi lô chỉ có ngày trồng, hệ thống cộng số ngày này để tính kỳ thu dự kiến.'],
 sucker_to_harvest_days:['Từ chọn chồi đến thu (ngày)','Khi đã có ngày chọn chồi, dùng mốc này thay cho dự tính từ ngày trồng của cùng đợt.'],
 shooting_to_harvest_days:['Từ trổ buồng đến thu (ngày)','Khi đã ghi nhận trổ buồng, dùng mốc này thay cho ngày chọn chồi của cùng đợt.'],
 cut_bud_to_harvest_days:['Từ cắt bắp đến thu (ngày)','Nguồn gần thu nhất; ưu tiên dùng số buồng và ngày cắt bắp đã ghi nhận.'],
 ratoon_interval_days:['Khoảng cách giữa hai vụ chồi (ngày)','Dự phóng các vụ chồi tương lai trong kế hoạch 3 năm khi chưa có ngày chọn chồi thực tế.'],
 avg_bunch_weight_kg:['Kg trung bình mỗi buồng','Nhập khối lượng buồng dự kiến, lấy từ đo đạc hoặc số liệu vườn đã xác nhận.'],
 bunch_survival_rate_percent:['Tỷ lệ buồng còn thu được (%)','Ví dụ 90 nghĩa là cứ 100 buồng dự tính thì còn 90 buồng được thu; không phải nhập 0,9.'],
 quality_pass_rate_percent:['Tỷ lệ đạt chất lượng (%)','Ví dụ 80 nghĩa là 100 kg buồng thì có 80 kg đạt yêu cầu trước bước đóng gói.'],
 packout_rate_percent:['Tỷ lệ ra thành phẩm (%)','Ví dụ 75 nghĩa là 100 kg đạt chất lượng cho 75 kg thành phẩm đóng gói.'],
 safety_buffer_percent:['Tỷ lệ dự phòng khi giữ hàng (%)','Là phần dự trữ an toàn khi tính hàng có thể cam kết; không làm giảm tấn dự thu hiển thị trong bảng 3 năm.'],
 approval_state:['Tình trạng duyệt','Bản nháp để thiết lập/kiểm tra. Chỉ bộ hệ số đã được duyệt mới tham gia tính dự thu tự động.'],
 version:['Lần cập nhật','Thông thường giữ số hệ thống đang có. Không tự tăng số khi chưa có quy trình duyệt phiên bản.'],
 active:['Đang sử dụng','Bỏ chọn khi không muốn hệ số này tiếp tục được chọn cho dự báo mới.'],
 notes:['Ghi chú / nguồn số liệu','Nên ghi rõ người xác nhận, thời điểm khảo sát và cách đo các hệ số.'],
}
const makeSchema=section=>({
 fields:(props.schema?.fields||[])
  .filter(f=>section.fields.includes(f.fieldname))
  .sort((a,b)=>section.fields.indexOf(a.fieldname)-section.fields.indexOf(b.fieldname))
  .map(f=>({...f,display_label:help[f.fieldname]?.[0]||f.label,
    description:help[f.fieldname]?.[1]||f.description})),
 tables:props.schema?.tables||{},
})
const inputValue=name=>{
 const value=props.model[name]
 return value===null||value===undefined||value===''?null:Number(value)
}
const example=computed(()=>{
 const weight=inputValue('avg_bunch_weight_kg')
 const survival=inputValue('bunch_survival_rate_percent')
 const quality=inputValue('quality_pass_rate_percent')
 const packout=inputValue('packout_rate_percent')
 if(![weight,survival,quality,packout].every(v=>v!==null&&Number.isFinite(v)))return null
 if(weight<=0||[survival,quality,packout].some(v=>v<0||v>100))return null
 const bunches=1000*survival/100
 const gross=bunches*weight
 const packed=gross*quality/100*packout/100
 return {bunches,gross,packed}
})
const number=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(n)
</script>

<template>
 <div class="harvest-settings">
  <div class="harvest-settings__lead">
   <strong>Chỉ thiết lập cách TÍNH dự thu tại đây.</strong>
   <p>Ngày trồng thật của từng lô nhập trong <b>Thông tin Lô</b>. Số buồng trổ hoặc cắt bắp lấy từ bản ghi ngoài vườn, không phải nhập lại ở bảng này.</p>
  </div>

  <section v-for="section in sections.slice(0,3)" :key="section.id" class="harvest-settings__section">
   <header><h3>{{section.title}}</h3><p>{{section.description}}</p></header>
   <div v-if="section.id==='timing'" class="harvest-settings__priority">
    <span>Ưu tiên nguồn dự thu:</span>
    <strong>Cắt bắp</strong> → <strong>Trổ buồng</strong> → <strong>Chọn chồi</strong> → <strong>Ngày trồng</strong> → <strong>Vụ chồi dự phóng</strong>
   </div>
   <SchemaForm :schema="makeSchema(section)" :model="model" :scope="scope" :readonly="readonly"/>
   <p v-if="section.id==='scope'" class="harvest-settings__hint">Một bộ hệ số cấp vườn dùng được cho nhiều lô. Nếu lô nào khác biệt mới cần bộ riêng.</p>
   <p v-if="section.id==='timing'" class="harvest-settings__hint">Chưa có số ngày được xác nhận thì để trống. Không nhập 0 để thay cho chưa biết, và không dùng ngày tháng làm số ngày.</p>
  </section>

  <section class="harvest-settings__section harvest-settings__preview">
   <h3>Thử cách tính từ các số vừa nhập</h3>
   <p>Đây là phép thử giả định có <b>1.000 buồng</b> để hiểu các tỷ lệ. Không tạo sản lượng thật hoặc lưu vào dự thu.</p>
   <div v-if="example" class="harvest-settings__numbers">
    <article><small>Buồng còn thu</small><strong>{{number(example.bunches)}} <em>buồng</em></strong></article>
    <article><small>Dự thu ngoài vườn</small><strong>{{number(example.gross/1000)}} <em>tấn buồng</em></strong></article>
    <article><small>Đóng gói dự kiến</small><strong>{{number(example.packed/1000)}} <em>tấn</em></strong></article>
   </div>
   <p v-else class="harvest-settings__hint">Nhập kg/buồng và đủ 3 tỷ lệ để xem phép thử. Không có số mặc định tự đặt.</p>
   <p class="harvest-settings__formula">Cách tính: số buồng × tỷ lệ còn thu × kg/buồng → tấn buồng; tiếp tục nhân tỷ lệ đạt chất lượng và tỷ lệ ra thành phẩm.</p>
  </section>

  <details class="harvest-settings__advanced">
   <summary>Thông tin nâng cao và trạng thái duyệt</summary>
   <p>Giữ nguyên quy trình phân quyền hiện tại. Nếu chưa được duyệt, bộ hệ số chưa tham gia tính dự thu 3 năm.</p>
   <SchemaForm :schema="makeSchema(sections[3])" :model="model" :scope="scope" :readonly="readonly"/>
  </details>
  <p class="harvest-settings__footer">Bấm <b>Lưu nháp</b> ở phía trên sau khi nhập. Bộ hệ số chỉ được dùng khi đã được người có quyền duyệt và bật trạng thái sử dụng.</p>
 </div>
</template>

<style scoped>
.harvest-settings{display:grid;gap:16px;padding:2px 0 16px;min-width:0;font-size:13px;line-height:1.55}
.harvest-settings__lead{padding:14px 16px;border-radius:10px;border:1px solid #d5e3dd;background:#f0f8f4;color:#235c47}
.harvest-settings__lead p{margin:5px 0 0;font-size:12px;line-height:1.6}
.harvest-settings__section{background:var(--lotus-surface,#fff);border:1px solid var(--lotus-border,#e5e8ec);border-radius:11px;padding:15px 17px;min-width:0}
.harvest-settings__section header{margin-bottom:13px}
.harvest-settings__section h3,.harvest-settings__preview h3{margin:0 0 3px;color:var(--lotus-text,#243143);font-size:15px;font-weight:700}
.harvest-settings__section header p,.harvest-settings__preview>p,.harvest-settings__advanced>p{margin:0 0 8px;color:var(--lotus-muted,#637286);font-size:12px}
.harvest-settings__section :deep(.schema-grid){margin:0;gap:12px}
.harvest-settings__section :deep(.schema-grid>label){min-width:0}
.harvest-settings__section :deep(.schema-grid>label>small){font-size:11px;line-height:1.5;color:var(--lotus-muted,#69798b)}
.harvest-settings__priority{background:var(--lotus-soft,#f6f7f9);padding:10px 12px;margin:0 0 12px;border-radius:8px;font-size:12px;line-height:1.8;color:var(--lotus-text,#334155)}
.harvest-settings__priority span{display:block;font-weight:650}
.harvest-settings__priority strong{font-weight:700}
.harvest-settings__hint{margin:8px 0 0;color:var(--lotus-muted,#68788a);font-size:12px}
.harvest-settings__preview{background:var(--lotus-soft,#f8fafb)}
.harvest-settings__numbers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:12px 0}
.harvest-settings__numbers article{background:var(--lotus-surface,#fff);border:1px solid var(--lotus-border,#e2e8ef);border-radius:8px;padding:12px;display:grid;gap:5px}
.harvest-settings__numbers small{color:var(--lotus-muted,#69798b)}
.harvest-settings__numbers strong{font-size:19px;letter-spacing:-.02em}
.harvest-settings__numbers em{font-size:12px;color:var(--lotus-muted,#637286);font-style:normal;font-weight:400}
.harvest-settings__formula{font-size:11px!important}
.harvest-settings__advanced{border:1px solid var(--lotus-border,#e5e8ee);border-radius:10px;padding:11px 15px}
.harvest-settings__advanced summary{cursor:pointer;font-weight:650;color:var(--lotus-text,#334155)}
.harvest-settings__advanced[open] summary{margin-bottom:12px}
.harvest-settings__footer{margin:0;font-size:12px;color:var(--lotus-muted,#637286)}
@media(max-width:720px){.harvest-settings__numbers{grid-template-columns:1fr}.harvest-settings__section{padding:12px}}
</style>

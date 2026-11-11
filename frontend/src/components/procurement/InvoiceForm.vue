<script setup>
// Nhập hóa đơn nhà cung cấp (spec 003, US5): kế toán tự gõ theo bản in. Các dòng điền sẵn từ phiếu nhận đã chọn (số lượng
// chưa có hóa đơn, đơn giá theo đơn); file gốc hiện ngay cạnh biểu mẫu (máy tính) hoặc mở bằng một chạm (điện thoại).
// Hệ thống không đọc số từ file. Máy chủ (finance.supplier_invoice.create) kiểm trùng, thuế, tổng in và ghi sổ.
import {computed,ref,watch} from 'vue'
import ResponsiveForm from '../form/ResponsiveForm.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import {Button} from '../ui/button'
import {FilePickerButton} from '../ui/file-input'
import {lotusMethod} from './use-procurement'
import {money} from '../../use-signing'
import {newKey} from '../../procurement'
import {unitLabel} from '../../units'
import {upload} from '../../api'

const props=defineProps({modelValue:Boolean,receipts:{type:Array,default:()=>[]},supplier:String,suppliers:{type:Array,default:()=>[]},mobile:Boolean,today:String,callFn:Function,uploader:Function})
const emit=defineEmits(['update:modelValue','created'])
const method=(name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.finance.supplier_invoice.'+name,args,write):lotusMethod('finance.supplier_invoice',name,args,write)
const VAT=[{value:'KCT',label:'Không chịu thuế'},{value:'0',label:'0%'},{value:'5',label:'5%'},{value:'8',label:'8%'},{value:'10',label:'10%'}]
const RATE={KCT:0,0:0,5:.05,8:.08,10:.1}
const busy=ref(false),error=ref(''),source=ref(null),lines=ref([]),services=ref([]),files=ref([]),added=ref([]),shown=ref(null),key=ref('')
const head=ref({supplier:'',bill_no:'',series:'',tax_code:'',bill_date:'',due_date:'',posting_date:'',printed_total:'',printed_vat:''})
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const serviceOnly=computed(()=>!props.receipts.length)
const fixed=computed(()=>!!source.value?.mua_nhanh)
const fmt=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const net=computed(()=>lines.value.reduce((sum,r)=>sum+Number(r.qty||0)*Number(r.rate||0),0)+services.value.reduce((sum,r)=>sum+Number(r.amount||0),0))
const vat=computed(()=>Math.round(lines.value.reduce((sum,r)=>sum+Number(r.qty||0)*Number(r.rate||0)*(RATE[r.vat_code]||0),0)+services.value.reduce((sum,r)=>sum+Number(r.amount||0)*(RATE[r.vat_code]||0),0)))
const freight=computed(()=>lines.value.reduce((sum,r)=>sum+Number(r.freight||0)*(Number(r.qty||0)/(Number(r.max_qty)||1)),0))
const total=computed(()=>Math.round(net.value+vat.value+freight.value))
const goodsLines=computed(()=>Math.max(1,lines.value.filter(r=>Number(r.qty)>0).length+services.value.length))
const gap=computed(()=>head.value.printed_total===''||head.value.printed_total==null?null:Math.round(Number(head.value.printed_total)-total.value))
const varies=row=>!row.fixed&&Math.abs(Number(row.rate||0)-Number(row.receipt_rate||0))>0.005
const problem=computed(()=>{
 if(!head.value.bill_no.trim())return 'Nhập số hóa đơn.'
 if(!head.value.bill_date)return 'Nhập ngày hóa đơn.'
 if(serviceOnly.value&&!head.value.supplier)return 'Chọn nhà cung cấp.'
 const used=lines.value.filter(r=>Number(r.qty)>0)
 if(!used.length&&!services.value.length)return 'Hóa đơn chưa có dòng nào.'
 for(const row of used){
  if(Number(row.qty)>Number(row.max_qty)+1e-6)return row.item_name+': chỉ còn '+fmt(row.max_qty)+' '+unitLabel(row.uom)+' chưa có hóa đơn.'
  if(Number(row.rate)<=0)return row.item_name+': nhập đơn giá theo hóa đơn.'
  if(varies(row)&&String(row.variance_reason||'').trim().length<3)return row.item_name+': đơn giá khác phiếu nhận, ghi lý do chênh lệch.'
 }
 for(const row of services.value){if(!String(row.description||'').trim()||Number(row.amount)<=0)return 'Dòng dịch vụ cần nội dung và số tiền.'}
 if(gap.value!=null&&Math.abs(gap.value)>goodsLines.value)return 'Tổng các dòng lệch tổng in '+money(Math.abs(gap.value))+' (cho phép '+goodsLines.value+' đ). Kiểm tra số lượng, đơn giá, thuế suất.'
 return ''
})
const title=computed(()=>serviceOnly.value?'Hóa đơn dịch vụ':'Nhập hóa đơn · '+(source.value?.supplier_name||''))
// A receipt line at a rate that ended before the invoice date takes the rate that followed (8 % → 10 % from 1/1/2027),
// as the server does; a rate the accountant picked by hand is kept.
const inForce=(code,day)=>{let c=String(code||'KCT');for(let i=0;i<5;i++){const end=source.value?.vat_ends?.[c];if(!end||!day||String(day)<=end.to)break;c=String(end.then)}return c}
function followDate(){for(const row of lines.value){const next=inForce(row.receipt_vat,head.value.bill_date);if(row.vat_code===row.auto_vat)row.vat_code=next;row.auto_vat=next}}
watch(()=>head.value.bill_date,followDate)
const isImage=file=>/\.(jpe?g|png|webp)$/i.test(file?.file_url||'')
const isPdf=file=>/\.pdf$/i.test(file?.file_url||'')

async function start(){
 error.value='';source.value=null;lines.value=[];services.value=[];files.value=[];added.value=[];shown.value=null;key.value=newKey()
 head.value={supplier:props.supplier||'',bill_no:'',series:'',tax_code:'',bill_date:props.today||'',due_date:'',posting_date:props.today||'',printed_total:'',printed_vat:''}
 if(serviceOnly.value){services.value=[{description:'',amount:'',vat_code:'KCT',cost:'admin'}];return}
 busy.value=true
 try{
  // A read goes as URL parameters: send the list as JSON, not as "A,B" (found on the live-site copy, 10/11/2026).
  source.value=await method('source',{receipts:JSON.stringify(props.receipts)})
  head.value.supplier=source.value.supplier
  lines.value=source.value.lines.map(r=>({...r,max_qty:r.qty,receipt_rate:r.rate,variance_reason:'',receipt_vat:r.vat_code,auto_vat:r.vat_code}))
  followDate()
  files.value=source.value.files||[];shown.value=files.value[0]||null
 }catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
watch(()=>props.modelValue,open=>{if(open)start()},{immediate:true})
function addFiles(list){added.value=[...added.value,...list].slice(0,20)}
const uploaded=new Map()
async function submit(){
 if(busy.value||problem.value)return
 busy.value=true;error.value=''
 try{
  const send=props.uploader||upload,urls=[]
  for(const file of added.value){if(!uploaded.has(file))uploaded.set(file,(await send(file)).file_url);urls.push(uploaded.get(file))}
  const result=await method('create',{receipts:props.receipts,supplier:head.value.supplier,
   lines:serviceOnly.value||fixed.value?null:lines.value.filter(r=>Number(r.qty)>0).map(r=>({source_item:r.source_item,qty:Number(r.qty),rate:Number(r.rate),vat_code:r.vat_code,variance_reason:varies(r)?r.variance_reason.trim():''})),
   service_lines:services.value.map(r=>({description:r.description.trim(),amount:Number(r.amount),vat_code:r.vat_code,cost:r.cost,lotus_farm:r.lotus_farm||null})),
   bill_no:head.value.bill_no.trim(),series:head.value.series.trim(),tax_code:head.value.tax_code.trim(),bill_date:head.value.bill_date,due_date:head.value.due_date||null,
   posting_date:head.value.posting_date||head.value.bill_date,printed_total:head.value.printed_total===''?null:Number(head.value.printed_total),
   printed_vat:head.value.printed_vat===''?null:Number(head.value.printed_vat),files:urls,client_key:key.value},true)
  emit('created',result);emit('update:modelValue',false)
 }catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
</script>

<template>
 <ResponsiveForm :mobile="mobile" :model-value="modelValue" :title="title" width="1280px" :busy="busy" :error="error" submit-label="Ghi hóa đơn" busy-label="Đang ghi sổ…" :submit-disabled="!!problem" @update:model-value="emit('update:modelValue',$event)" @submit="submit">
  <div class="invoice-form" :class="{'invoice-form--split':!mobile&&files.length}">
   <div class="invoice-form__entry">
    <p class="lotus-form-note">Gõ đúng theo hóa đơn của nhà cung cấp. File đính kèm chỉ là bằng chứng, hệ thống không đọc số từ file.</p>
    <FormGrid :columns="mobile?1:3">
     <LotusField v-if="serviceOnly" v-model="head.supplier" :mobile="mobile" label="Nhà cung cấp" :options="suppliers" required/>
     <LotusField v-model="head.series" :mobile="mobile" label="Ký hiệu hóa đơn" placeholder="VD: 1C26TKN" maxlength="20"/>
     <LotusField v-model="head.bill_no" :mobile="mobile" label="Số hóa đơn" required maxlength="40"/>
     <LotusField v-model="head.bill_date" :mobile="mobile" label="Ngày hóa đơn" type="date" required/>
     <LotusField v-model="head.due_date" :mobile="mobile" label="Hạn thanh toán" type="date" hint="Để trống: theo điều khoản của NCC"/>
     <LotusField v-model="head.posting_date" :mobile="mobile" label="Ngày ghi sổ" type="date"/>
     <LotusField v-model="head.tax_code" :mobile="mobile" label="Mã cơ quan thuế" maxlength="60"/>
    </FormGrid>
    <FormSection v-if="lines.length" title="Hàng theo phiếu nhận" :description="fixed?'Phiếu Mua nhanh: hàng đã vào kho theo giá trên phiếu, hóa đơn ghi đúng số đó.':'Số lượng là phần chưa có hóa đơn; sửa theo hóa đơn nếu khác.'">
     <div v-for="row in lines" :key="row.source_item" class="invoice-form__line">
      <strong>{{row.item_name}}</strong><small>{{row.source_name}}<template v-if="row.order"> · {{row.order}}</template> · chưa có hóa đơn {{fmt(row.max_qty)}} {{unitLabel(row.uom)}}<template v-if="row.order_rate!=null"> · giá đơn mua {{money(row.order_rate)}}</template></small>
      <FormGrid :columns="mobile?1:4">
       <LotusField v-model="row.qty" :mobile="mobile" type="number" :label="'Số lượng ('+unitLabel(row.uom)+')'" :disabled="row.fixed" min="0" :max="row.max_qty"/>
       <LotusField v-model="row.rate" :mobile="mobile" type="money" label="Đơn giá theo hóa đơn" :disabled="row.fixed"/>
       <LotusField v-model="row.vat_code" :mobile="mobile" label="Thuế GTGT" :options="VAT" :searchable="false" :disabled="row.fixed"/>
       <LotusField :model-value="money(Number(row.qty||0)*Number(row.rate||0))" :mobile="mobile" label="Thành tiền" disabled/>
      </FormGrid>
      <LotusField v-if="varies(row)" v-model="row.variance_reason" :mobile="mobile" :label="'Lý do đơn giá khác phiếu nhận ('+money(row.receipt_rate)+')'" required placeholder="NCC điều chỉnh giá, chiết khấu, nhập sai giá trên đơn…"/>
     </div>
    </FormSection>
    <FormSection v-if="!fixed" title="Dịch vụ, chi phí không qua phiếu nhận">
     <template #actions><component :is="button" type="button" variant="outline" size="sm" @click="services.push({description:'',amount:'',vat_code:'KCT',cost:'admin'})">Thêm dòng dịch vụ</component></template>
     <div v-for="(row,index) in services" :key="index" class="invoice-form__line">
      <FormGrid :columns="mobile?1:4">
       <LotusField v-model="row.description" :mobile="mobile" label="Nội dung" required maxlength="140"/>
       <LotusField v-model="row.amount" :mobile="mobile" type="money" label="Số tiền chưa thuế" required/>
       <LotusField v-model="row.vat_code" :mobile="mobile" label="Thuế GTGT" :options="VAT" :searchable="false"/>
       <component :is="button" type="button" variant="outline" size="sm" :aria-label="'Bỏ dòng dịch vụ '+(index+1)" @click="services.splice(index,1)">Bỏ dòng</component>
      </FormGrid>
     </div>
     <p v-if="!services.length" class="lotus-form-note">Không có dòng dịch vụ.</p>
    </FormSection>
    <FormSection title="Tổng theo bản in">
     <FormGrid :columns="mobile?1:2">
      <LotusField v-model="head.printed_vat" :mobile="mobile" type="money" label="Tiền thuế in trên hóa đơn"/>
      <LotusField v-model="head.printed_total" :mobile="mobile" type="money" label="Tổng thanh toán in trên hóa đơn" hint="Nhập đúng số in để khớp từng đồng"/>
     </FormGrid>
     <dl class="lotus-form-totals"><div><dt>Tiền hàng</dt><dd>{{money(net)}}</dd></div><div><dt>Thuế GTGT</dt><dd>{{money(vat)}}</dd></div><div v-if="freight"><dt>Vận chuyển</dt><dd>{{money(freight)}}</dd></div><div><dt>Tổng các dòng</dt><dd>{{money(total)}}</dd></div><div v-if="gap"><dt>Lệch so với tổng in</dt><dd>{{money(gap)}}</dd></div></dl>
     <p v-if="gap&&Math.abs(gap)<=goodsLines" class="lotus-form-note" role="status">Lệch {{money(Math.abs(gap))}} do làm tròn: hóa đơn ghi theo tổng in, phần lệch hiện ở dòng "Làm tròn theo hóa đơn".</p>
     <p v-if="source?.vat_in_cost" class="lotus-form-note">Hộ kinh doanh: thuế GTGT tính vào giá vốn, không khấu trừ.</p>
    </FormSection>
    <FormSection title="File gốc của hóa đơn">
     <template #actions><FilePickerButton :as="mobile?LotusMobileButton:undefined" accept="image/*,application/pdf" multiple label="Thêm file gốc của hóa đơn" size="sm" :disabled="busy" @files="addFiles">Thêm file</FilePickerButton></template>
     <p v-for="file in files" :key="file.name" class="invoice-form__file"><a v-if="mobile||!(isImage(file)||isPdf(file))" :href="file.file_url" target="_blank" rel="noopener">{{file.file_name}}</a><component :is="button" v-else type="button" variant="link" @click="shown=file">{{file.file_name}}</component><small>{{file.attached_to_name}}</small></p>
     <p v-for="(file,index) in added" :key="'n'+index" class="invoice-form__file"><span>{{file.name}} · gắn vào hóa đơn khi ghi</span><component :is="button" type="button" variant="ghost" size="sm" :aria-label="'Bỏ '+file.name" @click="added=added.filter((_,i)=>i!==index)">Bỏ</component></p>
     <p v-if="!files.length&&!added.length" class="lotus-form-note">Chưa có file gốc. Vẫn ghi được hóa đơn; nên đính kèm để đối chiếu.</p>
    </FormSection>
    <p v-if="problem" class="lotus-form-note" role="status">{{problem}}</p>
   </div>
   <aside v-if="!mobile&&files.length" class="invoice-form__viewer" aria-label="File gốc đang xem">
    <img v-if="isImage(shown)" :src="shown.file_url" :alt="'File gốc '+shown.file_name">
    <iframe v-else-if="isPdf(shown)" :src="shown.file_url" :title="'File gốc '+shown.file_name"></iframe>
    <p v-else class="lotus-form-note">Chọn một file ảnh hoặc PDF để xem cạnh biểu mẫu.</p>
   </aside>
  </div>
 </ResponsiveForm>
</template>

<style>
.invoice-form{display:grid;gap:var(--lotus-space-4,16px);min-width:0}
.invoice-form--split{grid-template-columns:minmax(0,3fr) minmax(280px,2fr);align-items:start}
.invoice-form__entry{display:grid;gap:var(--lotus-space-3,12px);min-width:0}
.invoice-form__line{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);min-width:0}
.invoice-form__line small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.invoice-form__file{display:flex;align-items:center;justify-content:space-between;gap:var(--lotus-space-2,8px);margin:0;font-size:var(--lotus-text-sm);min-width:0}
.invoice-form__file small{color:var(--lotus-muted)}
.invoice-form__viewer{position:sticky;top:0;min-height:480px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);overflow:auto;background:var(--lotus-surface)}
.invoice-form__viewer img{display:block;width:100%}
.invoice-form__viewer iframe{display:block;width:100%;height:70vh;border:0}
@media(max-width:1100px){.invoice-form--split{grid-template-columns:minmax(0,1fr)}.invoice-form__viewer{position:static;min-height:0}}
</style>

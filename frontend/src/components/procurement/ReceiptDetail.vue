<script setup>
// Chi tiết phiếu nhập theo đơn và phiếu trả hàng (spec 003, US4), dùng chung cho Kho và Mua hàng, máy tính và điện thoại:
// trạng thái, người giao hàng, chữ ký thủ kho, tệp đính kèm, và mọi thao tác trong Lotus — xác nhận nhập kho (là chữ ký
// của thủ kho), trả hàng (ghi sổ ngay), hủy có lý do, xóa nháp, in, tải bản PDF đã ký. Máy chủ kiểm tra lại tất cả.
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import StockEvidence from '../stock/StockEvidence.vue'
import DeliveryEvidence from './DeliveryEvidence.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'
import {newKey} from '../../procurement'
import {unitLabel} from '../../units'

const props=defineProps({name:{type:String,required:true},mobile:Boolean,today:String,canInvoice:Boolean,
 ask:{type:Function,required:true},callFn:Function,uploader:Function})
const emit=defineEmits(['changed','deleted','open','invoice','credit','notice','error','loaded'])
const method=(module,name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.'+module+'.'+name,args,write):lotusMethod(module,name,args,write)
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const d=ref(null),working=ref(false),mode=ref(''),reason=ref(''),returning=ref({}),returnKey=ref(''),evidence=ref(null),evidenceReady=ref(false),files=ref(null)
const fmt=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const facts=computed(()=>d.value?[d.value.is_return?'Phiếu trả hàng':'Phiếu nhập theo đơn',d.value.state,d.value.supplier_name||d.value.supplier,shortDate(d.value.date),
 d.value.billing,d.value.incoming_total!=null?'Giá trị nhập '+money(d.value.incoming_total,d.value.currency):''].filter(Boolean).join(' · '):'')
const orders=computed(()=>[...new Set((d.value?.items||[]).map(r=>r.order).filter(Boolean))])
const draft=computed(()=>d.value?.docstatus===0)
const waitsEvidence=computed(()=>draft.value&&!d.value.is_return&&d.value.needs_evidence&&!d.value.has_evidence)
const returnable=row=>Math.max(0,Number(row.qty||0)-Number(row.returned_qty||0))
const returnLines=computed(()=>Object.fromEntries((d.value?.items||[]).filter(r=>Number(returning.value[r.line])>0).map(r=>[r.line,Number(returning.value[r.line])])))
const returnProblem=computed(()=>{
 for(const row of d.value?.items||[]){const qty=Number(returning.value[row.line]||0);if(qty<0||qty>returnable(row)+1e-6)return row.item_name+': trả tối đa '+fmt(returnable(row))+' '+unitLabel(row.uom)+'.'}
 return Object.keys(returnLines.value).length?'':'Nhập số lượng trả của ít nhất một dòng.'
})
const deliverer=computed(()=>{
 if(!d.value||d.value.is_return)return ''
 if(d.value.deliverer_signed)return 'Người giao hàng: '+(d.value.deliverer_name||'—')+' · đã ký trên màn hình'
 if(d.value.delivery_proof)return 'Người giao hàng'+(d.value.deliverer_name?': '+d.value.deliverer_name:'')+' · đã ký trên phiếu giao hàng đính kèm'
 return d.value.needs_evidence?'Chưa có xác nhận của người giao hàng.':''
})

async function load(){
 mode.value='';reason.value='';returning.value={}
 try{d.value=await method('procurement','receipt',{name:props.name});emit('loaded',d.value)}
 catch(e){d.value=null;emit('error',e.message||String(e))}
}
watch(()=>props.name,load,{immediate:true})

async function run(work,message,{reload=true}={}){
 if(working.value)return false
 working.value=true;emit('error','')
 try{
  const answer=await work()
  if(reload){await load();files.value?.reload?.();emit('changed',d.value)}
  if(message)emit('notice',typeof message==='function'?message(answer):message)
  window.dispatchEvent(new CustomEvent('lotus-signing-changed'))
  return answer??true
 }catch(e){emit('error',e.message||String(e));return false}
 finally{working.value=false}
}
const base=()=>({name:d.value.name,modified:d.value.modified})
const action=(name,args={})=>method('warehouse_planning','receipt_action',{...base(),action:name,...args},true)

async function confirm(){
 const returned=d.value.is_return
 if(!await props.ask(returned?'Xác nhận trả hàng '+d.value.name+'? Tồn kho giảm ngay.':'Xác nhận nhập kho '+d.value.name+'? Xác nhận này là chữ ký của bạn trên phiếu nhập; tồn kho được cập nhật ngay.'))return
 await run(async()=>{
  let extra={}
  if(waitsEvidence.value){
   const got=await evidence.value.collect()
   for(const file_url of got.files)await method('stock_attachments','attach',{doctype:'Purchase Receipt',name:d.value.name,file_url},true)
   extra={deliverer_name:got.deliverer_name,deliverer_signature:got.deliverer_signature,delivery_proof:got.delivery_proof}
  }
  await action('submit',extra)
 },returned?'Đã xác nhận trả hàng '+d.value.name+'.':'Đã nhập kho '+d.value.name+'. Chữ ký của bạn đã ghi trên phiếu.')
}
async function cancel(){
 if(!await props.ask('Hủy phiếu '+d.value.name+' và đảo sổ kho? Số đã nhận của đơn mua giảm lại.'))return
 await run(()=>action('cancel',{reason:reason.value.trim()}),'Đã hủy phiếu '+d.value.name+'.')
}
async function remove(){
 if(!await props.ask('Xóa phiếu nháp '+d.value.name+'?'))return
 const name=d.value.name
 if(await run(()=>action('delete'),'Đã xóa phiếu nháp '+name+'.',{reload:false}))emit('deleted',name)
}
function startReturn(){mode.value=mode.value==='return'?'':'return';reason.value='';returning.value={};returnKey.value=newKey()}
async function sendBack(){
 if(!await props.ask('Trả hàng cho nhà cung cấp theo phiếu '+d.value.name+'? Tồn kho giảm ngay khi xác nhận.'))return
 const answer=await run(()=>method('procurement','return_receipt',{name:d.value.name,posting_date:props.today||new Date().toISOString().slice(0,10),
  quantities:returnLines.value,client_key:returnKey.value,post:1,reason:reason.value.trim()},true),
  result=>result.docstatus===1?'Đã trả hàng, phiếu '+result.name+'.'+(result.needs_credit_note?' Phiếu nhập gốc đã có hóa đơn: cần lập hóa đơn điều chỉnh trả hàng.':'')
   :'Đã lập phiếu trả nháp '+result.name+', chờ thủ kho xác nhận.')
 if(answer?.needs_credit_note)emit('credit',d.value,answer)
}
function toggle(next){mode.value=mode.value===next?'':next;reason.value=''}
defineExpose({reload:load})
</script>

<template>
 <section v-if="d" class="receipt-detail" :aria-label="'Phiếu '+d.name">
  <p class="lotus-form-note">{{facts}}</p>
  <p v-if="d.return_against" class="lotus-form-note">Trả hàng của phiếu <component :is="button" type="button" variant="link" @click="emit('open',{name:d.return_against},'receipts')">{{d.return_against}}</component></p>
  <p v-if="d.cancel_reason" role="status">Đã hủy: {{d.cancel_reason}}</p>
  <p v-if="d.notes" class="lotus-form-note">{{d.notes}}</p>
  <ul class="receipt-detail__lines" aria-label="Hàng trên phiếu">
   <li v-for="row in d.items" :key="row.line"><strong>{{row.item_name}}</strong><span>{{fmt(Math.abs(row.qty))}} {{unitLabel(row.uom)}} · {{row.warehouse}}<template v-if="row.order"> · {{row.order}}</template><template v-if="Number(row.returned_qty)>0"> · đã trả {{fmt(row.returned_qty)}}</template></span></li>
  </ul>
  <dl v-if="d.incoming_total!=null&&!d.is_return" class="lotus-form-totals"><div><dt>Tiền hàng</dt><dd>{{money(d.goods_total,d.currency)}}</dd></div><div><dt>Chi phí phân bổ</dt><dd>{{money(d.valuation_charges,d.currency)}}</dd></div><div><dt>Giá trị nhập</dt><dd>{{money(d.incoming_total,d.currency)}}</dd></div></dl>
  <p v-if="deliverer" :class="waitsEvidence?'receipt-detail__missing':'lotus-form-note'" role="status">{{deliverer}}<template v-if="d.delivery_proof"> · <a :href="d.delivery_proof" target="_blank" rel="noopener">Xem phiếu giao hàng</a></template></p>
  <p v-if="d.signed_by" class="lotus-form-note" role="status">Thủ kho {{d.signed_by}} đã ký khi xác nhận nhập kho{{d.signed_at?' lúc '+shortDate(d.signed_at)+' '+String(d.signed_at).slice(11,16):''}}.<template v-if="d.signed_copy"> Bản PDF đã ký được lưu kèm phiếu.</template></p>

  <DeliveryEvidence v-if="waitsEvidence&&d.can_submit" ref="evidence" :mobile="mobile" required :disabled="working" :uploader="uploader" @update:valid="evidenceReady=$event"/>
  <StockEvidence ref="files" doctype="Purchase Receipt" :name="d.name" :mobile="mobile" :disabled="working" :readonly="d.docstatus===2" title="Tệp đính kèm (phiếu giao hàng, hóa đơn, ảnh hàng)"/>

  <div v-if="mode==='return'" class="receipt-detail__form">
   <div v-for="row in d.items" :key="row.line" class="receipt-detail__return">
    <LotusField v-model="returning[row.line]" :mobile="mobile" type="number" :label="'Trả lại · '+row.item_name+' ('+unitLabel(row.uom)+')'" :hint="'Còn trả được '+fmt(returnable(row))+' '+unitLabel(row.uom)" min="0" :max="returnable(row)" :disabled="working||returnable(row)<=0" placeholder="0"/>
   </div>
   <LotusField v-model="reason" :mobile="mobile" label="Lý do trả hàng" type="textarea" placeholder="Hàng lỗi, sai quy cách, giao thừa…"/>
   <p v-if="returnProblem" class="lotus-form-note" role="status">{{returnProblem}}</p>
   <component :is="button" type="button" :disabled="working||!!returnProblem||reason.trim().length<3" @click="sendBack">Xác nhận trả hàng</component>
  </div>
  <div v-if="mode==='cancel'" class="receipt-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do hủy phiếu" type="textarea"/>
   <component :is="button" type="button" variant="destructive" :disabled="working||reason.trim().length<3" @click="cancel">Hủy phiếu và đảo sổ kho</component>
  </div>

  <div class="procurement-actions receipt-detail__actions">
   <component :is="button" v-if="d.can_submit" type="button" :disabled="working||waitsEvidence&&!evidenceReady" @click="confirm">{{d.is_return?'Xác nhận trả hàng':'Xác nhận nhập kho'}}</component>
   <component :is="button" v-if="canInvoice&&d.docstatus===1&&!d.is_return&&d.billing!=='Đã có hóa đơn'" type="button" :disabled="working" @click="emit('invoice',d)">Lập hóa đơn</component>
   <component :is="button" v-if="d.can_return" type="button" variant="outline" :disabled="working" @click="startReturn">Trả hàng</component>
   <component :is="button" v-if="d.can_cancel" type="button" variant="outline" :disabled="working" @click="toggle('cancel')">Hủy phiếu</component>
   <component :is="button" v-if="d.can_delete" type="button" variant="outline" :disabled="working" @click="remove">Xóa nháp</component>
   <component :is="button" v-for="order in orders" :key="order" type="button" variant="outline" @click="emit('open',{name:order},'orders')">Đơn mua {{order}}</component>
   <component :is="button" v-for="invoice in d.invoices||[]" :key="invoice" type="button" variant="outline" @click="emit('open',{name:invoice},'invoices')">Hóa đơn {{invoice}}</component>
   <component :is="link" as="a" variant="outline" :href="d.print_url" target="_blank" rel="noopener">In phiếu</component>
   <component :is="link" v-if="d.signed_copy" as="a" variant="outline" :href="d.signed_copy.url" target="_blank" rel="noopener">Tải bản PDF đã ký</component>
  </div>
 </section>
</template>

<style>
.receipt-detail{display:grid;gap:var(--lotus-space-3,12px);min-width:0}
.receipt-detail__lines{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.receipt-detail__lines li{display:grid;gap:2px;padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);min-width:0}
.receipt-detail__lines span{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.receipt-detail__form{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
.receipt-detail__missing{margin:0;color:var(--lotus-warning-800,var(--lotus-text))}
</style>

<script setup>
import '../procurement.css'
import {computed,nextTick,ref} from 'vue'
import {call} from '../api'
import {newKey,purchaseRequest} from '../procurement'
import {unitLabel} from '../units'
import ModalForm from './form/ModalForm.vue'
import FormGrid from './form/FormGrid.vue'
import LotusField from './form/LotusField.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
import PurchaseReceiptCosts from './PurchaseReceiptCosts.vue'
import DeliveryEvidence from './procurement/DeliveryEvidence.vue'
import ReceiptDetail from './procurement/ReceiptDetail.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileButton from './LotusMobileButton.vue'
// Nhận hàng theo đơn mua, một đường cho Kho và Mua hàng (spec 003, US4): chọn đơn đã duyệt → số thực nhận (nhận nhiều
// lần được), chi phí phát sinh, ảnh, người giao hàng ký hoặc ảnh phiếu giao → Xác nhận nhập kho. Xác nhận là chữ ký của
// thủ kho; phiếu được ghi sổ và lưu bản PDF đã ký trong cùng một bước. Người không có quyền ghi sổ chỉ lưu được phiếu nháp.
// Desktop uses the standard ModalForm; the phone PWAs keep their own dialog with the same fields.
const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,confirm:Function,canInvoice:Boolean,warehouses:{type:Array,default:()=>[]},callFn:Function,uploader:Function})
const emit=defineEmits(['changed','open','invoice','credit'])
const open=ref(false),mobileDialog=ref(null),stage=ref('picker'),orders=ref([]),order=ref(null),receiptName=ref(''),selected=ref(''),lines=ref([]),date=ref(''),error=ref(''),notice=ref(''),busy=ref(false),key=ref('')
const costs=ref([]),accounts=ref([]),defaultAccount=ref(''),notes=ref(''),evidence=ref(null),evidenceReady=ref(true)
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
const baseTotal=computed(()=>lines.value.reduce((sum,r)=>sum+Number(r.receive||0)*Number(r.rate||0),0))
const request=props.callFn||call
const api=(m,args={},write=false)=>purchaseRequest(request,'lotus_farm.warehouse_planning.'+m,args,write)
const ask=text=>props.confirm?props.confirm(text):Promise.resolve(true)
const selectedQty=computed(()=>Object.fromEntries(lines.value.filter(r=>Number(r.receive)>0).map(r=>[r.line,Number(r.receive)])))
const orderOptions=computed(()=>orders.value.map(r=>({value:r.name,label:r.name+' · '+r.supplier})))
const lineColumns=[{field:'item',label:'Hàng trên đơn',width:'minmax(260px,3fr)'},{field:'receive',label:'Thực nhận',type:'number',width:'minmax(140px,1fr)',disabled:r=>!r.remaining_qty||busy.value,props:r=>({min:0,max:r.remaining_qty}),hint:r=>'Còn nhận '+fmt(r.remaining_qty)+' '+unitLabel(r.uom)}]
const titles={picker:'Nhận hàng theo đơn',order:'Nhận hàng',receipt:'Phiếu nhận hàng'}
const title=computed(()=>stage.value==='order'?'Nhận hàng · '+(order.value?.name||'')+' · '+(order.value?.supplier_name||order.value?.supplier||''):stage.value==='receipt'?'Phiếu nhận hàng · '+receiptName.value:titles.picker)
// Posting needs the right to post receipts; without it the receipt is saved as a draft for the storekeeper.
const posts=computed(()=>order.value?.can_post!==false)
const needsEvidence=computed(()=>!!order.value?.needs_evidence&&posts.value)
const submitLabel=computed(()=>stage.value==='picker'?'Mở đơn nhận hàng':posts.value?'Xác nhận nhập kho':'Lưu phiếu nháp')
const blocked=computed(()=>stage.value==='picker'?!selected.value:!order.value?.can_receive||!Object.keys(selectedQty.value).length||needsEvidence.value&&!evidenceReady.value)
function hasChanges(){return open.value&&stage.value==='order'&&(Object.keys(selectedQty.value).length>0||costs.value.length>0||!!notes.value.trim()||!!evidence.value?.dirty?.())}
async function show(){open.value=true;if(props.mobile){await nextTick();mobileDialog.value?.showModal()}}
async function run(fn){if(busy.value)return;busy.value=true;error.value='';notice.value='';try{return await fn()}catch(e){error.value=e.message;throw e}finally{busy.value=false}}
const quiet=fn=>run(fn).catch(()=>{})
async function openPicker(){stage.value='picker';selected.value='';await show();await quiet(async()=>{const r=await api('overview',{company:props.company,warehouse:props.warehouse||'',from_date:props.today,to_date:props.today});orders.value=[...new Map((r.orders||[]).map(r=>[r.name,r])).values()]})}
async function openOrder(name){await quiet(async()=>{order.value=await api('purchase_order',{name});stage.value='order';date.value=props.today;key.value=newKey();lines.value=(order.value.items||[]).map(r=>({...r,receive:''}));costs.value=[];notes.value='';evidence.value?.reset?.();await show();const a=await request('lotus_farm.warehouse.receipt_accounts',{company:props.company});accounts.value=a.accounts||[];defaultAccount.value=a.default_account||''})}
async function openReceipt(name){receiptName.value=name;stage.value='receipt';error.value='';notice.value='';await show()}
// Someone else may have received meanwhile: show what the order still waits for, keep what was typed.
async function refreshRemaining(){try{const fresh=await api('purchase_order',{name:order.value.name});order.value=fresh;const typed=Object.fromEntries(lines.value.map(r=>[r.line,r.receive]));lines.value=(fresh.items||[]).map(r=>({...r,receive:typed[r.line]??''}))}catch{/* the refusal already says what happened */}}
async function receive(){
 if(posts.value&&!await ask('Xác nhận nhập kho theo đơn '+order.value.name+'? Xác nhận này là chữ ký của bạn trên phiếu nhập; tồn kho được cập nhật ngay.'))return
 try{
  await run(async()=>{
   const got=evidence.value?await evidence.value.collect():{files:[]}
   const result=await api('receive_order',{name:order.value.name,posting_date:date.value,quantities:selectedQty.value,client_event_id:key.value,additional_costs:costs.value,post:1,
    files:got.files,deliverer_name:got.deliverer_name||'',deliverer_signature:got.deliverer_signature||'',delivery_proof:got.delivery_proof||'',notes:notes.value.trim()},true)
   receiptName.value=result.name;stage.value='receipt';lines.value=[];costs.value=[];notes.value=''
   const left=(result.remaining||[]).map(r=>r.item_name+' '+fmt(r.remaining_qty)+' '+unitLabel(r.uom)).join('; ')
   notice.value=result.docstatus===1?'Đã nhập kho '+result.name+'. Chữ ký của bạn đã ghi trên phiếu.'+(left?' Đơn còn chờ: '+left+'.':' Đơn đã nhận đủ.'):'Đã lưu phiếu nháp '+result.name+'. Chờ thủ kho xác nhận nhập kho.'
   emit('changed',result)
  })
 }catch(e){if(/còn nhận được/i.test(e.message||''))await refreshRemaining()}
}
function submit(){if(stage.value==='picker')return openOrder(selected.value);if(stage.value==='order')return receive()}
function finish(){lines.value=[];costs.value=[];notes.value='';mobileDialog.value?.close();open.value=false}
async function close(event){event?.preventDefault?.();if(busy.value)return;if(hasChanges()&&props.confirm&&!await props.confirm('Bỏ số lượng nhận chưa lưu và đóng?'))return;finish()}
function discardChanges(){finish()}
function receiptChanged(detail){emit('changed',detail)}
function receiptDeleted(){emit('changed',null);finish()}
defineExpose({openPicker,openOrder,openReceipt,hasChanges,discardChanges})
</script>

<template>
 <ModalForm v-if="!mobile" :model-value="open" :title="title" :busy="busy" :error="error" width="1080px" :readonly="stage==='receipt'" :submit-label="submitLabel" :submit-disabled="blocked" @update:model-value="value=>!value&&close()" @submit="submit">
  <template v-if="stage==='picker'">
   <LotusField v-model="selected" label="Đơn mua chờ nhận" :options="orderOptions" required :hint="!busy&&!orders.length?'Chưa có đơn đã duyệt còn chờ nhận. Đơn mua phải được duyệt trước khi nhận hàng.':''" placeholder="Chọn hoặc gõ số đơn, nhà cung cấp…"/>
  </template>
  <template v-else-if="stage==='order'">
   <FormGrid :columns="3"><LotusField v-model="date" label="Ngày nhận" type="date" required/></FormGrid>
   <LineItemsEditor v-model="lines" title="Hàng trên đơn" :columns="lineColumns" fixed>
    <template #cell-item="{row}"><div class="receiving-line"><strong>{{row.item_name}}</strong><small>{{row.item}} · {{row.warehouse}}</small><small>Đặt {{fmt(row.ordered_qty)}} · Đã nhận {{fmt(row.received_qty)}} · Phiếu nháp {{fmt(row.draft_qty)}} · Đơn giá {{fmt(row.rate)}} {{order?.currency||'VND'}}/{{unitLabel(row.uom)}}</small></div></template>
   </LineItemsEditor>
   <PurchaseReceiptCosts v-model="costs" :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/>
   <DeliveryEvidence ref="evidence" :required="needsEvidence" :disabled="busy" :uploader="uploader" @update:valid="evidenceReady=$event"/>
   <LotusField v-model="notes" label="Ghi chú nhận hàng" type="textarea" :disabled="busy" placeholder="Tình trạng hàng, xe giao, người nhận…"/>
   <p v-if="posts" class="lotus-form-note">Bấm Xác nhận nhập kho là bạn ký phiếu nhập với tư cách thủ kho. Không còn bước ký riêng sau khi nhập.</p>
   <p v-else class="lotus-form-note">Bạn chưa có quyền ghi sổ nhập kho: phiếu được lưu nháp, thủ kho xác nhận sau.</p>
  </template>
  <template v-else-if="receiptName">
   <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <ReceiptDetail :name="receiptName" :today="today" :can-invoice="canInvoice" :ask="ask" :call-fn="callFn" :uploader="uploader" @changed="receiptChanged" @deleted="receiptDeleted"
    @open="(row,type)=>type==='receipts'?openReceipt(row.name):emit('open',row,type)" @invoice="emit('invoice',$event)" @credit="(d,r)=>emit('credit',d,r)" @notice="notice=$event" @error="error=$event"/>
  </template>
 </ModalForm>

 <LotusMobileDialog v-else ref="mobileDialog" bare title="Nhận hàng theo đơn" @cancel="close"><template v-if="open"><header class="procurement-actions"><h3>{{title}}</h3><LotusMobileButton :disabled="busy" @click="close">Đóng</LotusMobileButton></header><p v-if="error" role="alert" class="procurement-error">{{error}}</p>
  <form v-if="stage==='picker'" @submit.prevent="openOrder(selected)"><LotusField v-model="selected" mobile label="Đơn mua chờ nhận" :options="orderOptions" required/><LotusMobileButton type="submit" :disabled="busy||!selected">Mở đơn nhận hàng</LotusMobileButton><p v-if="!busy&&!orders.length">Chưa có đơn đã duyệt còn chờ nhận.</p></form>
  <form v-else-if="stage==='order'" @submit.prevent="receive"><fieldset :disabled="busy"><LotusField v-model="date" mobile label="Ngày nhận" type="date" required/><LineItemsEditor v-model="lines" mobile title="Hàng trên đơn" :columns="lineColumns" fixed><template #cell-item="{row}"><p class="receiving-line"><strong>{{row.item_name}}</strong><small>{{row.warehouse}} · Còn nhận {{fmt(row.remaining_qty)}} {{unitLabel(row.uom)}}</small></p></template></LineItemsEditor><PurchaseReceiptCosts v-model="costs" mobile :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/>
   <DeliveryEvidence ref="evidence" mobile :required="needsEvidence" :disabled="busy" :uploader="uploader" @update:valid="evidenceReady=$event"/>
   <LotusField v-model="notes" mobile label="Ghi chú nhận hàng" type="textarea"/>
   <p class="lotus-form-note">{{posts?'Bấm Xác nhận nhập kho là bạn ký phiếu nhập với tư cách thủ kho.':'Bạn chưa có quyền ghi sổ: phiếu được lưu nháp, thủ kho xác nhận sau.'}}</p>
   <LotusMobileButton type="submit" :disabled="busy||blocked">{{submitLabel}}</LotusMobileButton></fieldset></form>
  <section v-else-if="receiptName"><p v-if="notice" role="status">{{notice}}</p>
   <ReceiptDetail :name="receiptName" mobile :today="today" :can-invoice="canInvoice" :ask="ask" :call-fn="callFn" :uploader="uploader" @changed="receiptChanged" @deleted="receiptDeleted"
    @open="(row,type)=>type==='receipts'?openReceipt(row.name):emit('open',row,type)" @invoice="emit('invoice',$event)" @credit="(d,r)=>emit('credit',d,r)" @notice="notice=$event" @error="error=$event"/></section>
 </template></LotusMobileDialog>
</template>

<style>
.receiving-line{display:grid;gap:2px;margin:0;min-width:0}
.receiving-line small{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
</style>

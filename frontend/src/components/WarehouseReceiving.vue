<script setup>
import {computed,nextTick,ref,watch} from 'vue'
import {call} from '../api'
import {newKey,purchaseRequest} from '../procurement'
import {validateReceiptInputs} from '../warehouse-mobile-helpers'
import {unitLabel} from '../units'
import ProcurementField from './ProcurementField.vue'
import PurchaseReceiptCosts from './PurchaseReceiptCosts.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileCheck from './LotusMobileCheck.vue'
import {Button} from './ui/button'
const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,inline:Boolean,confirm:Function,online:{type:Boolean,default:true}})
const emit=defineEmits(['changed','close'])
const dialog=ref(null),opened=ref(false),stage=ref('picker'),orders=ref([]),order=ref(null),receipt=ref(null),selected=ref(''),quantities=ref({}),date=ref(''),error=ref(''),busy=ref(false),key=ref(''),confirmed=ref(false)
const costs=ref([]),accounts=ref([]),defaultAccount=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
let generation=0
const scopedCall=async(...args)=>{const id=generation;const result=await call(...args);if(id!==generation){const e=new Error('Scope changed');e.stale=true;throw e}return result}
const api=(m,args={},write=false)=>purchaseRequest(scopedCall,'lotus_farm.warehouse_planning.'+m,args,write)
const check=computed(()=>validateReceiptInputs(order.value?.items||[],quantities.value))
const selectedQty=computed(()=>check.value.quantities)
const baseTotal=computed(()=>(order.value?.items||[]).reduce((sum,r)=>sum+Number(selectedQty.value[r.line]||0)*Number(r.rate||0),0))
const money=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+(order.value?.currency||receipt.value?.currency||'VND')
const printURL=name=>'/lotus/in-phieu?'+new URLSearchParams({doctype:'Purchase Receipt',name})
function hasChanges(){return opened.value&&stage.value==='order'&&(Object.values(quantities.value).some(v=>String(v).trim()!=='')||costs.value.length>0||date.value!==props.today)}
async function show(){opened.value=true;await nextTick();if(!props.inline)dialog.value.showModal()}
async function run(fn){if(busy.value)return;const id=generation;busy.value=true;error.value='';try{return await fn()}catch(e){if(id===generation&&!e.stale)error.value=e.message}finally{if(id===generation)busy.value=false}}
async function fetchOrders(search){const r=await scopedCall('lotus_farm.warehouse_buying_lite.orders',{company:props.company,warehouse:props.warehouse||'',status:'pending',search});return (r.rows||[]).map(r=>({value:r.name,label:r.name+' · '+(r.supplier_name||r.supplier),subtitle:r.expected_date}))}
async function openPicker(){stage.value='picker';selected.value='';await show();await run(async()=>{orders.value=await fetchOrders('')})}
async function openOrder(name){await run(async()=>{order.value=await api('purchase_order',{name});stage.value='order';date.value=props.today;key.value=newKey();quantities.value={};costs.value=[];confirmed.value=false;await show();try{const a=await scopedCall('lotus_farm.warehouse.receipt_accounts',{company:props.company});accounts.value=a.accounts||[];defaultAccount.value=a.default_account||''}catch{accounts.value=[];defaultAccount.value=''}})}
async function openReceipt(name){await run(async()=>{receipt.value=await api('purchase_receipt',{name});stage.value='receipt';confirmed.value=false;await show()})}
async function receive(){
 if(!props.online)return
 if(!date.value){error.value='Chọn ngày nhận hàng.';return}
 if(!check.value.valid){error.value=check.value.reason;return}
 if(!Object.keys(selectedQty.value).length){error.value='Nhập số thực nhận của ít nhất một mặt hàng.';return}
 await run(async()=>{const r=await api('receive_order',{name:order.value.name,posting_date:date.value,quantities:selectedQty.value,client_event_id:key.value,additional_costs:costs.value},true);receipt.value=await api('purchase_receipt',{name:r.name});stage.value='receipt';quantities.value={};costs.value=[];confirmed.value=false;emit('changed',receipt.value)})
}
async function action(action){
 if(!props.online||action==='submit'&&!confirmed.value)return
 const question={submit:'Ghi sổ số thực nhận này và cập nhật tồn kho?',delete:'Xóa phiếu nhận nháp này?',cancel:'Hủy phiếu nhận và đảo tồn kho theo chứng từ gốc?'}[action]
 if(props.confirm&&!await props.confirm(question))return
 await run(async()=>{await api('receipt_action',{name:receipt.value.name,modified:receipt.value.modified,action},true);if(action==='delete'){discardChanges();emit('close')}else{receipt.value=await api('purchase_receipt',{name:receipt.value.name});confirmed.value=false}emit('changed',receipt.value)})
}
function discardChanges(){generation++;busy.value=false;quantities.value={};costs.value=[];order.value=null;receipt.value=null;dialog.value?.close?.();opened.value=false}
async function close(event){event?.preventDefault?.();if(busy.value)return;if(hasChanges()&&props.confirm&&!await props.confirm('Bỏ số lượng nhận chưa lưu và đóng?'))return;discardChanges();emit('close')}
watch(()=>[props.company,props.warehouse],discardChanges)
defineExpose({openPicker,openOrder,openReceipt,hasChanges,discardChanges,isOpen:()=>opened.value,isBusy:()=>busy.value})
</script>
<template>
 <component :is="inline?'section':mobile?LotusMobileDialog:WorkspaceModal" ref="dialog" bare title="Nhận hàng theo đơn" class="warehouse-receiving" :class="{'warehouse-receiving--mobile':mobile}" @cancel="close">
  <template v-if="opened">
   <header class="warehouse-receiving-heading"><h3 v-if="!inline">Nhận hàng theo đơn</h3><component :is="button" type="button" variant="outline" :disabled="busy" @click="close">Đóng</component></header>
   <p v-if="error" role="alert" class="warehouse-receiving-error">{{error}}</p><p v-if="busy" role="status">Đang tải…</p>
   <form v-if="stage==='picker'" class="warehouse-receiving-form" @submit.prevent="openOrder(selected)">
    <ProcurementField v-model="selected" :mobile="mobile" label="Đơn mua chờ nhận" :options="orders" :fetch-options="fetchOrders" required/>
    <component :is="button" type="submit" :disabled="busy||!selected">Mở đơn nhận hàng</component><p v-if="!busy&&!orders.length">Chưa có đơn đã duyệt còn chờ nhận.</p>
   </form>
   <form v-else-if="stage==='order'" class="warehouse-receiving-form" @submit.prevent="receive"><fieldset :disabled="busy||!online">
    <p>{{order?.name}} · {{order?.supplier}}</p><ProcurementField v-model="date" :mobile="mobile" label="Ngày nhận" type="date" required/>
    <section v-for="r in order?.items||[]" :key="r.line" class="warehouse-receiving-line"><strong>{{r.item_name}}</strong><small>{{r.warehouse}} · Còn nhận {{r.remaining_qty}} {{unitLabel(r.uom)}}</small><ProcurementField v-model="quantities[r.line]" :mobile="mobile" label="Thực nhận" type="number" inputmode="decimal" min="0" :max="r.remaining_qty" step="any" :hint="unitLabel(r.uom)" :disabled="!r.remaining_qty"/></section>
    <p v-if="!check.valid" role="alert" class="warehouse-receiving-error">{{check.reason}}</p>
    <PurchaseReceiptCosts v-model="costs" :mobile="mobile" :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/>
    <component :is="button" type="submit" :disabled="busy||!order?.can_receive||!check.valid||!Object.keys(selectedQty).length">Lập phiếu nhận nháp</component>
   </fieldset></form>
   <section v-else-if="receipt" class="warehouse-receiving-form"><p>{{receipt.name}} · {{receipt.supplier}} · {{['Nháp','Đã ghi sổ','Đã hủy'][receipt.docstatus]}}</p>
    <div v-for="(r,i) in receipt.items" :key="r.line||i" class="warehouse-receiving-line"><strong>{{r.item_name}}</strong><span>{{r.qty}} {{unitLabel(r.uom)}}</span></div>
    <div v-if="receipt.incoming_total!=null" class="warehouse-receiving-totals"><span>Tiền hàng <strong>{{money(receipt.goods_total)}}</strong></span><span>Chi phí phân bổ <strong>{{money(receipt.valuation_charges)}}</strong></span><span>Giá trị nhập <strong>{{money(receipt.incoming_total)}}</strong></span></div>
    <a v-if="receipt.can_print" :href="printURL(receipt.name)" target="_blank" rel="noopener">In phiếu nhận</a>
    <template v-if="receipt.can_submit"><LotusMobileCheck v-if="mobile" v-model="confirmed">Đã kiểm tra số thực nhận</LotusMobileCheck><label v-else class="warehouse-receiving-check"><input v-model="confirmed" type="checkbox">Đã kiểm tra số thực nhận</label><component :is="button" type="button" :disabled="busy||!confirmed||!online" @click="action('submit')">Ghi sổ nhận hàng</component></template>
    <component :is="button" v-if="receipt.can_delete" type="button" variant="outline" :disabled="busy||!online" @click="action('delete')">Xóa phiếu nhận nháp</component>
    <component :is="button" v-if="receipt.can_cancel" type="button" variant="outline" :disabled="busy||!online" @click="action('cancel')">Hủy phiếu nhận</component>
   </section>
  </template>
 </component>
</template>
<style scoped>
.warehouse-receiving{min-width:0;color:var(--lotus-text)}
.warehouse-receiving-heading{display:flex;align-items:center;justify-content:space-between;gap:var(--lotus-space-3);margin-bottom:var(--lotus-space-4)}
.warehouse-receiving-heading h3{margin:0;font-size:var(--lotus-text-lg)}
.warehouse-receiving-form,.warehouse-receiving-form fieldset{display:grid;gap:var(--lotus-space-4);min-width:0;margin:0;padding:0;border:0}
.warehouse-receiving-line{display:grid;gap:var(--lotus-space-2);min-width:0;padding:var(--lotus-space-3);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface)}
.warehouse-receiving-line small{color:var(--lotus-muted)}
.warehouse-receiving-totals{display:grid;gap:var(--lotus-space-2)}
.warehouse-receiving-totals span{display:flex;justify-content:space-between;gap:var(--lotus-space-3);flex-wrap:wrap}
.warehouse-receiving-check{display:flex;align-items:center;gap:var(--lotus-space-2)}
.warehouse-receiving-error{color:var(--lotus-danger);margin:0}
</style>

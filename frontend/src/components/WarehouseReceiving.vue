<script setup>
import '../procurement.css'
import {computed,nextTick,ref} from 'vue'
import {call} from '../api'
import {newKey,purchaseRequest} from '../procurement'
import ProcurementField from './ProcurementField.vue'
import PurchaseReceiptCosts from './PurchaseReceiptCosts.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button} from './ui/button'
const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,confirm:Function})
const emit=defineEmits(['changed'])
const dialog=ref(null),opened=ref(false),stage=ref('picker'),orders=ref([]),order=ref(null),receipt=ref(null),selected=ref(''),quantities=ref({}),date=ref(''),error=ref(''),busy=ref(false),key=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const costs=ref([]),accounts=ref([]),defaultAccount=ref('')
const baseTotal=computed(()=>(order.value?.items||[]).reduce((sum,r)=>sum+Number(quantities.value[r.line]||0)*Number(r.rate||0),0))
const api=(m,args={},write=false)=>purchaseRequest(call,'lotus_farm.warehouse_planning.'+m,args,write)
const selectedQty=computed(()=>Object.fromEntries(Object.entries(quantities.value).filter(([,v])=>Number(v)>0)))
function hasChanges(){return !!dialog.value?.open&&stage.value==='order'&&(Object.keys(selectedQty.value).length>0||costs.value.length>0)}
async function show(){opened.value=true;await nextTick();dialog.value.showModal()}
async function run(fn){if(busy.value)return;busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{busy.value=false}}
async function openPicker(){stage.value='picker';selected.value='';await show();await run(async()=>{const r=await api('overview',{company:props.company,warehouse:props.warehouse||'',from_date:props.today,to_date:props.today});orders.value=[...new Map((r.orders||[]).map(r=>[r.name,r])).values()]})}
async function openOrder(name){await run(async()=>{order.value=await api('purchase_order',{name});stage.value='order';date.value=props.today;key.value=newKey();quantities.value={};costs.value=[];await show();const a=await call('lotus_farm.warehouse.receipt_accounts',{company:props.company});accounts.value=a.accounts||[];defaultAccount.value=a.default_account||''})}
async function openReceipt(name){await run(async()=>{receipt.value=await api('purchase_receipt',{name});stage.value='receipt';await show()})}
async function receive(){await run(async()=>{const r=await api('receive_order',{name:order.value.name,posting_date:date.value,quantities:selectedQty.value,client_event_id:key.value,additional_costs:costs.value},true);receipt.value=await api('purchase_receipt',{name:r.name});stage.value='receipt';quantities.value={};costs.value=[];emit('changed',receipt.value)})}
async function post(){if(props.confirm&&!await props.confirm('Ghi sổ số thực nhận này và cập nhật tồn kho?'))return;await run(async()=>{await api('receipt_action',{name:receipt.value.name,modified:receipt.value.modified,action:'submit'},true);receipt.value=await api('purchase_receipt',{name:receipt.value.name});emit('changed',receipt.value)})}
async function close(event){event?.preventDefault?.();if(busy.value)return;if(hasChanges()&&props.confirm&&!await props.confirm('Bỏ số lượng nhận chưa lưu và đóng?'))return;quantities.value={};dialog.value.close();opened.value=false}
defineExpose({openPicker,openOrder,openReceipt,hasChanges,discardChanges:()=>{quantities.value={};dialog.value?.close();opened.value=false}})
</script>
<template><component :is="mobile?LotusMobileDialog:WorkspaceModal" ref="dialog" bare title="Nhận hàng theo đơn" @cancel="close"><template v-if="opened"><header class="procurement-actions"><h3>Nhận hàng theo đơn</h3><component :is="button" :disabled="busy" @click="close">Đóng</component></header><p v-if="error" role="alert" class="procurement-error">{{error}}</p>
 <form v-if="stage==='picker'" @submit.prevent="openOrder(selected)"><ProcurementField v-model="selected" :mobile="mobile" label="Đơn mua chờ nhận" :options="orders.map(r=>({value:r.name,label:r.name+' · '+r.supplier}))" required/><component :is="button" type="submit" :disabled="busy||!selected">Mở đơn nhận hàng</component><p v-if="!busy&&!orders.length">Chưa có đơn đã duyệt còn chờ nhận.</p></form>
 <form v-else-if="stage==='order'" @submit.prevent="receive"><fieldset :disabled="busy"><p>{{order?.name}} · {{order?.supplier}}</p><ProcurementField v-model="date" :mobile="mobile" label="Ngày nhận" type="date" required/><section v-for="r in order?.items||[]" :key="r.line" class="procurement-line"><p>{{r.item_name}} · {{r.warehouse}} · Còn nhận {{r.remaining_qty}} {{r.uom}}</p><ProcurementField v-model="quantities[r.line]" :mobile="mobile" label="Thực nhận" type="number" min="0" :max="r.remaining_qty" step="any" :disabled="!r.remaining_qty"/></section><PurchaseReceiptCosts v-model="costs" :mobile="mobile" :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/><component :is="button" type="submit" :disabled="busy||!order?.can_receive||!Object.keys(selectedQty).length">Lập phiếu nhận nháp</component></fieldset></form>
 <section v-else-if="receipt"><p>{{receipt.name}} · {{receipt.supplier}} · {{['Nháp','Đã ghi sổ','Đã hủy'][receipt.docstatus]}}</p><p v-for="(r,i) in receipt.items" :key="r.line||i">{{r.item_name}} · {{r.qty}} {{r.uom}}</p><p v-if="receipt.incoming_total!=null">Tiền hàng {{receipt.goods_total}} · Chi phí phân bổ {{receipt.valuation_charges}} · Giá trị nhập {{receipt.incoming_total}} {{receipt.currency}}</p><component :is="button" v-if="receipt.can_submit" :disabled="busy" @click="post">Ghi sổ nhận hàng</component></section>
</template></component></template>

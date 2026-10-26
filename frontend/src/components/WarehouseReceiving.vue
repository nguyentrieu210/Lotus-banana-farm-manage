<script setup>
import StockEvidence from './stock/StockEvidence.vue'
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
import DataTable from './DataTable.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button as UiButton} from './ui/button'
// Nhận hàng theo đơn mua: chọn đơn đã duyệt → nhập số thực nhận (nhận nhiều lần được) → phiếu nhận nháp → ghi sổ.
// Desktop uses the standard ModalForm; the phone PWAs keep their own dialog with the same fields.
const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,confirm:Function})
const emit=defineEmits(['changed'])
const open=ref(false),mobileDialog=ref(null),stage=ref('picker'),orders=ref([]),order=ref(null),receipt=ref(null),selected=ref(''),lines=ref([]),date=ref(''),error=ref(''),busy=ref(false),key=ref('')
const costs=ref([]),accounts=ref([]),defaultAccount=ref('')
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
const baseTotal=computed(()=>lines.value.reduce((sum,r)=>sum+Number(r.receive||0)*Number(r.rate||0),0))
const api=(m,args={},write=false)=>purchaseRequest(call,'lotus_farm.warehouse_planning.'+m,args,write)
const selectedQty=computed(()=>Object.fromEntries(lines.value.filter(r=>Number(r.receive)>0).map(r=>[r.line,Number(r.receive)])))
const orderOptions=computed(()=>orders.value.map(r=>({value:r.name,label:r.name+' · '+r.supplier})))
const lineColumns=[{field:'item',label:'Hàng trên đơn',width:'minmax(260px,3fr)'},{field:'receive',label:'Thực nhận',type:'number',width:'minmax(140px,1fr)',disabled:r=>!r.remaining_qty||busy.value,props:r=>({min:0,max:r.remaining_qty}),hint:r=>'Còn nhận '+fmt(r.remaining_qty)+' '+unitLabel(r.uom)}]
const receiptColumns=[{field:'item_name',headerName:'Vật tư',minWidth:220,flex:2},{field:'qty',headerName:'Số lượng',type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'uom',headerName:'Đơn vị',valueFormatter:p=>unitLabel(p.value)},{field:'warehouse',headerName:'Kho nhận',minWidth:160}]
const titles={picker:'Nhận hàng theo đơn',order:'Nhận hàng',receipt:'Phiếu nhận hàng'}
const title=computed(()=>stage.value==='order'?'Nhận hàng · '+(order.value?.name||'')+' · '+(order.value?.supplier||''):stage.value==='receipt'?'Phiếu nhận hàng · '+(receipt.value?.name||''):titles.picker)
const submitLabel=computed(()=>stage.value==='picker'?'Mở đơn nhận hàng':'Lập phiếu nhận nháp')
const printURL=computed(()=>receipt.value?'/lotus/in-phieu?'+new URLSearchParams({doctype:'Purchase Receipt',name:receipt.value.name}):'')
function hasChanges(){return open.value&&stage.value==='order'&&(Object.keys(selectedQty.value).length>0||costs.value.length>0)}
async function show(){open.value=true;if(props.mobile){await nextTick();mobileDialog.value?.showModal()}}
async function run(fn){if(busy.value)return;busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{busy.value=false}}
async function openPicker(){stage.value='picker';selected.value='';await show();await run(async()=>{const r=await api('overview',{company:props.company,warehouse:props.warehouse||'',from_date:props.today,to_date:props.today});orders.value=[...new Map((r.orders||[]).map(r=>[r.name,r])).values()]})}
async function openOrder(name){await run(async()=>{order.value=await api('purchase_order',{name});stage.value='order';date.value=props.today;key.value=newKey();lines.value=(order.value.items||[]).map(r=>({...r,receive:''}));costs.value=[];await show();const a=await call('lotus_farm.warehouse.receipt_accounts',{company:props.company});accounts.value=a.accounts||[];defaultAccount.value=a.default_account||''})}
async function openReceipt(name){await run(async()=>{receipt.value=await api('purchase_receipt',{name});stage.value='receipt';await show()})}
async function receive(){await run(async()=>{const r=await api('receive_order',{name:order.value.name,posting_date:date.value,quantities:selectedQty.value,client_event_id:key.value,additional_costs:costs.value},true);receipt.value=await api('purchase_receipt',{name:r.name});stage.value='receipt';lines.value=[];costs.value=[];emit('changed',receipt.value)})}
async function post(){if(props.confirm&&!await props.confirm('Ghi sổ số thực nhận này và cập nhật tồn kho?'))return;await run(async()=>{await api('receipt_action',{name:receipt.value.name,modified:receipt.value.modified,action:'submit'},true);receipt.value=await api('purchase_receipt',{name:receipt.value.name});emit('changed',receipt.value)})}
function submit(){if(stage.value==='picker')return openOrder(selected.value);if(stage.value==='order')return receive()}
async function close(event){event?.preventDefault?.();if(busy.value)return;if(hasChanges()&&props.confirm&&!await props.confirm('Bỏ số lượng nhận chưa lưu và đóng?'))return;lines.value=[];mobileDialog.value?.close();open.value=false}
function discardChanges(){lines.value=[];mobileDialog.value?.close();open.value=false}
defineExpose({openPicker,openOrder,openReceipt,hasChanges,discardChanges})
</script>

<template>
 <ModalForm v-if="!mobile" :model-value="open" :title="title" :busy="busy" :error="error" width="1080px" :readonly="stage==='receipt'" :submit-label="submitLabel" :submit-disabled="stage==='picker'?!selected:!order?.can_receive||!Object.keys(selectedQty).length" @update:model-value="value=>!value&&close()" @submit="submit">
  <template v-if="stage==='picker'">
   <LotusField v-model="selected" label="Đơn mua chờ nhận" :options="orderOptions" required :hint="!busy&&!orders.length?'Chưa có đơn đã duyệt còn chờ nhận. Đơn mua phải được duyệt trước khi nhận hàng.':''" placeholder="Chọn hoặc gõ số đơn, nhà cung cấp…"/>
  </template>
  <template v-else-if="stage==='order'">
   <FormGrid :columns="3"><LotusField v-model="date" label="Ngày nhận" type="date" required/></FormGrid>
   <LineItemsEditor v-model="lines" title="Hàng trên đơn" :columns="lineColumns" fixed>
    <template #cell-item="{row}"><div class="receiving-line"><strong>{{row.item_name}}</strong><small>{{row.item}} · {{row.warehouse}}</small><small>Đặt {{fmt(row.ordered_qty)}} · Đã nhận {{fmt(row.received_qty)}} · Phiếu nháp {{fmt(row.draft_qty)}} · Đơn giá {{fmt(row.rate)}} {{order?.currency||'VND'}}/{{unitLabel(row.uom)}}</small></div></template>
   </LineItemsEditor>
   <PurchaseReceiptCosts v-model="costs" :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/>
  </template>
  <template v-else-if="receipt">
   <p class="lotus-modal-form__description">{{receipt.supplier}} · {{['Nháp','Đã ghi sổ','Đã hủy'][receipt.docstatus]}}</p>
   <DataTable :rows="receipt.items||[]" :columns="receiptColumns"/>
   <dl v-if="receipt.incoming_total!=null" class="lotus-form-totals"><div><dt>Tiền hàng</dt><dd>{{fmt(receipt.goods_total)}} {{receipt.currency}}</dd></div><div><dt>Chi phí phân bổ</dt><dd>{{fmt(receipt.valuation_charges)}} {{receipt.currency}}</dd></div><div><dt>Giá trị nhập</dt><dd>{{fmt(receipt.incoming_total)}} {{receipt.currency}}</dd></div></dl>
   <p v-if="receipt.docstatus===1" class="stock-success" role="status">Đã ghi sổ nhận hàng. Tồn và phần chờ nhập đã cập nhật.</p>
   <StockEvidence doctype="Purchase Receipt" :name="receipt.name" title="Chứng từ nhận hàng (phiếu giao hàng, hóa đơn, ảnh hàng)"/>
  </template>
  <template #actions><template v-if="stage==='receipt'&&receipt"><UiButton as="a" variant="outline" :href="printURL" target="_blank" rel="noopener">In phiếu</UiButton><UiButton v-if="receipt.can_submit" type="button" :disabled="busy" @click="post">Ghi sổ nhận hàng</UiButton></template></template>
 </ModalForm>

 <LotusMobileDialog v-else ref="mobileDialog" bare title="Nhận hàng theo đơn" @cancel="close"><template v-if="open"><header class="procurement-actions"><h3>{{title}}</h3><LotusMobileButton :disabled="busy" @click="close">Đóng</LotusMobileButton></header><p v-if="error" role="alert" class="procurement-error">{{error}}</p>
  <form v-if="stage==='picker'" @submit.prevent="openOrder(selected)"><LotusField v-model="selected" mobile label="Đơn mua chờ nhận" :options="orderOptions" required/><LotusMobileButton type="submit" :disabled="busy||!selected">Mở đơn nhận hàng</LotusMobileButton><p v-if="!busy&&!orders.length">Chưa có đơn đã duyệt còn chờ nhận.</p></form>
  <form v-else-if="stage==='order'" @submit.prevent="receive"><fieldset :disabled="busy"><LotusField v-model="date" mobile label="Ngày nhận" type="date" required/><LineItemsEditor v-model="lines" mobile title="Hàng trên đơn" :columns="lineColumns" fixed><template #cell-item="{row}"><p class="receiving-line"><strong>{{row.item_name}}</strong><small>{{row.warehouse}} · Còn nhận {{fmt(row.remaining_qty)}} {{unitLabel(row.uom)}}</small></p></template></LineItemsEditor><PurchaseReceiptCosts v-model="costs" mobile :accounts="accounts" :default-account="defaultAccount" :base-total="baseTotal" :currency="order?.currency||'VND'" :disabled="busy"/><LotusMobileButton type="submit" :disabled="busy||!order?.can_receive||!Object.keys(selectedQty).length">Lập phiếu nhận nháp</LotusMobileButton></fieldset></form>
  <section v-else-if="receipt"><p>{{receipt.name}} · {{receipt.supplier}} · {{['Nháp','Đã ghi sổ','Đã hủy'][receipt.docstatus]}}</p><p v-for="(r,i) in receipt.items" :key="r.line||i">{{r.item_name}} · {{fmt(r.qty)}} {{unitLabel(r.uom)}}</p><p v-if="receipt.incoming_total!=null">Tiền hàng {{fmt(receipt.goods_total)}} · Chi phí phân bổ {{fmt(receipt.valuation_charges)}} · Giá trị nhập {{fmt(receipt.incoming_total)}} {{receipt.currency}}</p><LotusMobileButton v-if="receipt.can_submit" :disabled="busy" @click="post">Ghi sổ nhận hàng</LotusMobileButton></section>
 </template></LotusMobileDialog>
</template>

<style>
.receiving-line{display:grid;gap:2px;margin:0;min-width:0}
.receiving-line small{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
</style>

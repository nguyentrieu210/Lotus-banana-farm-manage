<script setup>
import {computed,onMounted,ref,useId,watch} from 'vue'
import {call} from '../api'
import {stockLine,stockUnits,selectStockLine,validateStockDraft} from '../stock-document'
import {unitLabel} from '../units'
import ProcurementField from './ProcurementField.vue'
import StockReceiptReason from './StockReceiptReason.vue'
import PurchaseReceiptCosts from './PurchaseReceiptCosts.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button} from './ui/button'
const props=defineProps({modelValue:{type:Object,required:true},company:String,mobile:Boolean,items:{type:Array,default:()=>[]},conversions:{type:Array,default:()=>[]},warehouses:{type:Array,default:()=>[]},employees:{type:Array,default:()=>[]},blocks:{type:Array,default:()=>[]},fetchItems:Function,currency:{type:String,default:'VND'},saving:Boolean,loading:Boolean,online:{type:Boolean,default:true}})
const emit=defineEmits(['update:modelValue','submit','error'])
const reason=ref(null),error=ref(''),accounts=ref([]),defaultAccount=ref(''),accountError=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const d=computed(()=>props.modelValue),planned=computed(()=>d.value.kind==='issue'&&d.value.issue_mode!=='Manual')
const storeOptions=computed(()=>props.warehouses.map(w=>({value:w.name,label:w.warehouse_name||w.name})))
const itemOptions=computed(()=>props.items.map(i=>({value:i.name,label:i.item_name,...i})))
const fields=computed(()=>d.value.kind==='receipt'||d.value.kind==='count'&&d.value.count_purpose==='Opening Stock')
const amount=computed(()=>d.value.lines.reduce((n,r)=>n+Number(r.qty||0)*Number(r.rate||0),0))
const lotList=useId()+'-stock-lots'
const money=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency
function patch(values){emit('update:modelValue',{...d.value,...values})}
function line(index,values){patch({lines:d.value.lines.map((r,i)=>i===index?{...r,...values}:r)})}
function choose(index,option){line(index,selectStockLine(d.value.lines[index],option,d.value.kind))}
let accountVersion=0
async function loadAccounts(){
 const id=++accountVersion;accounts.value=[];defaultAccount.value=''
 if(d.value.kind!=='receipt'||!props.company)return
 accountError.value=''
 try{const r=await call('lotus_farm.warehouse.receipt_accounts',{company:props.company});if(id!==accountVersion)return;accounts.value=r.accounts||[];defaultAccount.value=r.default_account||''}
 catch(e){if(id===accountVersion){accounts.value=[];accountError.value=e.message}}
}
watch(()=>[props.company,d.value.kind],loadAccounts)
onMounted(loadAccounts)
async function submit(){
 if(props.saving||props.loading||!props.online)return
 error.value=validateStockDraft(d.value)
 if(!error.value&&d.value.kind==='receipt')error.value=await reason.value.validate(d.value.lines)
 if(error.value){emit('error',error.value);return}
 emit('submit')
}
</script>
<template>
 <form class="warehouse-document-form" :class="{'warehouse-document-form--mobile':mobile}" @submit.prevent="submit">
  <p v-if="error" role="alert" class="warehouse-form-error">{{error}}</p>
  <fieldset :disabled="saving||loading"><slot name="source"/>
   <StockReceiptReason v-if="d.kind==='receipt'" ref="reason" :mobile="mobile" :reason="d.receipt_reason" :supplier="d.supplier" @update:reason="patch({receipt_reason:$event})" @update:supplier="patch({supplier:$event})"/>
   <div class="warehouse-form-fields">
    <ProcurementField :mobile="mobile" :model-value="d.posting_date" label="Ngày" type="date" required @update:model-value="patch({posting_date:$event})"/>
    <ProcurementField v-if="d.kind==='count'" :mobile="mobile" :model-value="d.count_purpose" label="Loại kiểm kê" :options="[{value:'Stock Reconciliation',label:'Kiểm kê định kỳ'},{value:'Opening Stock',label:'Tồn đầu kỳ khi bắt đầu'}]" :searchable="false" required @update:model-value="patch({count_purpose:$event})"/>
    <ProcurementField v-if="['issue','transfer'].includes(d.kind)" :mobile="mobile" :model-value="d.source" label="Kho xuất" :options="storeOptions" :searchable="false" required @update:model-value="patch({source:$event})"/>
    <ProcurementField v-if="['receipt','transfer','count'].includes(d.kind)" :mobile="mobile" :model-value="d.target" :label="d.kind==='count'?'Kho kiểm kê':'Kho nhận'" :options="storeOptions" :searchable="false" required @update:model-value="patch({target:$event})"/>
    <ProcurementField v-if="d.kind==='issue'" :mobile="mobile" :model-value="d.receiver_employee" label="Người nhận vật tư (HRMS)" :options="employees" :required="!d.existing_name||!d.receiver" :hint="d.existing_name&&d.receiver&&!d.receiver_employee?'Phiếu cũ: '+d.receiver:undefined" @update:model-value="patch({receiver_employee:$event})"/>
   </div>
   <slot name="empty"/>
   <section v-for="(row,index) in d.lines" :key="index" class="warehouse-document-line">
    <div class="warehouse-line-title"><strong>Hàng {{index+1}}</strong><component :is="button" type="button" variant="outline" :disabled="planned||d.lines.length===1||saving" aria-label="Xóa dòng vật tư" @click="patch({lines:d.lines.filter((_,i)=>i!==index)})">Xóa</component></div>
    <div class="warehouse-line-fields">
     <ProcurementField :mobile="mobile" :model-value="row.item" :label="mobile?'Tên hàng':'Vật tư'" :options="itemOptions" :fetch-options="fetchItems" :display-value="row.item_name||items.find(i=>i.name===row.item)?.item_name" :disabled="planned" placeholder="Gõ tên hoặc mã hàng…" required @select="choose(index,$event)"/>
     <ProcurementField :mobile="mobile" :model-value="row.qty" :label="d.kind==='count'?'Tồn thực đếm':'Số lượng'" type="number" :min="d.kind==='count'||planned?0:0.000001" :max="planned?row.remaining_qty:undefined" step="any" inputmode="decimal" required :hint="row.stock_uom&&row.uom!==row.stock_uom?'Đơn vị kho: '+unitLabel(row.stock_uom):unitLabel(row.uom||items.find(i=>i.name===row.item)?.stock_uom)" @update:model-value="line(index,{qty:$event})"/>
     <ProcurementField v-if="d.kind==='receipt'" :mobile="mobile" :model-value="row.uom" label="Đơn vị nhập hàng" :options="stockUnits(row,items,conversions)" :searchable="false" required @update:model-value="line(index,{uom:$event})"/>
     <ProcurementField v-if="fields" :mobile="mobile" :model-value="row.rate" label="Đơn giá" type="number" min="0" step="any" inputmode="decimal" required :hint="currency+' / '+(unitLabel(row.uom)||'đơn vị')+' · Thành tiền '+money(Number(row.qty||0)*Number(row.rate||0))" @update:model-value="line(index,{rate:$event})"/>
     <ProcurementField v-if="d.kind==='issue'||d.kind==='receipt'&&d.receipt_reason==='Recovery'" :mobile="mobile" :model-value="row.area" :label="d.kind==='receipt'?'Lô thu hồi vật tư':'Khu vực / lô sử dụng'" :disabled="planned&&row.fixed_area" :list="lotList" required placeholder="Mã lô / khu vực" :hint="planned?'Duyệt '+row.required_qty+' · Đã cấp/giữ '+row.allocated_qty+' · Còn '+row.remaining_qty:undefined" @update:model-value="line(index,{area:$event})"/>
    </div>
   </section>
   <datalist :id="lotList"><option v-for="b in blocks" :key="b.code" :value="b.code">{{b.label}}</option></datalist>
   <component v-if="!planned" :is="button" type="button" variant="outline" :disabled="d.lines.length>=100||saving" @click="patch({lines:[...d.lines,stockLine(d.kind)]})">Thêm vật tư</component>
   <template v-if="d.kind==='receipt'"><p v-if="accountError" role="alert" class="warehouse-form-error">{{accountError}}</p><PurchaseReceiptCosts :model-value="d.additional_costs||[]" :mobile="mobile" :accounts="accounts" :default-account="defaultAccount" :base-total="amount" :currency="currency" :disabled="saving" direct @update:model-value="patch({additional_costs:$event})"/></template>
   <ProcurementField v-if="d.kind!=='count'" :mobile="mobile" :model-value="d.notes" :label="d.kind==='issue'&&d.issue_mode==='Manual'?'Lý do xuất thủ công':'Ghi chú'" type="textarea" maxlength="2000" :required="d.kind==='issue'&&d.issue_mode==='Manual'" @update:model-value="patch({notes:$event})"/>
   <footer class="warehouse-form-actions"><component :is="button" type="submit" :variant="mobile?'primary':'default'" :disabled="saving||loading||!online||!d.lines.length">{{saving?'Đang lưu…':d.existing_name?'Lưu thay đổi':'Lưu phiếu nháp →'}}</component></footer>
  </fieldset>
 </form>
</template>
<style scoped>
.warehouse-document-form{display:grid;gap:var(--lotus-space-4);min-width:0;width:100%;color:var(--lotus-text)}
.warehouse-document-form fieldset{display:grid;gap:var(--lotus-space-4);min-width:0;margin:0;padding:0;border:0}
.warehouse-form-fields,.warehouse-line-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3);min-width:0}
.warehouse-document-line{display:grid;gap:var(--lotus-space-3);min-width:0;padding:var(--lotus-space-4);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface)}
.warehouse-line-title{display:flex;align-items:center;justify-content:space-between;gap:var(--lotus-space-3);min-width:0}
.warehouse-line-title strong{font-size:var(--lotus-text-md)}
.warehouse-form-actions{display:flex;justify-content:flex-end;gap:var(--lotus-space-3)}
.warehouse-form-error{color:var(--lotus-danger);font-size:var(--lotus-text-md);margin:0}
.warehouse-document-form--mobile .warehouse-form-fields,.warehouse-document-form--mobile .warehouse-line-fields{grid-template-columns:minmax(0,1fr)}
.warehouse-document-form--mobile .warehouse-form-actions .van-button{width:100%}
@media(max-width:640px){.warehouse-form-fields,.warehouse-line-fields{grid-template-columns:minmax(0,1fr)}}
</style>

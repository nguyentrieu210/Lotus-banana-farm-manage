<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
import ProcurementField from './ProcurementField.vue'
import LotusMobileButton from './LotusMobileButton.vue'

const props=defineProps({
  modelValue:{type:Array,default:()=>[]},
  accounts:{type:Array,default:()=>[]},
  defaultAccount:{type:String,default:''},
  baseTotal:{type:Number,default:0},
  currency:{type:String,default:'VND'},
  disabled:{type:Boolean,default:false},
  mobile:{type:Boolean,default:false},
})
const emit=defineEmits(['update:modelValue'])
const actionButton=computed(()=>props.mobile?LotusMobileButton:UiButton)
const accountOptions=computed(()=>props.accounts.map(a=>({value:a.name,label:a.account_name||a.name})))
const costsTotal=computed(()=>props.modelValue.reduce((sum,r)=>sum+Number(r.amount||0),0))
const money=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency
function add(){emit('update:modelValue',[...props.modelValue,{description:'',amount:'',expense_account:props.defaultAccount||''}])}
function patch(index,key,value){emit('update:modelValue',props.modelValue.map((r,i)=>i===index?{...r,[key]:value}:r))}
function remove(index){emit('update:modelValue',props.modelValue.filter((_,i)=>i!==index))}
</script>
<template>
 <section class="receipt-costs" :class="{'receipt-costs--mobile':mobile}">
  <div class="receipt-costs-title"><strong>Chi phí nhập kho phát sinh</strong>
   <component :is="actionButton" type="button" variant="outline" :disabled="disabled||!accounts.length||modelValue.length>=30" @click="add">Thêm chi phí</component>
  </div>
  <p class="stock-muted">Đơn giá lấy từ đơn mua. Không nhập lại phí đã tính trong đơn.</p>
  <p v-if="!accounts.length" class="stock-muted">Chưa có tài khoản chi phí phù hợp hoặc chưa được cấp quyền xem. Có thể nhận hàng không kèm chi phí.</p>
  <div v-for="(cost,index) in modelValue" :key="index" class="receipt-cost-row">
   <ProcurementField :mobile="mobile" :model-value="cost.description" :disabled="disabled" maxlength="140" required label="Khoản chi phí" placeholder="Bốc xếp, vận chuyển…" @update:model-value="v=>patch(index,'description',v)"/>
   <ProcurementField :mobile="mobile" :model-value="cost.amount" :disabled="disabled" type="number" min="0.000001" step="any" required :label="'Số tiền ('+currency+')'" @update:model-value="v=>patch(index,'amount',v===''?'':Number(v))"/>
   <ProcurementField :mobile="mobile" :model-value="cost.expense_account" :disabled="disabled" required label="Tài khoản chi phí" :options="accountOptions" @update:model-value="v=>patch(index,'expense_account',v)"/>
   <component :is="actionButton" type="button" variant="outline" :disabled="disabled" aria-label="Xóa chi phí" @click="remove(index)">Xóa</component>
  </div>
  <div class="receipt-totals">
   <span>Tiền hàng thực nhận <strong>{{money(baseTotal)}}</strong></span>
   <span>Chi phí phát sinh <strong>{{money(costsTotal)}}</strong></span>
   <span>Giá trị nhập tạm tính <strong>{{money(baseTotal+costsTotal)}}</strong></span>
  </div>
  <small class="stock-muted">Chưa gồm thuế và phí đã ghi trên đơn mua. Phí này cộng vào giá trị tồn kho; không tự phát sinh công nợ nhà cung cấp.</small>
 </section>
</template>
<style scoped>
.receipt-costs{display:grid;gap:12px;min-width:0}
.receipt-costs-title{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
.receipt-cost-row{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,2fr) auto;gap:10px;align-items:end;min-width:0}
.receipt-costs--mobile .receipt-cost-row{grid-template-columns:minmax(0,1fr)}
.receipt-totals{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between}
.receipt-totals span{display:flex;flex-wrap:wrap;gap:6px}
@media (max-width:720px){.receipt-cost-row{grid-template-columns:minmax(0,1fr)}}
</style>

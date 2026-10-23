<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'

const props=defineProps({
  modelValue:{type:Array,default:()=>[]},
  accounts:{type:Array,default:()=>[]},
  defaultAccount:{type:String,default:''},
  baseTotal:{type:Number,default:0},
  currency:{type:String,default:'VND'},
  disabled:{type:Boolean,default:false},
})
const emit=defineEmits(['update:modelValue'])
const costsTotal=computed(()=>props.modelValue.reduce((sum,r)=>sum+Number(r.amount||0),0))
const money=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency
function add(){emit('update:modelValue',[...props.modelValue,{description:'',amount:0,expense_account:props.defaultAccount||''}])}
function patch(index,key,value){emit('update:modelValue',props.modelValue.map((r,i)=>i===index?{...r,[key]:value}:r))}
function remove(index){emit('update:modelValue',props.modelValue.filter((_,i)=>i!==index))}
</script>
<template>
 <section class="receipt-costs">
  <div class="section-title"><h3>Chi phí nhập kho phát sinh</h3>
   <UiButton type="button" variant="outline" :disabled="disabled||!accounts.length||modelValue.length>=30" @click="add">+ Thêm chi phí</UiButton>
  </div>
  <p class="stock-muted">Đơn giá lấy từ đơn mua. Chỉ thêm khoản phát sinh khi nhận, không nhập lại khoản đã có trên đơn.</p>
  <p v-if="!accounts.length" class="stock-muted">Chưa có tài khoản chi phí phù hợp hoặc chưa được cấp quyền xem. Có thể nhận hàng không kèm chi phí; cần cấu hình trước khi thêm phí.</p>
  <div v-for="(cost,index) in modelValue" :key="index" class="receipt-cost-row">
   <label>Khoản chi phí<UiInput :model-value="cost.description" :disabled="disabled" maxlength="140" required placeholder="Vận chuyển, bốc xếp…" @update:model-value="v=>patch(index,'description',v)"/></label>
   <label>Số tiền ({{currency}})<UiInput :model-value="cost.amount" :disabled="disabled" type="number" min="0.000001" step="any" required @update:model-value="v=>patch(index,'amount',v===''?'':Number(v))"/></label>
   <label>Tài khoản chi phí<UiSelect :model-value="cost.expense_account" :disabled="disabled" required @update:model-value="v=>patch(index,'expense_account',v)">
     <option value="">Chọn tài khoản</option><option v-for="a in accounts" :key="a.name" :value="a.name">{{a.account_name}}</option>
   </UiSelect></label>
   <UiButton type="button" variant="ghost" :disabled="disabled" aria-label="Xóa chi phí" @click="remove(index)">×</UiButton>
  </div>
  <div class="receipt-totals">
   <span>Tiền hàng thực nhận <strong>{{money(baseTotal)}}</strong></span>
   <span>Chi phí phát sinh <strong>{{money(costsTotal)}}</strong></span>
   <span>Tạm tính giá trị nhập <strong>{{money(baseTotal+costsTotal)}}</strong></span>
  </div>
  <small class="stock-muted">Chưa gồm các khoản thuế hoặc phí đã có trên đơn mua. Phiếu nhận sẽ tính giá vốn bằng ERPNext; công nợ được xử lý bằng hóa đơn.</small>
 </section>
</template>

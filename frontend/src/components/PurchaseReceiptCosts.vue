<script setup>
import {computed} from 'vue'
import FormSection from './form/FormSection.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
// Chi phí nhập kho phát sinh khi nhận hàng theo đơn (bốc xếp, vận chuyển…): cộng vào giá trị tồn, không tạo công nợ NCC.
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
const costsTotal=computed(()=>props.modelValue.reduce((sum,r)=>sum+Number(r.amount||0),0))
const money=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency
const columns=computed(()=>[
 {field:'description',label:'Khoản chi phí',required:true,props:{maxlength:140,placeholder:'Bốc xếp, vận chuyển…'},width:'minmax(180px,2fr)'},
 {field:'amount',label:'Số tiền ('+props.currency+')',type:'money',required:true,props:{min:0.000001,currency:props.currency},width:'minmax(140px,1fr)'},
 {field:'expense_account',label:'Tài khoản chi phí',required:true,options:props.accounts.map(a=>({value:a.name,label:a.account_name||a.name})),width:'minmax(180px,2fr)'}
])
</script>
<template>
 <FormSection title="Chi phí nhập kho phát sinh" description="Đơn giá lấy từ đơn mua. Không nhập lại phí đã tính trong đơn.">
  <p v-if="!accounts.length" class="lotus-form-note">Chưa có tài khoản chi phí phù hợp hoặc chưa được cấp quyền xem. Có thể nhận hàng không kèm chi phí.</p>
  <LineItemsEditor :model-value="modelValue" title="Các khoản chi phí" add-label="Thêm chi phí" empty-text="Chưa có chi phí phát sinh." :columns="columns" :min="0" :max="30" :mobile="mobile" :readonly="disabled||!accounts.length" :new-row="()=>({description:'',amount:'',expense_account:defaultAccount||''})" @update:model-value="emit('update:modelValue',$event)"/>
  <dl class="lotus-form-totals"><div><dt>Tiền hàng thực nhận</dt><dd>{{money(baseTotal)}}</dd></div><div><dt>Chi phí phát sinh</dt><dd>{{money(costsTotal)}}</dd></div><div><dt>Giá trị nhập tạm tính</dt><dd>{{money(baseTotal+costsTotal)}}</dd></div></dl>
  <p class="lotus-form-note">Chưa gồm thuế và phí đã ghi trên đơn mua. Phí này cộng vào giá trị tồn kho; không tự phát sinh công nợ nhà cung cấp.</p>
 </FormSection>
</template>

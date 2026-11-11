<script setup>
import {computed} from 'vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {purchaseOrderStatus,purchaseStatusTone} from '../buying-order-status'

const props=defineProps({order:{type:Object,required:true},currency:{type:String,default:'VND'},showDate:Boolean})
const emit=defineEmits(['select'])
const status=computed(()=>purchaseOrderStatus(props.order))
const tone=computed(()=>purchaseStatusTone(props.order))
const amount=computed(()=>Number(props.order.amount||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency)
// Invoice and payment progress of an approved order (spec 003, FR-039); payment is shown only to people who may see it.
const percent=value=>Math.round(Number(value||0))+'%'
const progress=computed(()=>props.order.docstatus!==1||props.order.billed_percent==null?'':['Hóa đơn '+percent(props.order.billed_percent),props.order.paid_percent==null?'':'Đã trả '+percent(props.order.paid_percent)].filter(Boolean).join(' · '))
</script>
<template>
 <LotusMobileButton class="buy-order-card" :aria-label="'Mở đơn '+order.name" @click="emit('select',order.name)">
  <div class="buy-order-top">
   <strong class="buy-order-supplier" :title="order.supplier_name||order.supplier">{{order.supplier_name||order.supplier||'Chưa có nhà cung cấp'}}</strong>
   <span class="buy-order-status" :class="'buy-order-status--'+tone">{{status}}</span>
  </div>
  <div class="buy-order-code" :title="order.name">{{order.name}}<template v-if="progress"> · {{progress}}</template></div>
  <div class="buy-order-bottom">
   <span class="buy-order-meta" :title="order.warehouse">{{order.warehouse||'Chưa có kho'}}<template v-if="showDate&&order.expected_date"> · Hẹn {{order.expected_date}}</template><template v-if="order.overdue"> · quá hẹn</template></span>
   <strong class="buy-order-amount">{{amount}}</strong>
  </div>
 </LotusMobileButton>
</template>

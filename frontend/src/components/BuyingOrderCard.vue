<script setup>
import {computed} from 'vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {purchaseOrderStatus,purchaseStatusTone} from '../buying-order-status'

const props=defineProps({order:{type:Object,required:true},currency:{type:String,default:'VND'},showDate:Boolean})
const emit=defineEmits(['select'])
const status=computed(()=>purchaseOrderStatus(props.order))
const tone=computed(()=>purchaseStatusTone(props.order))
const amount=computed(()=>Number(props.order.amount||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency)
</script>
<template>
 <LotusMobileButton class="buy-order-card" :aria-label="'Mở đơn '+order.name" @click="emit('select',order.name)">
  <div class="buy-order-top">
   <strong class="buy-order-supplier" :title="order.supplier_name||order.supplier">{{order.supplier_name||order.supplier||'Chưa có nhà cung cấp'}}</strong>
   <span class="buy-order-status" :class="'buy-order-status--'+tone">{{status}}</span>
  </div>
  <div class="buy-order-code" :title="order.name">{{order.name}}</div>
  <div class="buy-order-bottom">
   <span class="buy-order-meta" :title="order.warehouse">{{order.warehouse||'Chưa có kho'}}<template v-if="showDate&&order.expected_date"> · Hẹn {{order.expected_date}}</template></span>
   <strong class="buy-order-amount">{{amount}}</strong>
  </div>
 </LotusMobileButton>
</template>

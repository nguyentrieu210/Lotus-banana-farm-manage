<script setup>
import {computed} from 'vue'
import DataTable from './DataTable.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import {money} from '../procurement'
import {unitLabel} from '../units'
const props=defineProps({progress:Object,mobile:Boolean,navigate:Boolean})
const emit=defineEmits(['open'])
const button=computed(()=>props.navigate?(props.mobile?LotusMobileButton:Button):'a')
const columns=[{field:'item_name',headerName:'Vật tư',minWidth:180},{field:'uom',headerName:'ĐVT',valueFormatter:p=>unitLabel(p.value)},
 {field:'qty',headerName:'Đề xuất'},{field:'ordered_qty',headerName:'Đã đặt'},{field:'remaining_order_qty',headerName:'Còn đặt'},
 {field:'received_qty',headerName:'Đã nhận'},{field:'remaining_receive_qty',headerName:'Còn nhận'},{field:'billed_qty',headerName:'Đã lập hóa đơn'}]
const groups=[['proposals','needs','Đề xuất'],['orders','orders','Đơn mua'],['receipts','receipts','Phiếu nhận'],['invoices','invoices','Hóa đơn'],['payments','payments','Thanh toán']]
const url=(row,type)=>'/lotus/mua-hang?'+new URLSearchParams({buying_view:type,purchase_doc:row.name,purchase_type:type,...(row.doctype?{purchase_doctype:row.doctype}:{})})
function open(event,row,type){if(props.navigate){event.preventDefault();emit('open',row,type)}}
</script>
<template>
 <section v-if="progress" aria-label="Tiến độ mua hàng">
  <p v-if="progress.stage||progress.receiving_status||progress.invoice_status">{{[progress.stage,progress.receiving_status,progress.invoice_status].filter(Boolean).join(' · ')}}</p>
  <template v-if="mobile"><p v-for="row in progress.lines" :key="row.name||row.item_name">{{row.item_name}} · {{unitLabel(row.uom)}} · Đề xuất {{row.qty}} · Đã đặt {{row.ordered_qty}} · Đã nhận {{row.received_qty}}</p></template>
  <DataTable v-else-if="progress.lines?.length" :rows="progress.lines" :columns="columns"/>
  <p v-if="progress.outstanding_amount!=null">Còn nợ theo hóa đơn liên quan {{money(progress.outstanding_amount)}}</p>
  <div v-for="[key,type,label] in groups" :key="key" class="procurement-actions">
   <component :is="button" v-for="row in progress[key]||[]" :key="row.name" as="a" :href="url(row,type)" variant="outline" @click="open($event,row,type)">{{label}} {{row.name}} · {{row.docstatus===0?'Nháp':row.docstatus===2?'Đã hủy':'Đã xác nhận'}}<template v-if="row.amount!=null"> · {{money(row.amount)}}</template></component>
  </div>
 </section>
</template>

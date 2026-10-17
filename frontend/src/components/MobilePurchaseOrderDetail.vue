<script setup>
import {computed} from 'vue'
import {Cell,CellGroup} from 'vant'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import {unitLabel} from '../units'
const props=defineProps({order:{type:Object,required:true},currency:{type:String,default:'VND'},warehouses:{type:Array,default:()=>[]}})
const number=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const money=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency
const warehouse=name=>props.warehouses.find(r=>r.name===name)?.warehouse_name||name||'—'
const total=computed(()=>props.order.amount??props.order.items?.reduce((sum,line)=>sum+Number(line.qty||0)*Number(line.rate||0),0)??0)
const displayStatus=computed(()=>props.order.docstatus===2?'Đã hủy':['Đã đóng','Đã nhận đủ','Quá hẹn','Về một phần'].includes(props.order.status)?props.order.status:props.order.approval_status||props.order.status||'Nháp')
</script>
<template>
 <section class="lotus-purchase-detail">
  <CellGroup class="lotus-order-summary" :border="false">
   <Cell title="Số đơn" :value="order.name"/><Cell title="Nhà cung cấp" :value="order.supplier_name||order.supplier"/>
   <Cell title="Trạng thái" :value="displayStatus"/>
   <Cell v-if="order.expected_date" :title="order.revised_delivery_date?'Ngày NCC hẹn lại':'Ngày giao dự kiến'" :value="order.expected_date"/>
   <Cell v-if="order.revised_delivery_date&&order.original_expected_date" title="Ngày hẹn ban đầu" :value="order.original_expected_date"/>
   <Cell v-if="order.sent_at" title="Đã gửi NCC" :value="order.sent_at"/>
   <Cell v-if="order.supplier_confirmed_at" title="NCC đã xác nhận" :value="order.supplier_confirmed_at"/>
   <Cell title="Tổng tiền" :value="money(total)"/>
  </CellGroup>
  <LotusMobileFeedback v-if="order.reject_reason" kind="warning">Lý do trả lại: {{order.reject_reason}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="order.revised_delivery_reason" kind="warning">Lý do đổi lịch: {{order.revised_delivery_reason}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="order.close_reason" kind="warning">Lý do đóng đơn: {{order.close_reason}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="order.cancel_reason" kind="warning">Lý do hủy đơn: {{order.cancel_reason}}</LotusMobileFeedback>
  <CellGroup v-for="(line,index) in order.items||[]" :key="line.line||index" class="lotus-order-line" :border="false">
   <Cell :title="line.item_name||line.item" :label="warehouse(line.warehouse||line.source||line.target)" :value="number(line.qty)+' '+unitLabel(line.uom)"/>
   <Cell v-if="line.rate!==undefined" title="Đơn giá" :value="money(line.rate)"/>
   <Cell v-if="order.docstatus===1&&line.received_qty!==undefined" title="Đã nhận" :value="number(line.received_qty)+' '+unitLabel(line.uom)"/>
   <Cell v-if="line.remaining_qty!==undefined" title="Còn chờ" :value="number(line.remaining_qty)+' '+unitLabel(line.uom)"/>
  </CellGroup>
  <CellGroup v-if="order.quote_files?.length" class="lotus-order-summary" :border="false"><Cell title="Báo giá đính kèm"/>
   <Cell v-for="file in order.quote_files" :key="file.name"><a :href="file.file_url" target="_blank" rel="noopener">{{file.file_name}}</a></Cell>
  </CellGroup>
  <CellGroup v-if="order.notes" class="lotus-order-summary" :border="false"><Cell title="Ghi chú giao hàng" :label="order.notes"/></CellGroup>
 </section>
</template>
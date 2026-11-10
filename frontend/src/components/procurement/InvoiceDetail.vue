<script setup>
// Chi tiết hóa đơn nhà cung cấp đã nhập (spec 003, US5): đúng như bản in (ký hiệu, số, từng dòng, thuế, tổng in, phần
// làm tròn), phiếu nhận liên quan, file gốc, thanh toán; hủy có lý do khi chưa có thanh toán; in; trả tiền; điều chỉnh.
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import StockEvidence from '../stock/StockEvidence.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'
import {unitLabel} from '../../units'

const props=defineProps({name:{type:String,required:true},mobile:Boolean,ask:{type:Function,required:true},callFn:Function})
const emit=defineEmits(['changed','open','pay','credit','notice','error','loaded'])
const method=(name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.finance.supplier_invoice.'+name,args,write):lotusMethod('finance.supplier_invoice',name,args,write)
const d=ref(null),working=ref(false),cancelling=ref(false),reason=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const fmt=value=>Number(value||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const facts=computed(()=>d.value?[d.value.is_return?'Hóa đơn điều chỉnh trả hàng':'Hóa đơn nhà cung cấp',d.value.status,d.value.supplier_name,
 [d.value.series,d.value.bill_no].filter(Boolean).join(' · '),d.value.bill_date?'ngày '+shortDate(d.value.bill_date):'',d.value.due_date?'hạn trả '+shortDate(d.value.due_date):''].filter(Boolean).join(' · '):'')
async function load(){
 cancelling.value=false;reason.value=''
 try{d.value=await method('detail',{name:props.name});emit('loaded',d.value)}catch(e){d.value=null;emit('error',e.message||String(e))}
}
watch(()=>props.name,load,{immediate:true})
async function cancel(){
 if(!await props.ask('Hủy hóa đơn '+d.value.name+'? Công nợ của nhà cung cấp giảm lại; phiếu nhận liên quan quay về chờ hóa đơn.'))return
 if(working.value)return
 working.value=true;emit('error','')
 try{await method('cancel',{name:d.value.name,reason:reason.value.trim(),modified:d.value.modified},true);await load();emit('changed',d.value);emit('notice','Đã hủy hóa đơn '+d.value.name+'.')}
 catch(e){emit('error',e.message||String(e))}finally{working.value=false}
}
defineExpose({reload:load})
</script>

<template>
 <section v-if="d" class="invoice-detail" :aria-label="'Hóa đơn '+d.name">
  <p class="lotus-form-note">{{facts}}</p>
  <p v-if="d.cancel_reason" role="status">Đã hủy: {{d.cancel_reason}}</p>
  <ul class="invoice-detail__lines" aria-label="Dòng hóa đơn">
   <li v-for="row in d.items" :key="row.line"><strong>{{row.item_name}}</strong>
    <span>{{fmt(Math.abs(row.qty))}} {{unitLabel(row.uom)}} × {{money(row.rate,d.currency)}} = {{money(row.amount,d.currency)}} · thuế {{row.vat_code==='KCT'?'KCT':row.vat_code+'%'}}<template v-if="row.receipt"> · {{row.receipt}}</template></span>
    <small v-if="row.variance_reason">Lý do chênh lệch giá: {{row.variance_reason}}</small></li>
  </ul>
  <dl class="lotus-form-totals">
   <div><dt>Tiền hàng</dt><dd>{{money(d.net,d.currency)}}</dd></div>
   <div v-for="tax in d.taxes" :key="tax.description"><dt>{{tax.description}}</dt><dd>{{money(tax.amount,d.currency)}}</dd></div>
   <div><dt>Tổng thanh toán</dt><dd>{{money(d.amount,d.currency)}}</dd></div>
   <div v-if="d.printed_total"><dt>Tổng in trên hóa đơn</dt><dd>{{money(d.printed_total,d.currency)}}</dd></div>
   <div><dt>Còn phải trả</dt><dd>{{money(d.outstanding_amount,d.currency)}}</dd></div>
  </dl>
  <p v-if="d.rounding_adjustment" class="lotus-form-note" role="status">Ghi theo tổng in; phần làm tròn {{money(d.rounding_adjustment,d.currency)}} đã tính vào chi phí.</p>
  <p v-for="row in d.settlements" :key="row.doctype+row.name" class="lotus-form-note">{{row.kind}} <component :is="button" type="button" variant="link" @click="emit('open',row,row.doctype==='Purchase Invoice'?'invoices':'payments')">{{row.name}}</component> · {{money(row.amount,d.currency)}}</p>
  <StockEvidence doctype="Purchase Invoice" :name="d.name" :mobile="mobile" :readonly="d.docstatus===2" title="File gốc của hóa đơn"/>
  <p v-if="d.files.some(f=>f.attached_to_name!==d.name)" class="lotus-form-note">File ở phiếu nhận: <a v-for="file in d.files.filter(f=>f.attached_to_name!==d.name)" :key="file.name" :href="file.file_url" target="_blank" rel="noopener">{{file.file_name}} </a></p>

  <div v-if="cancelling" class="invoice-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do hủy hóa đơn" type="textarea"/>
   <component :is="button" type="button" variant="destructive" :disabled="working||reason.trim().length<3" @click="cancel">Hủy hóa đơn</component>
  </div>
  <div class="procurement-actions">
   <component :is="button" v-if="d.can_pay" type="button" :disabled="working" @click="emit('pay',d)">Trả tiền hóa đơn</component>
   <component :is="button" v-if="d.can_credit" type="button" variant="outline" :disabled="working" @click="emit('credit',d)">Lập hóa đơn điều chỉnh</component>
   <component :is="button" v-if="d.can_cancel" type="button" variant="outline" :disabled="working" @click="cancelling=!cancelling;reason=''">Hủy hóa đơn</component>
   <component :is="button" v-for="receipt in d.receipts" :key="receipt" type="button" variant="outline" @click="emit('open',{name:receipt},'receipts')">Phiếu nhận {{receipt}}</component>
   <component :is="button" v-for="receipt in d.quick_receipts" :key="receipt" type="button" variant="outline" @click="emit('open',{name:receipt},'quick')">Mua nhanh {{receipt}}</component>
   <component :is="link" as="a" variant="outline" :href="d.print_url" target="_blank" rel="noopener">In bảng kê hóa đơn</component>
  </div>
  <p v-if="d.docstatus===1&&!d.can_cancel&&d.settlements.length" class="lotus-form-note">Hóa đơn đã có thanh toán hoặc chứng từ liên quan: đảo phiếu chi trước, hoặc lập hóa đơn điều chỉnh.</p>
 </section>
</template>

<style>
.invoice-detail{display:grid;gap:var(--lotus-space-3,12px);min-width:0}
.invoice-detail__lines{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.invoice-detail__lines li{display:grid;gap:2px;padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);min-width:0}
.invoice-detail__lines span,.invoice-detail__lines small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.invoice-detail__form{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
</style>

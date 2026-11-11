<script setup>
// Sổ chi tiết công nợ một nhà cung cấp theo kỳ (spec 003, FR-059): số đầu kỳ, từng chứng từ (mở được), số cuối kỳ,
// in biên bản đối chiếu công nợ.
import {computed,ref,watch} from 'vue'
import ResponsiveForm from '../form/ResponsiveForm.vue'
import FormGrid from '../form/FormGrid.vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'

const props=defineProps({modelValue:Boolean,supplier:String,company:String,asOf:String,mobile:Boolean,callFn:Function})
const emit=defineEmits(['update:modelValue','open'])
const call=(name,args={})=>props.callFn?props.callFn('lotus_farm.procurement_queries.'+name,args):lotusMethod('procurement_queries',name,args)
const data=ref(null),busy=ref(false),error=ref(''),from=ref(''),to=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const TYPES={'Purchase Invoice':'invoices','Payment Entry':'payments','Journal Entry':'payments'}
async function load(){
 if(!props.supplier)return
 busy.value=true;error.value=''
 try{data.value=await call('supplier_statement',{company:props.company,supplier:props.supplier,from_date:from.value||null,to_date:to.value||null});from.value=data.value.from_date;to.value=data.value.to_date}
 catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
watch(()=>props.modelValue,open=>{if(open){data.value=null;to.value=props.asOf||'';from.value=to.value?to.value.slice(0,8)+'01':'';load()}},{immediate:true})
</script>

<template>
 <ResponsiveForm :mobile="mobile" :model-value="modelValue" :title="'Sổ chi tiết công nợ · '+(data?.supplier_name||'')" width="1080px" readonly :busy="busy" :error="error" @update:model-value="emit('update:modelValue',$event)">
  <FormGrid :columns="mobile?1:3">
   <LotusField v-model="from" :mobile="mobile" label="Từ ngày" type="date"/>
   <LotusField v-model="to" :mobile="mobile" label="Đến ngày" type="date"/>
   <component :is="button" type="button" variant="outline" :disabled="busy" @click="load">Xem kỳ này</component>
  </FormGrid>
  <template v-if="data">
   <dl class="lotus-form-totals"><div><dt>Số đầu kỳ</dt><dd>{{money(data.opening)}}</dd></div><div><dt>Tăng nợ (hóa đơn)</dt><dd>{{money(data.credit)}}</dd></div><div><dt>Giảm nợ (trả, điều chỉnh)</dt><dd>{{money(data.debit)}}</dd></div><div><dt>Số cuối kỳ</dt><dd>{{money(data.closing)}}</dd></div></dl>
   <p class="lotus-form-note" role="status">{{data.closing>=0?'Còn phải trả nhà cung cấp':'Nhà cung cấp đang giữ tiền tạm ứng'}} {{money(Math.abs(data.closing))}} · {{data.ledger_matches?'khớp sổ cái tài khoản phải trả':'lệch với sổ cái '+money(data.ledger_balance)+', kế toán kiểm tra'}}.</p>
   <ul class="supplier-statement__lines" aria-label="Chứng từ trong kỳ">
    <li v-for="row in data.lines" :key="row.doctype+row.name">
     <div><strong>{{row.kind_label}}<template v-if="row.bill_no"> · HĐ {{row.bill_no}}</template></strong><small>{{shortDate(row.date)}} · <component :is="button" type="button" variant="link" @click="emit('open',row,TYPES[row.doctype]||'payments')">{{row.name}}</component></small></div>
     <div class="supplier-statement__amount"><b>{{row.credit?'+'+money(row.credit):'−'+money(row.debit)}}</b><small>Còn {{money(row.balance)}}</small></div>
    </li>
   </ul>
   <p v-if="!data.lines.length" class="lotus-form-note">Không có chứng từ nào trong kỳ.</p>
  </template>
  <template #actions><component :is="link" v-if="data" as="a" variant="outline" :href="data.print_url" target="_blank" rel="noopener">In biên bản đối chiếu</component></template>
 </ResponsiveForm>
</template>

<style>
.supplier-statement__lines{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.supplier-statement__lines li{display:flex;justify-content:space-between;gap:var(--lotus-space-3,12px);padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);min-width:0}
.supplier-statement__lines div{display:grid;gap:2px;min-width:0}
.supplier-statement__lines small{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.supplier-statement__amount{text-align:right;white-space:nowrap}
</style>

<script setup>
// Hóa đơn chờ nhập (spec 003, FR-047, FR-048): mọi phiếu nhập mua chưa có hóa đơn đủ — theo đơn và Mua nhanh — kèm file,
// ảnh hóa đơn đã đính ở phiếu nhận. Chọn các phiếu của một nhà cung cấp rồi nhập hóa đơn; hóa đơn dịch vụ không cần phiếu.
import {computed,onMounted,ref,watch} from 'vue'
import InvoiceForm from './InvoiceForm.vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import LotusMobileCheck from '../LotusMobileCheck.vue'
import {Button} from '../ui/button'
import {Checkbox} from '../ui/checkbox'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'

const props=defineProps({company:String,mobile:Boolean,today:String,canPost:Boolean,suppliers:{type:Array,default:()=>[]},callFn:Function,uploader:Function})
const emit=defineEmits(['created','open','notice','error'])
const method=(name,args={})=>props.callFn?props.callFn('lotus_farm.finance.supplier_invoice.'+name,args):lotusMethod('finance.supplier_invoice',name,args)
const rows=ref([]),total=ref(0),amount=ref(0),busy=ref(false),supplier=ref(''),withFile=ref(''),picked=ref([]),form=ref(false),formReceipts=ref([])
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const check=computed(()=>props.mobile?LotusMobileCheck:Checkbox)
const fileOptions=[{value:'',label:'Tất cả'},{value:'1',label:'Đã có file hóa đơn'},{value:'0',label:'Chưa có file'}]
const chosen=computed(()=>rows.value.filter(r=>picked.value.includes(r.name)))
// One invoice: one supplier, and one kind of receipt (theo đơn, or Mua nhanh).
const problem=computed(()=>{
 if(!chosen.value.length)return 'Chọn phiếu nhận của hóa đơn.'
 if(new Set(chosen.value.map(r=>r.supplier)).size>1)return 'Các phiếu phải cùng một nhà cung cấp.'
 if(new Set(chosen.value.map(r=>r.mua_nhanh)).size>1)return 'Chọn riêng phiếu nhận theo đơn và phiếu Mua nhanh.'
 return ''
})
async function load(){
 busy.value=true;emit('error','')
 try{const result=await method('queue',{supplier:supplier.value||null,has_file:withFile.value===''?null:withFile.value,limit:500});rows.value=result?.rows||[];total.value=result?.total||0;amount.value=result?.amount||0
  picked.value=picked.value.filter(name=>rows.value.some(r=>r.name===name))}
 catch(e){emit('error',e.message||String(e))}finally{busy.value=false}
}
function toggle(row,on){picked.value=on?[...new Set([...picked.value,row.name])]:picked.value.filter(n=>n!==row.name)}
function enter(){formReceipts.value=[...picked.value];form.value=true}
function service(){formReceipts.value=[];form.value=true}
async function created(result){picked.value=[];emit('notice','Đã ghi hóa đơn '+result.invoice+' · '+money(result.amount)+'.'+(result.warnings?.length?' '+result.warnings.join(' '):''));emit('created',result);await load()}
watch([supplier,withFile],load)
onMounted(load)
defineExpose({reload:load})
</script>

<template>
 <section class="invoice-queue" aria-label="Hóa đơn chờ nhập">
  <div class="invoice-queue__filters">
   <LotusField v-model="supplier" :mobile="mobile" label="Nhà cung cấp" :options="suppliers" empty-option="Tất cả nhà cung cấp"/>
   <LotusField v-model="withFile" :mobile="mobile" label="File hóa đơn" :options="fileOptions" :searchable="false"/>
  </div>
  <p class="lotus-form-note" role="status">{{busy?'Đang tải…':total+' phiếu nhập chưa có hóa đơn đủ · tạm tính '+money(amount)}}</p>
  <ul class="invoice-queue__list">
   <li v-for="row in rows" :key="row.name" :class="{'is-picked':picked.includes(row.name)}">
    <component :is="check" v-if="canPost" :model-value="picked.includes(row.name)" :aria-label="'Chọn '+row.name" @update:model-value="toggle(row,$event)"/>
    <div class="invoice-queue__body">
     <strong>{{row.supplier_name}}</strong>
     <span>{{row.name}} · {{shortDate(row.date)}} · <b>{{row.source_type}}</b> · chưa có hóa đơn {{money(row.amount)}}</span>
     <small>{{row.lines.map(l=>l.item_name).slice(0,3).join(', ')}}<template v-if="row.lines.length>3"> và {{row.lines.length-3}} dòng khác</template></small>
     <small v-if="row.files.length">File đính kèm: <a v-for="file in row.files" :key="file.name" :href="file.file_url" target="_blank" rel="noopener">{{file.file_name}}</a></small>
     <small v-else>Chưa có file hóa đơn đính kèm.</small>
    </div>
    <component :is="button" type="button" variant="outline" size="sm" @click="emit('open',row)">Xem phiếu</component>
   </li>
  </ul>
  <p v-if="!busy&&!rows.length" class="lotus-form-note">Không còn phiếu nhập nào chờ hóa đơn.</p>
  <div v-if="canPost" class="procurement-actions">
   <component :is="button" type="button" :disabled="!!problem" @click="enter">Nhập hóa đơn cho {{chosen.length}} phiếu đã chọn</component>
   <component :is="button" type="button" variant="outline" @click="service">Hóa đơn dịch vụ (không phiếu nhận)</component>
   <span v-if="picked.length&&problem" class="lotus-form-note" role="status">{{problem}}</span>
  </div>
  <p v-else class="lotus-form-note">Bạn xem và đính kèm file ở phiếu nhận; kế toán nhập và ghi hóa đơn.</p>
  <InvoiceForm v-model="form" :receipts="formReceipts" :suppliers="suppliers" :mobile="mobile" :today="today" :call-fn="callFn" :uploader="uploader" @created="created"/>
 </section>
</template>

<style>
.invoice-queue{display:grid;gap:var(--lotus-space-3,12px);min-width:0}
.invoice-queue__filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:var(--lotus-space-3,12px)}
.invoice-queue__list{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.invoice-queue__list li{display:flex;align-items:flex-start;gap:var(--lotus-space-3,12px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:var(--lotus-surface);min-width:0}
.invoice-queue__list li.is-picked{border-color:var(--lotus-primary)}
.invoice-queue__body{display:grid;gap:2px;flex:1;min-width:0}
.invoice-queue__body span,.invoice-queue__body small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.invoice-queue__body a{margin-right:var(--lotus-space-2,8px)}
</style>

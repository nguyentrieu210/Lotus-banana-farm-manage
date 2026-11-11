<script setup>
import {computed,ref,watch} from 'vue'
import ListPage from './ListPage.vue'
import LotusField from './form/LotusField.vue'
import {Button} from './ui/button'
import {unitLabel} from '../units'
import {money,newKey,supplierOffer,cheapestCost,needsReason,defaultChoices,defaultReasons,compareSelections} from '../procurement'
import CompareCards from './procurement/CompareCards.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import {lotusMethod} from './procurement/use-procurement'
// So sánh giá: one row per request line (or item), one column per supplier. The cheapest landed cost per stock unit
// is chosen by default; picking another supplier asks for a reason. "Tạo đơn" turns the choices into purchase orders
// (lotus_farm.procurement.select_quotes). Every order is a draft waiting for the director's signature (spec 003, FR-020);
// choosing an approver here sends the new orders to them at once. On the phone each item is a card (CompareCards).
const props=defineProps({company:String,mobile:Boolean,canCreate:Boolean,api:{type:Function,required:true}})
const emit=defineEmits(['created'])
const data=ref(null),busy=ref(false),saving=ref(false),error=ref(''),request=ref(''),choices=ref({}),reasons=ref({}),search=ref(''),key=ref(''),notice=ref('')
const approver=ref(''),approvers=ref([])
async function loadApprovers(){
 if(!props.canCreate||!props.company)return
 try{const found=await lotusMethod('purchasing','approver_options',{company:props.company});approvers.value=(found?.candidates?.APPROVE||[]).map(c=>({value:c.user,label:c.name}))}catch{approvers.value=[]}
}
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
async function load(){
 if(!props.company)return
 busy.value=true;error.value=''
 try{data.value=await props.api('compare',{company:props.company,...(request.value?{request:request.value}:{})});choices.value=defaultChoices(data.value.rows);reasons.value=defaultReasons(data.value.rows);key.value=''}
 catch(e){error.value=e.message}finally{busy.value=false}
}
watch(()=>[props.company,request.value],load,{immediate:true})
watch(()=>props.company,loadApprovers,{immediate:true})
const suppliers=computed(()=>data.value?.suppliers||[])
const rows=computed(()=>{const q=search.value.trim().toLocaleLowerCase('vi');return (data.value?.rows||[]).filter(r=>!q||[r.item_name,r.item,r.request].some(x=>String(x||'').toLocaleLowerCase('vi').includes(q)))})
const requestOptions=computed(()=>(data.value?.requests||[]).map(r=>({value:r.name,label:r.name+' · '+r.state})))
const columns=computed(()=>[
 {field:'item_name',headerName:'Mặt hàng',minWidth:220,flex:2,valueGetter:p=>p.data.item_name+(p.data.request?' · '+p.data.request:'')},
 {field:'need_qty',headerName:'Còn cần mua',minWidth:120,sum:false,valueFormatter:p=>p.value==null?'—':fmt(p.value)+' '+unitLabel(p.data.stock_uom)},
 ...suppliers.value.map((s,i)=>({field:'s'+i,headerName:s.label,minWidth:150,sum:false,sortable:false,valueGetter:p=>supplierOffer(p.data,s.name)?.unit_cost??null})),
 {field:'reason',headerName:'Lý do chọn (khi không chọn giá thấp nhất)',minWidth:240,flex:1.5,sortable:false,sum:false}
])
const chosen=computed(()=>compareSelections(rows.value,choices.value,reasons.value))
const missingReason=computed(()=>rows.value.some(r=>choices.value[r.key]&&needsReason(r,choices.value[r.key])&&!String(reasons.value[r.key]||'').trim()))
const pendingRequests=computed(()=>rows.value.some(r=>choices.value[r.key]&&r.request&&!r.approved))
function pick(row,offer){if(!offer)return;choices.value={...choices.value,[row.key]:choices.value[row.key]===offer.line?'':offer.line}}
async function create(){
 if(saving.value||!chosen.value.length)return
 saving.value=true;error.value=''
 try{
  const result=await props.api('select_quotes',{company:props.company,selections:chosen.value,client_key:key.value||=newKey(),...(approver.value?{approver:approver.value}:{})},true)
  key.value=''
  emit('created',result)
  await load()
 }catch(e){error.value=e.message}finally{saving.value=false}
}
// Lưu lựa chọn mà chưa tạo đơn: the choice stays on the proposal line, so "Lập đơn từ đề xuất" brings supplier and price.
const savable=computed(()=>rows.value.filter(r=>r.request&&r.request_line&&(choices.value[r.key]||'')!==(r.selected_line||'')))
async function saveChoices(){
 if(saving.value||!savable.value.length||missingReason.value)return
 saving.value=true;error.value='';notice.value=''
 try{
  for(const row of savable.value){
   const offer=(row.offers||[]).find(o=>o.line===choices.value[row.key])
   await props.api('choose_quote',{company:props.company,request:row.request,request_item:row.request_line,quotation:offer?.quotation||'',quotation_item:offer?.line||'',reason:offer&&needsReason(row,offer.line)?String(reasons.value[row.key]||'').trim():''},true)
  }
  notice.value='Đã lưu lựa chọn báo giá.'
  await load()
 }catch(e){error.value=e.message}finally{saving.value=false}
}
defineExpose({refresh:load})
</script>

<template>
 <section v-if="mobile" class="compare-mobile" aria-label="So sánh giá">
  <LotusField v-model="request" mobile label="Đề xuất mua" :options="requestOptions" empty-option="Mọi đề xuất và báo giá lẻ"/>
  <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="busy" kind="loading">Đang tải báo giá…</LotusMobileFeedback>
  <p v-if="!busy&&!rows.length" class="mobile-empty">Chưa có báo giá còn hiệu lực.</p>
  <CompareCards v-model:choices="choices" v-model:reasons="reasons" :rows="rows" :suppliers="suppliers" :disabled="saving"/>
  <p v-if="pendingRequests" class="lotus-form-note" role="status">Có dòng thuộc đề xuất chưa duyệt xong: chưa tạo đơn được cho các dòng này.</p>
  <template v-if="canCreate&&rows.length">
   <LotusField v-if="approvers.length" v-model="approver" mobile label="Gửi duyệt ngay cho" :options="approvers" empty-option="Chỉ tạo đơn nháp" :searchable="false"/>
   <LotusMobileButton :disabled="saving||!savable.length||missingReason" @click="saveChoices">Lưu lựa chọn ({{savable.length}})</LotusMobileButton>
   <LotusMobileButton variant="primary" :disabled="saving||busy||!chosen.length||missingReason" @click="create">Tạo đơn từ lựa chọn ({{chosen.length}})</LotusMobileButton>
  </template>
 </section>
 <!-- ListPage forwards the cell-* slots it sees when created: rebuild it when the supplier columns change. -->
 <ListPage v-else :key="suppliers.map(s=>s.name).join('|')" title="So sánh giá" :rows="rows" :columns="columns" :loading="busy" :error="error" v-model:search="search" search-placeholder="Tìm mặt hàng, đề xuất…" row-key="key" :row-detail="false"
   empty="Chưa có báo giá còn hiệu lực. Thêm báo giá hoặc Nhập Excel ở mục Báo giá." @refresh="load">
  <template #filters><LotusField v-model="request" aria-label="Đề xuất mua" :options="requestOptions" empty-option="Mọi đề xuất và báo giá lẻ"/></template>
  <template #actions><Button v-if="canCreate" :disabled="saving||busy||!chosen.length||missingReason" @click="create">Tạo đơn từ lựa chọn ({{chosen.length}})</Button><Button v-if="canCreate" variant="outline" :disabled="saving||!savable.length||missingReason" @click="saveChoices">Lưu lựa chọn ({{savable.length}})</Button><LotusField v-if="canCreate&&approvers.length" v-model="approver" aria-label="Gửi duyệt ngay cho" :options="approvers" empty-option="Chỉ tạo đơn nháp" :searchable="false"/></template>
  <template #before>
   <p class="lotus-form-note">Giá đủ đã gồm VAT và vận chuyển, tính trên 1 đơn vị tồn kho. Ô được tô là nhà cung cấp đang chọn; mặc định chọn giá thấp nhất. Mọi đơn tạo ra đều chờ giám đốc ký duyệt.</p>
   <p v-if="pendingRequests" class="lotus-form-note" role="status">Có dòng thuộc đề xuất chưa duyệt xong: chưa tạo đơn được cho các dòng này, bỏ chọn hoặc chờ đề xuất được duyệt.</p>
  </template>
  <template v-for="(s,i) in suppliers" :key="s.name" #[`cell-s${i}`]="{row}">
   <button v-if="supplierOffer(row,s.name)" type="button" class="compare-offer" :class="{'is-chosen':choices[row.key]===supplierOffer(row,s.name).line,'is-best':supplierOffer(row,s.name).unit_cost===cheapestCost(row)}"
     :aria-pressed="choices[row.key]===supplierOffer(row,s.name).line" :aria-label="'Chọn '+s.label+' cho '+row.item_name" @click.stop="pick(row,supplierOffer(row,s.name))">
    <small>{{[supplierOffer(row,s.name).unit_cost===cheapestCost(row)&&'rẻ nhất',supplierOffer(row,s.name).docstatus===0&&'nháp'].filter(Boolean).join(' · ')}}</small><span :title="money(supplierOffer(row,s.name).unit_cost)+' / '+unitLabel(row.stock_uom)">{{money(supplierOffer(row,s.name).unit_cost)}}</span>
   </button>
   <span v-else class="compare-empty">—</span>
  </template>
  <template #cell-reason="{row}">
   <LotusField v-if="choices[row.key]&&needsReason(row,choices[row.key])" v-model="reasons[row.key]" :aria-label="'Lý do chọn '+row.item_name" placeholder="Vì sao không chọn giá thấp nhất?"/>
   <span v-else class="compare-empty">{{choices[row.key]?'Giá thấp nhất':'Chưa chọn'}}</span>
  </template>
 </ListPage>
</template>

<style>
.compare-offer{display:flex;align-items:baseline;justify-content:flex-end;width:100%;height:26px;gap:6px;white-space:nowrap;overflow:hidden;padding:0 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-sm,6px);background:var(--lotus-surface);color:var(--lotus-text);text-align:right;cursor:pointer;font:inherit;line-height:1.25}
.compare-offer small{overflow:hidden;text-overflow:ellipsis;color:var(--lotus-muted);font-size:11px;font-weight:400}
.compare-offer.is-best{border-color:var(--lotus-success,var(--lotus-primary))}
.compare-offer.is-chosen{background:var(--lotus-primary-subtle);border-color:var(--lotus-primary);font-weight:600}
.compare-empty{color:var(--lotus-muted)}
</style>

<script setup>
import {unitLabel} from '../units'
import {hrCatalogLabel} from '../hr-catalog-labels'
import '../procurement.css'
import {computed,onMounted,ref,watch} from 'vue'
import {Cell,CellGroup} from 'vant'
import {call} from '../api'
import ListPage from './ListPage.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusField from './form/LotusField.vue'
import FormSection from './form/FormSection.vue'
import ProcurementMasterForm from './ProcurementMasterForm.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import {money} from '../procurement'
// Nhà cung cấp / Hàng mua: server-paged list; a record opens in the standard dialog (desktop) or inline (phone).
const props=defineProps({company:String,kind:String,mobile:Boolean})
const emit=defineEmits(['navigate','dirty'])
const rows=ref([]),search=ref(''),state=ref('active'),group=ref(''),start=ref(0),total=ref(0),more=ref(false),busy=ref(false),error=ref(''),options=ref({}),editing=ref(false),selected=ref(''),history=ref(null),dirty=ref(false)
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const api=(m,args={})=>call('lotus_farm.procurement_masters.'+m,args)
const suppliers=computed(()=>props.kind==='suppliers')
const columns=computed(()=>suppliers.value?[
 {field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200,flex:1},{field:'supplier_group',headerName:'Nhóm NCC',valueFormatter:p=>hrCatalogLabel(p.value)},{field:'tax_id',headerName:'Mã số thuế'},{field:'lotus_supplier_contact',headerName:'Liên hệ'},{field:'lotus_supplier_phone',headerName:'Điện thoại'},{field:'email_id',headerName:'Email'}]:[
 {field:'name',headerName:'Mã hàng'},{field:'item_name',headerName:'Tên hàng',minWidth:200,flex:1},{field:'item_group',headerName:'Nhóm hàng',valueFormatter:p=>hrCatalogLabel(p.value)},{field:'stock_uom',headerName:'Đơn vị gốc',valueFormatter:p=>unitLabel(p.value)},{headerName:'Loại',valueGetter:p=>p.data.is_fixed_asset?'Tài sản':p.data.is_stock_item?'Hàng tồn kho':'Dịch vụ'}])
const canCreate=computed(()=>suppliers.value?options.value.can_create_supplier:options.value.can_create_item)
const addLabel=computed(()=>suppliers.value?'Thêm nhà cung cấp':'Thêm hàng mua')
const groupOptions=computed(()=>(suppliers.value?options.value.supplier_groups||[]:options.value.item_groups||[]).map(r=>({value:r.name,label:hrCatalogLabel(r.name)})))
const stateOptions=[{value:'active',label:'Đang dùng'},{value:'disabled',label:'Ngừng dùng'},{value:'all',label:'Tất cả'}]
const historyLinks=[['quotes','Báo giá'],['orders','Đơn mua'],['receipts','Phiếu nhận'],['invoices','Hóa đơn'],['payments','Thanh toán'],['payables','Công nợ']]
let timer
async function load(){busy.value=true;error.value='';try{const r=await api('listing',{company:props.company,kind:props.kind,search:search.value,state:state.value,group:group.value,start:start.value});rows.value=r.rows;total.value=r.total_count;more.value=r.has_more}catch(e){error.value=e.message}finally{busy.value=false}}
async function open(row){selected.value=row?.name||'';editing.value=true;history.value=null;setDirty(false);if(row&&suppliers.value)try{history.value=await call('lotus_farm.procurement_queries.supplier_history',{company:props.company,supplier:row.name})}catch(e){error.value=e.message}}
function setDirty(v){dirty.value=v;emit('dirty',v)}
function close(){editing.value=false;selected.value='';setDirty(false)}
async function saved(){close();await load()}
function reset(){start.value=0;load()}
watch(search,()=>{clearTimeout(timer);timer=setTimeout(reset,220)})
onMounted(async()=>{try{options.value=await api('options',{company:props.company});await load()}catch(e){error.value=e.message}})
watch(()=>[props.company,props.kind],()=>{close();group.value='';reset()})
defineExpose({hasChanges:()=>dirty.value,close})
</script>

<template>
 <template v-if="!mobile">
  <ListPage :title="suppliers?'Nhà cung cấp':'Hàng mua'" :rows="rows" :columns="columns" :loading="busy" :error="error" v-model:search="search" search-placeholder="Tên, mã, MST, điện thoại…" @refresh="load"
    paged :start="start" :total="total" :has-more="more" @update:start="value=>{start=value;load()}" :storage-key="'procurement-master-'+kind" show-empty-headers interactive empty="Chưa có hồ sơ phù hợp." @open="open">
   <template #filters><slot name="scope"/><LotusField v-model="state" aria-label="Trạng thái" :options="stateOptions" :searchable="false" :empty-option="null" @update:model-value="reset"/><LotusField v-model="group" aria-label="Nhóm" :options="groupOptions" :searchable="false" empty-option="Tất cả nhóm" @update:model-value="reset"/></template>
   <template #actions><Button v-if="canCreate" @click="open()">{{addLabel}}</Button></template>
  </ListPage>
  <WorkspaceModal :model-value="editing" :title="selected?(suppliers?'Hồ sơ nhà cung cấp':'Hồ sơ hàng mua'):addLabel" width="1080px" @update:model-value="value=>!value&&emit('navigate','close-master')">
   <ProcurementMasterForm v-if="editing" :key="kind+selected" :company="company" :kind="kind" :name="selected" @saved="saved" @dirty="setDirty"/>
   <FormSection v-if="history" title="Giao dịch với nhà cung cấp">
    <div class="procurement-actions"><Button v-for="[id,label] in historyLinks" v-show="history[id]" :key="id" variant="outline" size="sm" @click="emit('navigate',id,selected)">{{label}} · {{history[id]?.total_count??history[id]?.length??0}}</Button></div>
    <dl v-if="history.payables" class="lotus-form-totals"><div><dt>Phải trả</dt><dd>{{money(history.payables.owed)}}</dd></div><div><dt>Tạm ứng</dt><dd>{{money(history.payables.advance)}}</dd></div><div><dt>Quá hạn</dt><dd>{{money(history.payables.overdue)}}</dd></div></dl>
    <div v-for="[id,label] in historyLinks.slice(0,5)" :key="id" class="procurement-actions"><Button v-for="r in history[id]||[]" :key="r.name" variant="link" @click="emit('navigate',id,selected,r)">{{label}} · {{r.name}} · {{r.date}}</Button></div>
   </FormSection>
  </WorkspaceModal>
 </template>

 <template v-else>
  <p v-if="error" role="alert" class="procurement-error">{{error}}</p>
  <template v-if="!editing">
   <div class="procurement-toolbar"><slot name="scope"/>
    <LotusField v-model="search" mobile label="Tìm kiếm" placeholder="Tên, mã, MST, điện thoại…"/>
    <LotusField v-model="state" mobile label="Trạng thái" :searchable="false" :options="stateOptions" @update:model-value="reset"/>
    <LotusField v-model="group" mobile label="Nhóm" :options="[{value:'',label:'Tất cả'},...groupOptions]" @update:model-value="reset"/>
   </div>
   <component :is="button" v-if="canCreate" @click="open()">{{addLabel}}</component>
   <CellGroup :border="false"><Cell v-for="r in rows" :key="r.name" :title="r.supplier_name||r.item_name" :label="r.tax_id||r.name" is-link @click="open(r)"/><Cell v-if="!rows.length" :title="busy?'Đang tải…':'Chưa có hồ sơ phù hợp.'"/></CellGroup>
   <div class="procurement-actions"><span>{{total?start+1:0}}–{{start+rows.length}} / {{total}}</span><component :is="button" :disabled="!start||busy" @click="start-=50;load()">Trước</component><component :is="button" :disabled="!more||busy" @click="start+=50;load()">Sau</component></div>
  </template>
  <template v-else><component :is="button" @click="emit('navigate','close-master')">Đóng hồ sơ</component>
   <ProcurementMasterForm :key="kind+selected" :company="company" :kind="kind" :name="selected" mobile @saved="saved" @dirty="setDirty"/>
   <section v-if="history" class="procurement-chain"><div class="procurement-actions"><component :is="button" v-for="[id,label] in historyLinks" v-show="history[id]" :key="id" @click="emit('navigate',id,selected)">{{label}} · {{history[id]?.total_count??history[id]?.length??0}}</component></div>
    <p v-if="history.payables">Phải trả {{money(history.payables.owed)}} · Tạm ứng {{money(history.payables.advance)}} · Quá hạn {{money(history.payables.overdue)}}</p></section>
  </template>
 </template>
</template>

<script setup>
import '../procurement.css'
import {computed,onMounted,ref,watch} from 'vue'
import {Cell,CellGroup} from 'vant'
import {call} from '../api'
import DataTable from './DataTable.vue'
import ProcurementField from './ProcurementField.vue'
import ProcurementMasterForm from './ProcurementMasterForm.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import {money} from '../procurement'
const props=defineProps({company:String,kind:String,mobile:Boolean})
const emit=defineEmits(['navigate','dirty'])
const rows=ref([]),search=ref(''),state=ref('active'),group=ref(''),start=ref(0),total=ref(0),more=ref(false),busy=ref(false),error=ref(''),options=ref({}),editing=ref(false),selected=ref(''),history=ref(null),dirty=ref(false)
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const api=(m,args={})=>call('lotus_farm.procurement_masters.'+m,args)
const columns=computed(()=>props.kind==='suppliers'?[
 {field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200,flex:1},{field:'supplier_group',headerName:'Nhóm NCC'},{field:'tax_id',headerName:'Mã số thuế'},{field:'lotus_supplier_contact',headerName:'Liên hệ'},{field:'lotus_supplier_phone',headerName:'Điện thoại'},{field:'email_id',headerName:'Email'}]:[
 {field:'name',headerName:'Mã hàng'},{field:'item_name',headerName:'Tên hàng',minWidth:200,flex:1},{field:'item_group',headerName:'Nhóm hàng'},{field:'stock_uom',headerName:'Đơn vị gốc'},{headerName:'Loại',valueGetter:p=>p.data.is_fixed_asset?'Tài sản':p.data.is_stock_item?'Hàng tồn kho':'Dịch vụ'}])
async function load(){busy.value=true;error.value='';try{const r=await api('listing',{company:props.company,kind:props.kind,search:search.value,state:state.value,group:group.value,start:start.value});rows.value=r.rows;total.value=r.total_count;more.value=r.has_more}catch(e){error.value=e.message}finally{busy.value=false}}
async function open(row){selected.value=row?.name||'';editing.value=true;history.value=null;setDirty(false);if(row&&props.kind==='suppliers')try{history.value=await call('lotus_farm.procurement_queries.supplier_history',{company:props.company,supplier:row.name})}catch(e){error.value=e.message}}
function setDirty(v){dirty.value=v;emit('dirty',v)}
function close(){editing.value=false;selected.value='';setDirty(false)}
async function saved(){close();await load()}
function reset(){start.value=0;load()}
onMounted(async()=>{try{options.value=await api('options',{company:props.company});await load()}catch(e){error.value=e.message}})
watch(()=>[props.company,props.kind],()=>{close();group.value='';reset()})
defineExpose({hasChanges:()=>dirty.value,close})
</script>
<template><p v-if="error" role="alert" class="procurement-error">{{error}}</p>
 <template v-if="!editing"><div class="procurement-toolbar">
  <ProcurementField v-model="search" :mobile="mobile" label="Tìm kiếm" placeholder="Tên, mã, MST, điện thoại…" @update:model-value="reset"/>
  <ProcurementField v-model="state" :mobile="mobile" label="Trạng thái" :searchable="false" :options="[{value:'active',label:'Đang dùng'},{value:'disabled',label:'Ngừng dùng'},{value:'all',label:'Tất cả'}]" @update:model-value="reset"/>
  <ProcurementField v-model="group" :mobile="mobile" label="Nhóm" :options="[{value:'',label:'Tất cả'},...(kind==='suppliers'?options.supplier_groups||[]:options.item_groups||[]).map(r=>({value:r.name,label:r.name}))]" @update:model-value="reset"/>
  <component :is="button" :disabled="busy" @click="load">Làm mới</component>
  <component :is="button" v-if="kind==='suppliers'?options.can_create_supplier:options.can_create_item" @click="open()">{{kind==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'}}</component>
 </div><DataTable v-if="!mobile" :rows="rows" :columns="columns" :loading="busy" interactive @open="open" empty="Chưa có hồ sơ phù hợp."/>
 <CellGroup v-else :border="false"><Cell v-for="r in rows" :key="r.name" :title="r.supplier_name||r.item_name" :label="r.tax_id||r.name" is-link @click="open(r)"/><Cell v-if="!rows.length" :title="busy?'Đang tải…':'Chưa có hồ sơ phù hợp.'"/></CellGroup>
 <div class="procurement-actions"><span>{{total?start+1:0}}–{{start+rows.length}} / {{total}}</span><component :is="button" :disabled="!start||busy" @click="start-=50;load()">Trước</component><component :is="button" :disabled="!more||busy" @click="start+=50;load()">Sau</component></div></template>
 <template v-else><component :is="button" @click="emit('navigate','close-master')">Đóng hồ sơ</component>
  <ProcurementMasterForm :key="kind+selected" :company="company" :kind="kind" :name="selected" :mobile="mobile" @saved="saved" @dirty="setDirty"/>
  <section v-if="history" class="procurement-chain"><div class="procurement-actions"><component :is="button" v-for="[id,label] in [['quotes','Báo giá'],['orders','Đơn mua'],['receipts','Phiếu nhận'],['invoices','Hóa đơn'],['payments','Thanh toán'],['payables','Công nợ']]" v-show="history[id]" :key="id" @click="emit('navigate',id,selected)">{{label}} · {{history[id]?.total_count??history[id]?.length??0}}</component></div>
   <p v-if="history.payables">Phải trả {{money(history.payables.owed)}} · Tạm ứng {{money(history.payables.advance)}} · Quá hạn {{money(history.payables.overdue)}}</p>
   <div v-for="[id,label] in [['quotes','Báo giá'],['orders','Đơn mua'],['receipts','Phiếu nhận'],['invoices','Hóa đơn'],['payments','Thanh toán']]" :key="id"><component :is="button" v-for="r in history[id]||[]" :key="r.name" variant="link" @click="emit('navigate',id,selected,r)">{{label}} · {{r.name}} · {{r.date}}</component></div>
  </section>
 </template>
</template>

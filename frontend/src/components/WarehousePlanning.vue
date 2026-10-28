<script setup>
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {unitLabel} from '../units'
import {updateColumnFilter,shiftISODate} from '../stock-filter-state'
import {call} from '../api'
import DataTable from './DataTable.vue'
import ListPage from './ListPage.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import ModalForm from './form/ModalForm.vue'
import LotusField from './form/LotusField.vue'
import {DateRangePicker} from './ui/date-picker'
import {Button as UiButton} from './ui/button'
// Nhu cầu vật tư: approved demand vs stock, purchase requests still to order and purchase orders still to receive.
// Receiving goods uses the one shared WarehouseReceiving of the stock workspace (events receive / open-receipt).
const props=defineProps({company:String,warehouse:String,today:String})
const emit=defineEmits(['receive','open-receipt'])
const api=(name,args={},write=false)=>call('lotus_farm.warehouse_planning.'+name,args,write)
const data=ref(null),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),from=ref(props.today||''),to=ref(shiftISODate(props.today,6)||''),search=ref(''),searchDraft=ref(''),start=ref(0),filters=ref({}),view=ref('coverage')
const detail=ref(null),detailOpen=ref(false),selectedStores=ref({}),request=ref(null),requestOpen=ref(false),confirmAction=ref('')
const sortModel=ref([])
let version=0
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
const warehouseLabel=id=>data.value?.warehouses?.find(w=>w.name===id)?.warehouse_name||id||'—'
const unit=unitLabel
const views=[{id:'coverage',label:'Nhu cầu vật tư'},{id:'requests',label:'Đề nghị mua'},{id:'orders',label:'Hàng chờ về'}]
async function load(reset=false){if(reset)start.value=0;if(!props.company)return;if(from.value&&to.value&&from.value>to.value){error.value='Từ ngày không được sau đến ngày.';return}const id=++version;busy.value=true;error.value='';try{const result=await api('overview',{company:props.company,warehouse:props.warehouse,from_date:from.value,to_date:to.value,search:search.value,start:start.value,sort_model:JSON.stringify(sortModel.value),column_filters:JSON.stringify(filters.value)});if(id===version)data.value=result}catch(e){if(id===version)error.value='Không tải được danh sách mới: '+e.message}finally{if(id===version)busy.value=false}}
watch(()=>[props.company,props.warehouse],()=>{filters.value={};load(true)})
watch([from,to],()=>load(true))
onMounted(()=>load(true))
function filter({field,values}){filters.value=updateColumnFilter(filters.value,field,values);load(true)}
let searchTimer=null
watch(searchDraft,value=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load(true)}},220)})
onUnmounted(()=>clearTimeout(searchTimer))
watch(()=>props.today,value=>{if(value&&!from.value){from.value=value;to.value=shiftISODate(value,6)}})
function resetFilters(){filters.value={};search.value='';searchDraft.value='';from.value=props.today||'';to.value=shiftISODate(from.value,6);sortModel.value=[];load(true)}
const hasFilters=computed(()=>Object.keys(filters.value).length>0||!!search.value||!!from.value&&!!props.today&&(from.value!==props.today||to.value!==shiftISODate(props.today,6)))
const requestRows=computed(()=>{const q=search.value.toLocaleLowerCase('vi');return (data.value?.requests||[]).filter(r=>!q||[r.name,r.item_name,r.warehouse,r.status].some(x=>String(x||'').toLocaleLowerCase('vi').includes(q)))})
const orderRows=computed(()=>{const q=search.value.toLocaleLowerCase('vi');return (data.value?.orders||[]).filter(r=>!q||[r.name,r.item_name,r.supplier,r.warehouse].some(x=>String(x||'').toLocaleLowerCase('vi').includes(q)))})
const numeric=(field,headerName)=>({field,headerName,minWidth:92,type:'numericColumn',valueFormatter:p=>fmt(p.value)})
const columns=[{field:'item',headerName:'Tên hàng',minWidth:210,flex:1.8,valueFormatter:p=>p.data?p.data.item_name+' · '+p.value:p.value,tooltipValueGetter:p=>p.data.item_name+' · '+p.value},{field:'warehouse',headerName:'Kho cấp',minWidth:130,valueFormatter:p=>warehouseLabel(p.value)},{field:'uom',headerName:'ĐVT',minWidth:65,valueFormatter:p=>unit(p.value)},numeric('remaining_qty','Cần dùng'),numeric('available_qty','Có thể dùng'),numeric('shortage_qty','Còn thiếu'),numeric('incoming_qty','Sắp về'),numeric('to_buy_qty','Cần mua'),{field:'status',headerName:'Tình trạng',minWidth:120}]
const sourceColumns=[{field:'name',headerName:'Nguồn',minWidth:210},{field:'date',headerName:'Ngày cần',minWidth:110},{field:'farm',headerName:'Vườn',minWidth:150},{field:'area',headerName:'Khu vực / lô',minWidth:150},numeric('required_qty','Nhu cầu duyệt'),numeric('issued_qty','Đã cấp'),numeric('draft_qty','Đang lập phiếu'),numeric('remaining_qty','Còn cần cấp')]
const orderColumns=[{field:'name',headerName:'Đơn mua',minWidth:210},{field:'supplier',headerName:'Nhà cung cấp',minWidth:170},{field:'item_name',headerName:'Tên hàng',minWidth:210},{field:'warehouse',headerName:'Kho nhận',minWidth:145,valueFormatter:p=>warehouseLabel(p.value)},numeric('qty','Chưa nhận'),{field:'uom',headerName:'Đơn vị',minWidth:80,valueFormatter:p=>unit(p.value)},{field:'date',headerName:'Dự kiến về',minWidth:110},{field:'overdue',headerName:'Tiến độ',minWidth:110,valueFormatter:p=>p.value?'Quá hẹn':'Đang chờ'}]
const requestColumns=[{field:'name',headerName:'Đề nghị mua',minWidth:210},{field:'item_name',headerName:'Vật tư',minWidth:210},{field:'warehouse',headerName:'Kho nhận',minWidth:145,valueFormatter:p=>warehouseLabel(p.value)},numeric('qty','Chưa mua'),{field:'uom',headerName:'Đơn vị',minWidth:80,valueFormatter:p=>unit(p.value)},{field:'date',headerName:'Ngày cần',minWidth:110},{field:'status',headerName:'Trạng thái',minWidth:110}]
const purchaseItems=[{field:'item_name',headerName:'Vật tư',minWidth:220},numeric('qty','Số lượng'),{field:'uom',headerName:'Đơn vị',valueFormatter:p=>unit(p.value)},{field:'warehouse',headerName:'Kho nhận',minWidth:145,valueFormatter:p=>warehouseLabel(p.value)},{field:'date',headerName:'Ngày cần',minWidth:110}]
const storeOptions=computed(()=>(data.value?.warehouses||[]).map(store=>({value:store.name,label:store.warehouse_name})))
function show(row){detail.value=row;detailOpen.value=true}
async function openRequest(name){try{request.value=await api('purchase_request',{name});confirmAction.value='';requestOpen.value=true}catch(e){error.value=e.message}}
async function buy(row){if(saving.value)return;saving.value=true;error.value='';try{const result=await api('create_purchase_request',{company:props.company,warehouse:row.warehouse,from_date:from.value,to_date:to.value,items:[row.item]},true);notice.value=result.name?'Đã tạo đề nghị mua nháp '+result.name:result.note;detailOpen.value=false;await load();if(result.name)await openRequest(result.name)}catch(e){error.value=e.message}finally{saving.value=false}}
async function assign(source){if(saving.value)return;saving.value=true;try{await api('assign_warehouse',{company:props.company,requirement:source.name,warehouse:selectedStores.value[source.name]},true);await load()}catch(e){error.value=e.message}finally{saving.value=false}}
async function act(action){if(saving.value)return;saving.value=true;error.value='';try{await api('purchase_action',{name:request.value.name,modified:request.value.modified,action},true);requestOpen.value=false;notice.value=action==='submit'?'Đã duyệt đề nghị mua. Chưa tính là hàng chờ nhập cho tới khi có đơn mua đã duyệt.':'Đã xóa đề nghị mua nháp.';await load()}catch(e){error.value=e.message}finally{saving.value=false}}
const printURL=(doctype,name)=>'/lotus/in-phieu?'+new URLSearchParams({doctype,name})
function openOrder(name){emit('receive',name)}
function openReceipt(name){emit('open-receipt',name)}
const unresolved=computed(()=>data.value?.unmapped||[])
const listRows=computed(()=>view.value==='coverage'?data.value?.rows||[]:view.value==='requests'?requestRows.value:orderRows.value)
const listColumns=computed(()=>view.value==='coverage'?columns:view.value==='requests'?requestColumns:orderColumns)
const empty={coverage:'Chưa có nhu cầu vật tư đã duyệt trong khoảng ngày này.',requests:'Chưa có đề nghị mua còn chờ đặt hàng.',orders:'Chưa có đơn mua đã duyệt còn chờ nhận.'}
function openRow(row){if(view.value==='coverage')show(row);else if(view.value==='requests')openRequest(row.name);else openOrder(row.name)}
defineExpose({refresh:()=>load(true),openReceipt})
</script>
<template>
 <div class="warehouse-planning">
  <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
  <WorkspaceTabs :items="views" :model-value="view" label="Nhu cầu và mua hàng" @update:model-value="value=>view=value"/>
  <p v-for="warning in data?.warnings" :key="warning" class="stock-error" role="alert">{{warning}}</p>
  <section v-if="unresolved.length" class="planning-unmapped"><strong>Nhu cầu chưa xác định kho cấp</strong>
   <div v-for="source in unresolved" :key="source.name+source.line"><span>{{source.name}} · {{source.item_name}} · {{fmt(source.remaining_qty)}} {{unit(source.uom)}} · {{source.area}}</span><LotusField v-if="source.can_assign" v-model="selectedStores[source.name]" aria-label="Kho cấp cho nhu cầu" :options="storeOptions" :searchable="false" empty-option="Chọn kho cấp"/><UiButton v-if="source.can_assign" variant="outline" :disabled="saving||!selectedStores[source.name]" @click="assign(source)">Gán kho</UiButton></div>
  </section>
  <ListPage :title="views.find(v=>v.id===view).label" :rows="listRows" :columns="listColumns" :loading="busy" :error="error" v-model:search="searchDraft" search-placeholder="Tìm vật tư, phiếu…" @refresh="load(true)"
    :paged="view==='coverage'" :start="start" :total="data?.total_count" :has-more="data?.has_more" @update:start="value=>{start=value;load()}"
    :storage-key="'lotus-stock-planning-'+view" show-empty-headers interactive :server-sort="view==='coverage'" :filter-values="view==='coverage'?data?.filter_values:undefined" :server-filters="view==='coverage'?filters:{}" :empty="empty[view]"
    @sort="model=>{sortModel=model;load(true)}" @filter="filter" @open="openRow">
   <template #filters><slot name="scope"/><DateRangePicker v-model:from="from" v-model:to="to"/><UiButton v-if="hasFilters" variant="outline" @click="resetFilters">Bỏ lọc</UiButton></template>
   <template #actions><slot name="actions"/><UiButton v-if="view==='coverage'" as="a" variant="outline" href="/lotus/materials">Lập và duyệt nhu cầu vật tư</UiButton></template>
  </ListPage>

  <ModalForm v-model="detailOpen" :title="(detail?.item_name||'')+' · '+warehouseLabel(detail?.warehouse)" :busy="saving" :error="error" readonly width="1080px">
   <DataTable :rows="detail?.sources||[]" :columns="sourceColumns"/>
   <dl class="lotus-form-totals planning-quantity-summary"><div><dt>Tồn thực tế</dt><dd>{{fmt(detail?.actual_qty)}}</dd></div><div><dt>Giữ chỗ ERP</dt><dd>{{fmt(detail?.native_reserved_qty)}}</dd></div><div><dt>Phiếu nháp của nhu cầu khác</dt><dd>{{fmt(detail?.other_hold_qty)}}</dd></div><div><dt>Phiếu nháp của nhu cầu này</dt><dd>{{fmt(detail?.own_draft_qty)}}</dd></div><div><dt>Đã đề nghị mua</dt><dd>{{fmt(detail?.requested_qty)}}</dd></div><div><dt>Chưa đề nghị</dt><dd>{{fmt(detail?.to_request_qty)}}</dd></div><div><dt>Hàng hẹn sau kỳ</dt><dd>{{fmt(detail?.later_incoming_qty)}}</dd></div></dl>
   <template #actions><UiButton v-if="data?.can_request&&detail?.to_request_qty>0" type="button" :disabled="saving" @click="buy(detail)">Lập đề nghị mua {{fmt(detail?.to_request_qty)}} {{unit(detail?.uom)}}</UiButton></template>
  </ModalForm>

  <ModalForm v-model="requestOpen" :title="'Đề nghị mua · '+(request?.name||'')" :busy="saving" :error="error" readonly width="960px">
   <DataTable :rows="request?.items||[]" :columns="purchaseItems"/>
   <div v-if="confirmAction" class="lotus-delete-confirm" role="alert"><p>{{confirmAction==='submit'?'Duyệt đề nghị mua này?':'Xóa đề nghị mua nháp này?'}}</p><div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="confirmAction=''">Quay lại</UiButton><UiButton type="button" :disabled="saving" @click="act(confirmAction)">Xác nhận</UiButton></div></div>
   <template #secondary><UiButton v-if="request?.can_delete" type="button" variant="destructive" :disabled="saving" @click="confirmAction='delete'">Xóa nháp</UiButton></template>
   <template #actions><UiButton v-if="request" as="a" variant="outline" :href="printURL('Material Request',request.name)" target="_blank" rel="noopener">In phiếu</UiButton><UiButton v-if="request?.can_submit" type="button" :disabled="saving" @click="confirmAction='submit'">Duyệt đề nghị mua</UiButton></template>
  </ModalForm>

 </div>
</template>

<script setup>
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {unitLabel} from '../units'
import {updateColumnFilter,shiftISODate} from '../stock-filter-state'
import {call} from '../api'
import DataTable from './DataTable.vue'
import ListPage from './ListPage.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import ModalForm from './form/ModalForm.vue'
import FormGrid from './form/FormGrid.vue'
import LotusField from './form/LotusField.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
import PurchaseReceiptCosts from './PurchaseReceiptCosts.vue'
import {DateRangePicker} from './ui/date-picker'
import {Button as UiButton} from './ui/button'
// Nhu cầu vật tư: approved demand vs stock, purchase requests still to order and purchase orders still to receive.
const props=defineProps({company:String,warehouse:String,today:String})
const api=(name,args={},write=false)=>call('lotus_farm.warehouse_planning.'+name,args,write)
const data=ref(null),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),from=ref(props.today||''),to=ref(shiftISODate(props.today,6)||''),search=ref(''),searchDraft=ref(''),start=ref(0),filters=ref({}),view=ref('coverage')
const detail=ref(null),detailOpen=ref(false),selectedStores=ref({}),request=ref(null),requestOpen=ref(false),confirmAction=ref('')
const order=ref(null),orderOpen=ref(false),receipt=ref(null),receiptOpen=ref(false),receiveDate=ref(props.today||''),receiveLines=ref([]),receiveKey=ref(''),receiptConfirm=ref('')
const receiveCosts=ref([]),receiveAccounts=ref([]),receiveDefaultAccount=ref('')
const receiveBaseTotal=computed(()=>receiveLines.value.reduce((sum,r)=>sum+Number(r.receive||0)*Number(r.rate||0),0))
async function loadReceiveAccounts(){try{const r=await call('lotus_farm.warehouse.receipt_accounts',{company:props.company});receiveAccounts.value=r.accounts||[];receiveDefaultAccount.value=r.default_account||''}catch{receiveAccounts.value=[];receiveDefaultAccount.value=''}}
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
const receiveColumns=[{field:'item',label:'Vật tư'},{field:'receive',label:'Thực nhận',type:'number',width:'minmax(140px,1fr)',disabled:r=>!r.remaining_qty||saving.value,props:r=>({min:0,max:r.remaining_qty}),hint:r=>unit(r.uom)}]
const storeOptions=computed(()=>(data.value?.warehouses||[]).map(store=>({value:store.name,label:store.warehouse_name})))
function show(row){detail.value=row;detailOpen.value=true}
async function openRequest(name){try{request.value=await api('purchase_request',{name});confirmAction.value='';requestOpen.value=true}catch(e){error.value=e.message}}
async function buy(row){if(saving.value)return;saving.value=true;error.value='';try{const result=await api('create_purchase_request',{company:props.company,warehouse:row.warehouse,from_date:from.value,to_date:to.value,items:[row.item]},true);notice.value=result.name?'Đã tạo đề nghị mua nháp '+result.name:result.note;detailOpen.value=false;await load();if(result.name)await openRequest(result.name)}catch(e){error.value=e.message}finally{saving.value=false}}
async function assign(source){if(saving.value)return;saving.value=true;try{await api('assign_warehouse',{company:props.company,requirement:source.name,warehouse:selectedStores.value[source.name]},true);await load()}catch(e){error.value=e.message}finally{saving.value=false}}
async function act(action){if(saving.value)return;saving.value=true;error.value='';try{await api('purchase_action',{name:request.value.name,modified:request.value.modified,action},true);requestOpen.value=false;notice.value=action==='submit'?'Đã duyệt đề nghị mua. Chưa tính là hàng chờ nhập cho tới khi có đơn mua đã duyệt.':'Đã xóa đề nghị mua nháp.';await load()}catch(e){error.value=e.message}finally{saving.value=false}}
const printURL=(doctype,name)=>'/lotus/in-phieu?'+new URLSearchParams({doctype,name})
async function openOrder(name){try{order.value=await api('purchase_order',{name});receiveLines.value=(order.value.items||[]).map(row=>({...row,receive:''}));receiveCosts.value=[];receiveKey.value=crypto.randomUUID();receiveDate.value=props.today;await loadReceiveAccounts();orderOpen.value=true}catch(e){error.value=e.message}}
async function openReceipt(name){try{receipt.value=await api('purchase_receipt',{name});receiptConfirm.value='';receiptOpen.value=true}catch(e){error.value=e.message}}
const receiving=computed(()=>Object.fromEntries(receiveLines.value.filter(r=>Number(r.receive)>0).map(r=>[r.line,Number(r.receive)])))
async function receive(){if(saving.value)return;saving.value=true;error.value='';try{const result=await api('receive_order',{name:order.value.name,posting_date:receiveDate.value,quantities:receiving.value,client_event_id:receiveKey.value,additional_costs:receiveCosts.value},true);orderOpen.value=false;await openReceipt(result.name);await load()}catch(e){error.value=e.message}finally{saving.value=false}}
async function actReceipt(action){if(saving.value)return;saving.value=true;error.value='';try{await api('receipt_action',{name:receipt.value.name,modified:receipt.value.modified,action},true);receiptOpen.value=false;notice.value=action==='submit'?'Đã ghi sổ nhận hàng. Tồn và phần chờ nhập đã cập nhật.':'Đã xóa phiếu nhận nháp.';await load()}catch(e){error.value=e.message}finally{saving.value=false}}
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

  <ModalForm v-model="orderOpen" :title="'Nhận hàng · '+(order?.name||'')+' · '+(order?.supplier||'')" :busy="saving" :error="error" width="1080px" submit-label="Lập phiếu nhận nháp" :submit-disabled="!order?.can_receive||!Object.keys(receiving).length" @submit="receive">
   <FormGrid :columns="3"><LotusField v-model="receiveDate" label="Ngày nhận" type="date" required/></FormGrid>
   <LineItemsEditor v-model="receiveLines" title="Hàng trên đơn" :columns="receiveColumns" fixed>
    <template #cell-item="{row}"><div class="planning-receive-line"><strong>{{row.item_name}}</strong><small>{{row.item}} · {{warehouseLabel(row.warehouse)}}</small><small>Đặt {{fmt(row.ordered_qty)}} · Đã nhận {{fmt(row.received_qty)}} · Phiếu nháp {{fmt(row.draft_qty)}} · Còn nhận {{fmt(row.remaining_qty)}} {{unit(row.uom)}}</small><small>Đơn giá theo đơn: {{fmt(row.rate)}} {{order?.currency||'VND'}} / {{unit(row.uom)}}</small></div></template>
   </LineItemsEditor>
   <PurchaseReceiptCosts v-model="receiveCosts" :accounts="receiveAccounts" :default-account="receiveDefaultAccount" :base-total="receiveBaseTotal" :currency="order?.currency||'VND'" :disabled="saving"/>
  </ModalForm>

  <ModalForm v-model="receiptOpen" :title="'Nhận hàng · '+(receipt?.name||'')" :busy="saving" :error="error" readonly width="1080px" :description="(receipt?.supplier||'')+' · '+(['Nháp','Đã ghi sổ','Đã hủy'][receipt?.docstatus]||'')">
   <DataTable :rows="receipt?.items||[]" :columns="purchaseItems"/>
   <dl v-if="receipt" class="lotus-form-totals"><div><dt>Tiền hàng</dt><dd>{{fmt(receipt.goods_total)}} {{receipt.currency}}</dd></div><div><dt>Chi phí vào giá vốn</dt><dd>{{fmt(receipt.valuation_charges)}} {{receipt.currency}}</dd></div><div><dt>Giá trị nhập</dt><dd>{{fmt(receipt.incoming_total)}} {{receipt.currency}}</dd></div></dl>
   <div v-if="receiptConfirm" class="lotus-delete-confirm" role="alert"><p>{{receiptConfirm==='submit'?'Ghi sổ số thực nhận này và cập nhật tồn kho?':'Xóa phiếu nhận hàng nháp này?'}}</p><div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="receiptConfirm=''">Quay lại</UiButton><UiButton type="button" :disabled="saving" @click="actReceipt(receiptConfirm)">Xác nhận</UiButton></div></div>
   <template #secondary><UiButton v-if="receipt?.can_delete" type="button" variant="destructive" :disabled="saving" @click="receiptConfirm='delete'">Xóa nháp</UiButton></template>
   <template #actions><UiButton v-if="receipt" as="a" variant="outline" :href="printURL('Purchase Receipt',receipt.name)" target="_blank" rel="noopener">In phiếu</UiButton><UiButton v-if="receipt?.can_submit" type="button" :disabled="saving" @click="receiptConfirm='submit'">Ghi sổ nhận hàng</UiButton></template>
  </ModalForm>
 </div>
</template>

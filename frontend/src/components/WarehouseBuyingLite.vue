<script setup>
import {computed,nextTick,onMounted,ref,watch} from 'vue'
import {call,upload} from '../api'
import {unitLabel,stockItemUomOptions} from '../units'
import {updateColumnFilter} from '../stock-filter-state'
import {dismissOnBackdrop} from '../dialogs'
import DataTable from './DataTable.vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import {Textarea as UiTextarea} from './ui/textarea'

const props=defineProps({company:String,warehouse:String,today:String})
const api=(name,args={},write=false)=>call('lotus_farm.warehouse_buying_lite.'+name,args,write)
const receivingAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_planning.'+name,args,write)
const setup=ref(null),rows=ref([]),total=ref(0),hasMore=ref(false),choices=ref({})
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const search=ref(''),status=ref(''),start=ref(0),sort=ref([]),filters=ref({})
const formDialog=ref(null),detailDialog=ref(null),formError=ref(''),detailError=ref('')
const draft=ref(null),current=ref(null),quote=ref(null),newSupplier=ref('')
const confirmSubmit=ref(false),confirmDelete=ref(false)
const receiveDate=ref(props.today||''),receiving=ref({}),receiveKey=ref('')
const receipt=ref(null),receiptConfirm=ref(false),cancelReceiptConfirm=ref('')
const modeOptions=['Chủ đầu tư chỉ định','Kho tự mua']
const fmtn=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const money=n=>fmtn(n)+' '+(setup.value?.currency||'VND')
const warehouses=computed(()=>setup.value?.warehouses||[])
const warehouseName=id=>warehouses.value.find(w=>w.name===id)?.warehouse_name||id||'—'
const canCreate=computed(()=>setup.value?.can_create&&!!warehouses.value.length)
const hasFilters=computed(()=>!!search.value||!!status.value||Object.keys(filters.value).length>0)
const columns=[
 {field:'name',headerName:'Số đơn',minWidth:155},
 {field:'supplier_name',headerName:'Nhà cung cấp',minWidth:165,flex:1.5},
 {field:'mode',headerName:'Cách mua',minWidth:145},
 {field:'warehouse',headerName:'Kho nhận',minWidth:160,valueFormatter:p=>p.value.split(', ').map(warehouseName).join(', ')},
 {field:'expected_date',headerName:'Ngày hẹn',minWidth:110},
 {field:'status',headerName:'Tình trạng',minWidth:130},
 {field:'lines',headerName:'Số mặt hàng',minWidth:100},
 {field:'remaining_lines',headerName:'Còn chờ',minWidth:95}
]
const itemOptions=computed(()=>setup.value?.items||[])
const uomsFor=row=>{
 const selected=String(row.item||'')
 const item=itemOptions.value.find(i=>i.name===selected)
 const units=(setup.value?.conversions||[]).filter(c=>c.parent===selected)
 return [item?.stock_uom,...units.map(x=>x.uom)].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i)
}
const itemName=code=>itemOptions.value.find(x=>x.name===code)?.item_name||code||''
const lineMoney=computed(()=>draft.value?.items?.reduce((sum,r)=>sum+Number(r.qty||0)*Number(r.rate||0),0)||0)
let req=0
let searchTimer
async function load(reset=false){
 if(reset)start.value=0
 if(!props.company)return
 const id=++req
 busy.value=true
 error.value=''
 try{
  const result=await api('orders',{company:props.company,warehouse:props.warehouse,
    search:search.value,status:status.value,start:start.value,
    sort_model:JSON.stringify(sort.value),column_filters:JSON.stringify(filters.value)})
  if(id!==req)return
  rows.value=result.rows||[];total.value=result.total_count||0
  hasMore.value=!!result.has_more;choices.value=result.filter_values||{}
 }catch(e){if(id===req)error.value=e.message}
 finally{if(id===req)busy.value=false}
}
async function initialize(){
 try{setup.value=await api('setup',{company:props.company});await load(true)}
 catch(e){error.value=e.message}
}
let initialLoad=Promise.resolve()
onMounted(()=>{initialLoad=initialize()})
watch(()=>[props.company,props.warehouse],()=>{setup.value=null;filters.value={};initialLoad=initialize()})
watch(search,value=>{
 clearTimeout(searchTimer)
 searchTimer=setTimeout(()=>load(true),220)
})
function changeFilter({field,values}){filters.value=updateColumnFilter(filters.value,field,values);load(true)}
function clearFilters(){filters.value={};search.value='';status.value='';sort.value=[];load(true)}
function newLine(){draft.value.items.push({item:'',uom:'',qty:1,rate:0,warehouse:props.warehouse||warehouses.value[0]?.name||'',expected_date:draft.value.expected_date})}
async function pickRequest(){
 if(!draft.value?.request)return
 try{
  const result=await api('request_detail',{name:draft.value.request,company:props.company})
  if(!result.items.length){formError.value='Đề nghị mua đã được đặt hết, không còn dòng cần mua.';return}
  draft.value.items=result.items.map(r=>({...r,expected_date:draft.value.expected_date}))
  draft.value.warehouse=result.items[0].warehouse
  formError.value=''
 }catch(e){formError.value=e.message}
}
function itemSelected(row){
 const item=itemOptions.value.find(r=>r.name===row.item)
 row.uom=item?.stock_uom||''
}
function emptyDraft(){
 return {request:'',supplier:'',mode:modeOptions[0],warehouse:props.warehouse||warehouses.value[0]?.name||'',expected_date:props.today||setup.value?.today||'',notes:'',items:[]}
}
async function addOrder(){
 if(!canCreate.value)return
 draft.value=emptyDraft();newLine();quote.value=null;formError.value='';newSupplier.value=''
 await nextTick();formDialog.value.showModal()
}
async function showOrder(name){
 try{
  current.value=await api('order_detail',{name});current.value.receipts=await api('order_receipts',{name});cancelReceiptConfirm.value='';detailError.value='';confirmSubmit.value=false;confirmDelete.value=false;receipt.value=null;receiving.value={};receiveKey.value=crypto.randomUUID()
  receiveDate.value=props.today||setup.value?.today||''
  await nextTick();detailDialog.value.showModal()
 }catch(e){error.value=e.message}
}
async function editOrder(){
 const source=current.value
 if(!source?.can_write)return
 draft.value={name:source.name,modified:source.modified,supplier:source.supplier,mode:source.mode,
  warehouse:source.items[0]?.warehouse||props.warehouse||'',expected_date:source.expected_date,
  notes:source.notes,items:source.items.map(r=>({item:r.item,uom:r.uom,qty:r.qty,rate:r.rate,warehouse:r.warehouse,expected_date:r.expected_date,material_request:r.material_request,material_request_item:r.material_request_item}))}
 quote.value=null;formError.value='';detailDialog.value.close()
 await nextTick();formDialog.value.showModal()
}
async function createSupplier(){
 const name=newSupplier.value.trim()
 if(!name)return
 saving.value=true;formError.value=''
 try{
  const created=await api('create_supplier',{company:props.company,name},true)
  setup.value.suppliers.push(created)
  draft.value.supplier=created.name
  newSupplier.value=''
 }catch(e){formError.value=e.message}
 finally{saving.value=false}
}
async function saveOrder(){
 if(saving.value)return
 saving.value=true;formError.value=''
 try{
  const data={...draft.value,items:draft.value.items.map(r=>({...r,warehouse:draft.value.warehouse}))}
  const result=await api('save_order',{company:props.company,data,
    name:draft.value.name||null,modified:draft.value.modified||null},true)
  draft.value.name=result.name;draft.value.modified=result.modified
  if(quote.value){
   if(quote.value.size>10*1024*1024)throw new Error('Báo giá không được quá 10MB.')
   await upload(quote.value,'Purchase Order',result.name)
  }
  formDialog.value.close();quote.value=null
  notice.value='Đã lưu đơn mua '+result.name+' (nháp).'
  await load()
  await showOrder(result.name)
 }catch(e){formError.value=(draft.value.name?'Đơn có thể đã được lưu. ':'')+e.message}
 finally{saving.value=false}
}
async function submitOrder(){
 if(!confirmSubmit.value||saving.value)return
 saving.value=true;detailError.value=''
 try{
  await api('submit_order',{name:current.value.name,modified:current.value.modified},true)
  detailDialog.value.close();notice.value='Đã xác nhận đặt hàng. Đơn được theo dõi ở Hàng chờ về.'
  await load();await showOrder(current.value.name)
 }catch(e){detailError.value=e.message}
 finally{saving.value=false}
}
async function deleteDraft(){
 if(!confirmDelete.value||saving.value)return
 saving.value=true;detailError.value=''
 try{
  await api('delete_draft',{name:current.value.name,modified:current.value.modified},true)
  detailDialog.value.close();notice.value='Đã xóa đơn mua nháp.';await load()
 }catch(e){detailError.value=e.message}
 finally{saving.value=false}
}
const chosenReceipts=computed(()=>Object.fromEntries(Object.entries(receiving.value)
 .filter(([,qty])=>Number(qty)>0)
 .map(([line,qty])=>{
  const item=current.value?.items?.find(r=>r.line===line)
  return [line,Number(qty)*(Number(item?.conversion_factor)||1)]
 })))
async function makeReceipt(){
 if(saving.value||!Object.keys(chosenReceipts.value).length)return
 saving.value=true;detailError.value=''
 try{
  const result=await receivingAPI('receive_order',{name:current.value.name,
    posting_date:receiveDate.value,quantities:chosenReceipts.value,client_event_id:receiveKey.value},true)
  receipt.value=await receivingAPI('purchase_receipt',{name:result.name})
  notice.value='Đã tạo phiếu nhận nháp '+result.name+'. Chỉ tăng tồn khi ghi sổ.'
 }catch(e){detailError.value=e.message}
 finally{saving.value=false}
}
async function cancelReceipt(row){
 if(saving.value||cancelReceiptConfirm.value!==row.name)return
 saving.value=true;detailError.value=''
 try{
  await receivingAPI('receipt_action',{name:row.name,modified:row.modified,action:'cancel'},true)
  const name=current.value.name
  detailDialog.value.close()
  cancelReceiptConfirm.value=''
  notice.value='Đã hủy phiếu nhận; ERPNext hoàn lại tồn và cập nhật số chờ nhận.'
  await load();await showOrder(name)
 }catch(e){detailError.value=e.message}
 finally{saving.value=false}
}
async function postReceipt(){
 if(!receiptConfirm.value||saving.value||!receipt.value)return
 saving.value=true;detailError.value=''
 try{
  await receivingAPI('receipt_action',{name:receipt.value.name,modified:receipt.value.modified,action:'submit'},true)
  const name=current.value.name
  detailDialog.value.close();notice.value='Đã ghi sổ nhận hàng, tồn kho và số còn chờ đã cập nhật.'
  receipt.value=null;receiptConfirm.value=false
  await load();await showOrder(name)
 }catch(e){detailError.value=e.message}
 finally{saving.value=false}
}
function startReceiving(){status.value='pending';search.value='';filters.value={};load(true)}
defineExpose({refresh:()=>load(true),startReceiving,createOrder:async()=>{await initialLoad;await addOrder()}})
</script>

<template>
 <section class="warehouse-buying">
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
  <div class="stock-buying-toolbar">
   <div class="stock-buying-tabs">
    <UiButton variant="outline" :class="{active:!status}" @click="status='';load(true)">Tất cả đơn mua</UiButton>
    <UiButton variant="outline" :class="{active:status==='pending'}" @click="status='pending';load(true)">Hàng chờ về</UiButton>
   </div>
   <UiButton v-if="hasFilters" variant="outline" @click="clearFilters">Bỏ lọc</UiButton>
   <UiInput v-model="search" class="stock-buying-search" placeholder="Tìm đơn, NCC…" aria-label="Tìm đơn mua, nhà cung cấp"/>
   <UiButton variant="outline" @click="startReceiving">↓ Nhập theo đơn</UiButton>
   <UiButton :disabled="!canCreate||busy" @click="addOrder">+ Tạo đơn mua</UiButton>
  </div>
  <section class="stock-panel">
   <DataTable :rows="rows" :columns="columns" show-empty-headers server-sort
     @sort="model=>{sort=model;load(true)}" :filter-values="choices"
     :server-filters="filters" @filter="changeFilter" :loading="busy"
     interactive @open="row=>showOrder(row.name)"
     empty="Chưa có đơn mua phù hợp. Bấm Tạo đơn mua để bắt đầu."/>
   <footer class="stock-pagination">
    <span>{{total?start+1:0}}–{{start+rows.length}} / {{total}} đơn</span>
    <div><UiButton variant="outline" :disabled="!start||busy" @click="start-=50;load()">← Trước</UiButton><UiButton variant="outline" :disabled="!hasMore||busy" @click="start+=50;load()">Sau →</UiButton></div>
   </footer>
  </section>
  <dialog ref="formDialog" class="stock-dialog stock-buying-dialog" @click="dismissOnBackdrop($event,saving)">
   <form v-if="draft" @submit.prevent="saveOrder">
    <header><h2>{{draft.name?'Sửa đơn mua '+draft.name:'Tạo đơn mua'}}</h2><UiButton type="button" variant="outline" @click="formDialog.close()">Đóng</UiButton></header>
    <p v-if="formError" class="stock-error" role="alert">{{formError}}</p>
    <p class="stock-form-help">Chọn NCC, vật tư và ngày hẹn. Báo giá có thể tải lên sau khi tạo đơn; chưa chốt giá vẫn lưu nháp được.</p>
    <div class="stock-form-grid">
     <label v-if="setup?.requests?.length">Từ đề nghị mua (không bắt buộc)<UiSelect v-model="draft.request" @change="pickRequest"><option value="">Tạo mới không theo đề nghị</option><option v-for="r in setup.requests" :key="r.name" :value="r.name">{{r.name}}</option></UiSelect></label>
     <label>Nhà cung cấp <UiSelect v-model="draft.supplier" required><option value="">Chọn NCC</option><option v-for="s in setup?.suppliers||[]" :key="s.name" :value="s.name">{{s.supplier_name}}</option></UiSelect></label>
     <label>Cách mua <UiSelect v-model="draft.mode"><option v-for="mode in modeOptions" :key="mode" :value="mode">{{mode}}</option></UiSelect></label>
     <label>Kho nhận <UiSelect v-model="draft.warehouse" required><option v-for="w in warehouses" :key="w.name" :value="w.name">{{w.warehouse_name}}</option></UiSelect></label>
     <label>Ngày giao dự kiến <UiInput v-model="draft.expected_date" type="date" required/></label>
     <label>Báo giá (PDF/ảnh, tối đa 10MB) <input type="file" accept=".pdf,image/png,image/jpeg,image/webp" @change="quote=$event.target.files?.[0]||null"/></label>
    </div>
    <div v-if="setup?.can_create_supplier" class="stock-buying-supplier">
     <UiInput v-model="newSupplier" placeholder="Tên NCC mới"/>
     <UiButton type="button" variant="outline" :disabled="!newSupplier.trim()||saving" @click="createSupplier">+ Tạo NCC nhanh</UiButton>
    </div>
    <label>Ghi chú giao hàng <UiTextarea v-model="draft.notes" rows="2" placeholder="Địa chỉ giao, người liên hệ, yêu cầu khác…"/></label>
    <div class="stock-form-section-title"><h3>Hàng cần mua</h3><span>{{draft.items.length}} mặt hàng</span></div>
    <div v-for="(row,i) in draft.items" :key="i" class="stock-buying-line">
     <label>Vật tư <UiSelect v-model="row.item" required @change="itemSelected(row)"><option value="">Chọn vật tư</option><option v-for="item in itemOptions" :key="item.name" :value="item.name">{{item.item_name}}</option></UiSelect></label>
     <label>ĐVT <UiSelect v-model="row.uom" required><option v-for="u in uomsFor(row)" :key="u" :value="u">{{unitLabel(u)}}</option></UiSelect></label>
     <label>Số lượng <UiInput v-model.number="row.qty" type="number" min="0.000001" step="any" required/></label>
     <label>Đơn giá (nếu có) <UiInput v-model.number="row.rate" type="number" min="0" step="any"/></label>
     <UiButton type="button" variant="outline" @click="draft.items.splice(i,1)" :disabled="draft.items.length===1">Xóa</UiButton>
    </div>
    <div class="stock-buying-total"><UiButton type="button" variant="outline" @click="newLine">+ Thêm dòng</UiButton><span>Tạm tính: <strong>{{money(lineMoney)}}</strong></span></div>
    <footer><UiButton type="button" variant="outline" @click="formDialog.close()">Hủy</UiButton><UiButton type="submit" :disabled="saving||!draft.supplier||!draft.items.length">{{saving?'Đang lưu…':'Lưu đơn mua nháp'}}</UiButton></footer>
   </form>
  </dialog>
  <dialog ref="detailDialog" class="stock-dialog stock-buying-dialog" @click="dismissOnBackdrop($event,saving)">
   <section v-if="current" class="stock-buying-detail">
    <header><h2>Đơn mua {{current.name}}</h2><UiButton variant="outline" @click="detailDialog.close()">Đóng</UiButton></header>
    <p v-if="detailError" class="stock-error" role="alert">{{detailError}}</p>
    <div class="stock-buying-fields"><span><strong>NCC</strong>{{current.supplier_name}}</span><span><strong>Cách mua</strong>{{current.mode}}</span><span><strong>Kho</strong>{{warehouseName(current.items[0]?.warehouse)}}</span><span><strong>Hẹn giao</strong>{{current.expected_date}}</span><span><strong>Tình trạng</strong>{{current.status}}</span></div>
    <table class="stock-buying-detail-table"><thead><tr><th>Tên hàng</th><th>Đặt</th><th>Đã nhận</th><th>Còn chờ</th><th>ĐVT</th></tr></thead><tbody><tr v-for="r in current.items" :key="r.line"><td>{{r.item_name}}</td><td>{{fmtn(r.qty)}}</td><td>{{fmtn(r.received_qty)}}</td><td>{{fmtn(r.remaining_qty)}}</td><td>{{unitLabel(r.uom)}}</td></tr></tbody></table>
    <section class="stock-buying-quotes"><h3>Báo giá đính kèm</h3><p v-if="!current.quote_files.length">Chưa có báo giá.</p><p v-for="q in current.quote_files" :key="q.name"><a v-if="q.file_url?.startsWith('/')" :href="q.file_url" target="_blank" rel="noopener noreferrer">{{q.file_name}} ↗</a></p></section>
    <p v-if="current.notes">Ghi chú: {{current.notes}}</p>
    <section v-if="current.receipts?.length" class="stock-buying-receipts">
      <h3>Phiếu nhận theo đơn</h3>
      <div v-for="r in current.receipts" :key="r.name" class="stock-buying-receipt-line">
        <span><strong>{{r.name}}</strong> · {{r.date}} · {{r.status}}</span>
        <label v-if="r.can_cancel"><input type="checkbox" :checked="cancelReceiptConfirm===r.name" @change="cancelReceiptConfirm=$event.target.checked?r.name:''"/> Xác nhận hủy</label>
        <UiButton v-if="r.can_cancel" variant="outline" :disabled="saving||cancelReceiptConfirm!==r.name" @click="cancelReceipt(r)">Hủy phiếu</UiButton>
      </div>
    </section>
    <div v-if="current.can_receive&&current.remaining_lines>0" class="stock-buying-receive">
     <h3>Nhận hàng</h3><label>Ngày nhận <UiInput type="date" v-model="receiveDate"/></label>
     <div v-for="r in current.items.filter(x=>x.remaining_qty>0)" :key="r.line" class="stock-buying-receive-row">
      <span>{{r.item_name}} — còn {{fmtn(r.remaining_qty)}} {{unitLabel(r.uom)}}</span>
      <UiInput :model-value="receiving[r.line]||''" @update:model-value="v=>receiving[r.line]=v" type="number" min="0" :max="r.remaining_qty" step="any" :placeholder="'Nhận ('+unitLabel(r.uom)+')'"/>
     </div>
     <UiButton v-if="!receipt" variant="outline" :disabled="saving||!Object.keys(chosenReceipts).length" @click="makeReceipt">Tạo phiếu nhận nháp</UiButton>
     <div v-if="receipt" class="stock-buying-receipt"><strong>Phiếu {{receipt.name}} (chưa ghi sổ)</strong><label><input v-model="receiptConfirm" type="checkbox"/> Xác nhận số thực nhận đúng</label><UiButton :disabled="saving||!receiptConfirm" @click="postReceipt">Ghi sổ nhận hàng</UiButton></div>
    </div>
    <footer>
     <UiButton v-if="current.can_write" variant="outline" @click="editOrder">Sửa nháp</UiButton>
     <label v-if="current.can_submit"><input v-model="confirmSubmit" type="checkbox"/> Đã kiểm tra NCC, hàng và giá</label>
     <UiButton v-if="current.can_submit" :disabled="saving||!confirmSubmit" @click="submitOrder">Xác nhận đặt hàng</UiButton>
     <label v-if="current.can_write"><input v-model="confirmDelete" type="checkbox"/> Xóa nháp</label>
     <UiButton v-if="current.can_write&&confirmDelete" variant="outline" :disabled="saving" @click="deleteDraft">Xóa đơn nháp</UiButton>
    </footer>
   </section>
  </dialog>
 </section>
</template>

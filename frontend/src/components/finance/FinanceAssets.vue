<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import DataTable from '../DataTable.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import MonthPicker from '../MonthPicker.vue'
import {Button} from '../ui/button'
import {Input} from '../ui/input'
import {FormField} from '../ui/form-field'
import {DatePicker} from '../ui/date-picker'
import {Combobox} from '../ui/combobox'
import Select from '../ui/select/Select.vue'
import {call} from '../../api'

const emit=defineEmits(['notice'])
const API='lotus_farm.finance.assets.'
const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Ho_Chi_Minh'})
const month=ref(today.slice(0,7)),section=ref('assets'),search=ref(''),data=ref(null),lookups=ref({}),error=ref(''),busy=ref(false),saving=ref(false)
const editor=ref(''),form=ref({}),errors=ref({}),selected=ref(null),review=ref(null),schedule=ref(null),report=ref(null),allocation=ref([]),purchaseRows=ref([])
const reportFarm=ref(''),importContent=ref(''),importPreview=ref(null),reason=ref(''),cancelTarget=ref(null)
const kinds=[['Move','Điều chuyển / bàn giao'],['Repair','Sửa chữa'],['Upgrade','Nâng cấp / vốn hóa'],['Suspend','Tạm ngừng sử dụng'],['Resume','Sử dụng lại'],['Sell','Bán tài sản'],['Scrap','Thanh lý / loại bỏ'],['Restore','Phục hồi thanh lý']]
const kindLabel=v=>v==='Create'?'Ghi tăng tài sản':v==='Profile'?'Cập nhật hồ sơ':kinds.find(k=>k[0]===v)?.[1]||v
const stateLabel=v=>({Pending:'Chờ duyệt',Posted:'Đã duyệt',Cancelled:'Đã hủy',Submitted:'Đang sử dụng',Draft:'Nháp',Sold:'Đã bán',Scrapped:'Đã thanh lý','Partially Depreciated':'Đang khấu hao','Fully Depreciated':'Đã khấu hao hết'})[v]||v
const fmt=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const documentUrl=d=>'/desk/'+d.doctype.toLowerCase().replaceAll(' ','-')+'/'+encodeURIComponent(d.name)
const date=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):'—'
const canWrite=computed(()=>!!data.value?.permissions?.write),canApprove=computed(()=>!!data.value?.permissions?.approve)
const assets=computed(()=>(data.value?.assets||[]).filter(a=>!search.value||(a.asset_name+' '+a.lotus_asset_code+' '+(a.lotus_serial_no||'')).toLowerCase().includes(search.value.toLowerCase())))
const options=(key,label='name',filter=()=>true)=>(lookups.value[key]||[]).filter(filter).map(r=>({value:r.name,label:r[label]||r.name,subtitle:r.name}))
const accounts=kind=>(lookups.value.accounts||[]).filter(r=>!kind||r.root_type===kind).map(r=>({value:r.name,label:(r.account_number||'')+' · '+r.account_name}))
const column=(field,headerName,extra={})=>({field,headerName,minWidth:130,flex:1,...(['posting_date','schedule_date'].includes(field)?{valueFormatter:p=>date(p.value)}:{}),...(['total_asset_cost','value_after_depreciation','depreciation_amount','accumulated_depreciation_amount','amount','depreciation','accumulated','remaining'].includes(field)?{valueFormatter:p=>fmt(p.value)+' đ'}:{}),...(field==='actions'?{pinned:'right'}:{}),...extra})
const assetColumns=[column('lotus_asset_code','Mã tài sản'),column('asset_name','Tài sản',{minWidth:200}),column('asset_category','Nhóm'),column('location','Vị trí'),column('total_asset_cost','Nguyên giá'),column('value_after_depreciation','Giá trị còn lại'),column('status','Trạng thái'),column('actions','Thao tác',{minWidth:240,sortable:false})]
const opColumns=[column('posting_date','Ngày'),column('kind','Nghiệp vụ'),column('asset','Tài sản'),column('state','Trạng thái'),column('approved_by','Người duyệt'),column('actions','Thao tác',{minWidth:200,sortable:false})]
const runColumns=[column('month','Tháng'),column('state','Trạng thái'),column('approved_by','Người duyệt'),column('actions','Thao tác',{sortable:false})]
const depreciationColumns=[column('asset_name','Tài sản',{minWidth:200}),column('schedule_date','Ngày trích'),column('amount','Khấu hao'),column('allocation_summary','Phân bổ',{minWidth:300,valueGetter:p=>(p.data.allocations||[]).map(r=>(r.lotus_farm_block||r.lotus_farm||r.expense_account)+': '+r.percent+'% · '+fmt(r.amount)+' đ').join('; ')})]
const allocationColumns=[column('percent','Tỷ lệ %'),column('expense_account','Tài khoản',{minWidth:200}),column('cost_center','Trung tâm chi phí',{minWidth:200}),column('lotus_farm','Vườn',{minWidth:180}),column('lotus_farm_block','Lô',{minWidth:180}),column('lotus_crop_cycle','Vụ',{minWidth:180}),column('lotus_work_type','Công việc',{minWidth:180}),column('remove','',{minWidth:70,sortable:false})]
const scheduleColumns=[column('schedule_date','Ngày trích'),column('depreciation_amount','Khấu hao'),column('accumulated_depreciation_amount','Lũy kế'),column('journal_entry','Bút toán')]
const reportColumns=[...assetColumns.slice(0,4),column('total_asset_cost','Nguyên giá'),column('depreciation','Khấu hao đã ghi'),column('accumulated','Hao mòn lũy kế'),column('remaining','Giá trị còn lại')]
let allocationRowKey=0
const allocationRow=(row={percent:0})=>({...row,row_key:'allocation-'+(++allocationRowKey)})
const importColumns=[column('line','Dòng'),column('code','Mã',{valueGetter:p=>p.data.values.code}),column('asset_name','Tài sản',{valueGetter:p=>p.data.values.asset_name}),column('errors','Lỗi',{minWidth:300,valueGetter:p=>Object.values(p.data.errors||{}).join('; ')})]

async function task(fn){busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message||String(e)}finally{busy.value=false}}
async function load(){return task(async()=>{[data.value,lookups.value]=await Promise.all([call(API+'overview',{month:month.value}),call(API+'lookups')]);if(section.value==='report')await loadReport()})}
async function mutate(fn,notice){saving.value=true;errors.value={};error.value='';try{const result=await fn();if(result?.errors&&Object.keys(result.errors).length){errors.value=result.errors;return}emit('notice',notice);editor.value='';await load();return result}catch(e){error.value=e.message||String(e)}finally{saving.value=false}}
async function activate(){await mutate(()=>call(API+'activate',{on:1},true),'Đã bật quản lý tài sản; khấu hao chờ kế toán trưởng duyệt.')}
async function showAsset(row){await task(async()=>{selected.value=row;schedule.value=await call(API+'detail',{asset:row.name});editor.value='detail'})}
async function openAsset(row){errors.value={};selected.value=row||null;purchaseRows.value=[]
 if(row){const detail=await task(()=>call(API+'detail',{asset:row.name}));if(!detail)return;const a=detail.asset,b=a.finance_books?.[0]||{}
  form.value={name:a.name,code:a.lotus_asset_code,asset_name:a.asset_name,serial_no:a.lotus_serial_no,asset_category:a.asset_category,location:a.location,custodian:a.custodian,department:a.department,
   purchase_date:a.purchase_date,available_for_use_date:a.available_for_use_date,amount:a.net_purchase_amount,opening_depreciation:a.opening_accumulated_depreciation,
   months:b.total_number_of_depreciations||12,booked_months:a.opening_number_of_booked_depreciations||0,salvage_value:b.expected_value_after_useful_life||0,method:b.depreciation_method||'Straight Line',
   existing:(a.asset_type==='Existing Asset'||!!a.is_existing_asset)?'1':'0',purchase_invoice:a.purchase_invoice,purchase_receipt:a.purchase_receipt,item_code:a.item_code,purchase_row:a.purchase_invoice_item||a.purchase_receipt_item,
   posting_date:today,...Object.fromEntries(['lotus_farm','lotus_farm_block','lotus_crop_cycle','lotus_work_type'].map(k=>[k,a[k]||'']))}
 }else form.value={existing:'1',code:'',asset_name:'',purchase_date:'',available_for_use_date:'',amount:'',opening_depreciation:0,months:'',booked_months:0,salvage_value:0,method:'Straight Line',posting_date:today,vat_code:'KCT'}
 editor.value='asset'
}
async function saveAsset(){await mutate(()=>call(API+'save_asset',{values:JSON.stringify({...form.value,existing:Number(form.value.existing)===1})},true),'Đã lưu hồ sơ chờ kế toán trưởng duyệt.')}
async function loadPurchase(value){if(!value){purchaseRows.value=[];return}await task(async()=>{const r=await call(API+'purchase_details',{name:value});purchaseRows.value=r.items})}
function choosePurchaseRow(value){const r=purchaseRows.value.find(r=>r.name===value);if(r)Object.assign(form.value,{purchase_row:r.name,item_code:r.item_code,asset_category:r.asset_category,amount:r.base_net_amount})}
function openOperation(row){selected.value=row;form.value={kind:row.status==='Scrapped'?'Restore':'Move',posting_date:today,location:row.location,custodian:row.custodian,amount:'',vat_code:'KCT',reason:'',increase_months:0,...Object.fromEntries(['lotus_farm','lotus_farm_block','lotus_crop_cycle','lotus_work_type'].map(k=>[k,row[k]||'']))};errors.value={};editor.value='operation'}
async function saveOperation(){const {kind,posting_date,reason,...values}=form.value;await mutate(()=>call(API+'save_operation',{kind,posting_date,reason,asset:selected.value.name,values:JSON.stringify(values)},true),'Đã lập nghiệp vụ chờ duyệt.')}
async function reviewOperation(row){await task(async()=>{review.value={type:'operation',...(await call(API+'operation_preview',{name:row.name}))};editor.value='review'})}
async function reviewDepreciation(){await task(async()=>{review.value={type:'depreciation',...(await call(API+'depreciation_preview',{month:month.value}))};editor.value='review'})}
async function prepare(){const r=review.value;await mutate(()=>call(API+'depreciation_prepare',{month:r.month,fingerprint:r.fingerprint},true),'Đã lưu bảng khấu hao chờ kế toán trưởng duyệt.')}
async function reviewRun(row){if(row.state==='Pending'){month.value=row.month;await reviewDepreciation()}else await task(async()=>{review.value={type:'depreciation',...(await call(API+'depreciation_detail',{name:row.name}))};editor.value='review'})}
async function approve(){const r=review.value;if(r.type==='operation')await mutate(()=>call(API+'operation_post',{name:r.name,fingerprint:r.fingerprint},true),'Đã duyệt nghiệp vụ tài sản.')
 else await mutate(()=>call(API+'depreciation_post',{month:r.month,fingerprint:r.fingerprint},true),'Đã ghi khấu hao và phân bổ chi phí.')}
function requestCancel(type,row){cancelTarget.value={type,row};reason.value='';editor.value='reason'}
async function cancel(){const {type,row}=cancelTarget.value;await mutate(()=>call(API+(type==='operation'?'operation_cancel':'depreciation_reverse'),{name:row.name,reason:reason.value},true),'Đã hủy/đảo nghiệp vụ; giữ nguyên lịch sử.')}
async function openAllocation(row){await task(async()=>{selected.value=row;const r=await call(API+'allocation',{asset:row.name,month:month.value});form.value={modified:r.modified,inherited_from:r.inherited_from};allocation.value=r.rows.map(allocationRow);editor.value='allocation'})}
const allocationTotal=computed(()=>allocation.value.reduce((s,r)=>s+Number(r.percent||0),0))
async function saveAllocation(){await mutate(()=>call(API+'save_allocation',{asset:selected.value.name,month:month.value,rows:JSON.stringify(allocation.value),modified:form.value.modified},true),'Đã lưu tỷ lệ phân bổ tháng.')}
function openCategory(){form.value={asset_category_name:'',non_depreciable_category:'0'};editor.value='category'}
async function saveCategory(){await mutate(()=>call(API+'save_category',{values:JSON.stringify(form.value)},true),'Đã lưu nhóm tài sản.')}
async function saveLocation(){await mutate(()=>call(API+'save_location',{location_name:form.value.location_name},true),'Đã lưu vị trí tài sản.')}
async function loadReport(){report.value=await call(API+'report',{farm:reportFarm.value||undefined,on_date:month.value+'-'+new Date(Number(month.value.slice(0,4)),Number(month.value.slice(5,7)),0).getDate()})}
function download(method){window.location.href='/api/method/'+API+method+(method==='export'?'?on_date='+encodeURIComponent(month.value+'-'+new Date(Number(month.value.slice(0,4)),Number(month.value.slice(5,7)),0).getDate())+(reportFarm.value?'&farm='+encodeURIComponent(reportFarm.value):''):'')}
async function readFile(event){const file=event.target.files?.[0];importPreview.value=null;importContent.value='';if(!file)return;if(file.size>5_000_000){error.value='File vượt quá 5 MB.';return}const reader=new FileReader();reader.onload=()=>{importContent.value=String(reader.result)};reader.readAsDataURL(file)}
async function previewImport(){await task(async()=>{importPreview.value=await call(API+'import_preview',{content:importContent.value},true)})}
async function commitImport(){await mutate(()=>call(API+'import_commit',{content:importContent.value,fingerprint:importPreview.value.fingerprint},true),'Đã tạo hồ sơ tài sản chờ duyệt; chưa ghi số dư đầu kỳ.')}
watch(month,()=>{review.value=null;load()})
watch(reportFarm,()=>{if(section.value==='report')task(loadReport)})
watch(section,async value=>{error.value='';if(value==='report')await task(loadReport)})
onMounted(load)
defineExpose({load})
</script>

<template>
<section class="fin-assets" aria-label="Tài sản cố định">
 <div class="fin-assets__toolbar">
  <Select v-model="section" aria-label="Mục tài sản"><option value="assets">Danh mục tài sản</option><option value="depreciation">Khấu hao tháng</option><option value="operations">Biến động tài sản</option><option value="report">Báo cáo tài sản</option></Select>
  <MonthPicker v-model="month" label="Tháng tài sản"/>
  <Button variant="outline" :disabled="busy||saving" @click="load">Làm mới</Button>
  <Input v-if="section==='assets'" v-model="search" type="search" placeholder="Tìm mã, tên, serial…" aria-label="Tìm tài sản"/>
  <template v-if="data?.enabled&&canWrite">
   <Button v-if="section==='assets'" :disabled="saving" @click="openAsset()">Thêm tài sản</Button>
   <Button v-if="section==='assets'" variant="outline" @click="editor='import';importPreview=null;importContent=''">Nhập Excel</Button>
   <Button v-if="section==='assets'&&canApprove" variant="outline" @click="openCategory">Nhóm tài sản</Button>
   <Button v-if="section==='assets'" variant="outline" @click="form={location_name:''};editor='location'">Thêm vị trí</Button>
   <Button v-if="section==='depreciation'" :disabled="busy" @click="reviewDepreciation">Lập bảng khấu hao</Button>
  </template>
  <Combobox v-if="section==='report'" v-model="reportFarm" :options="options('farms','farm_name')" label="Vườn báo cáo tài sản" placeholder="Tất cả vườn"/>
  <Button v-if="section==='report'" variant="outline" @click="download('export')">Xuất Excel</Button>
 </div>
 <p v-if="busy" role="status">Đang tải tài sản…</p>
 <p v-if="error" class="hr-ops-error" role="alert">{{error}}</p>
 <div v-if="data&&!data.enabled" class="fin-assets__activation">
  <p>Quản lý tài sản chưa bật. Khi bật, khấu hao chuyển sang xem trước và kế toán trưởng duyệt; hệ thống không tự tạo tài sản hay ghi số dư.</p>
  <Button v-if="canApprove" :disabled="saving" @click="activate">Bật quản lý tài sản</Button>
 </div>
 <DataTable v-if="section==='assets'&&data?.enabled" :rows="assets" :columns="assetColumns" row-key="name" storage-key="fin-assets-register" empty="Chưa có tài sản. Thêm hồ sơ hoặc nhập danh sách đầu kỳ.">
  <template #cell-total_asset_cost="{row}">{{fmt(row.total_asset_cost||row.net_purchase_amount)}} đ</template>
  <template #cell-value_after_depreciation="{row}">{{fmt(row.value_after_depreciation)}} đ</template>
  <template #cell-status="{row}">{{row.lotus_usage_suspended?'Tạm ngừng sử dụng · vẫn khấu hao':stateLabel(row.status)}}</template>
  <template #cell-actions="{row}"><div class="fin-assets__actions"><Button size="sm" variant="outline" @click="showAsset(row)">Chi tiết</Button><template v-if="canWrite"><Button size="sm" variant="ghost" @click="openAsset(row)">Sửa hồ sơ</Button><Button size="sm" variant="ghost" @click="openAllocation(row)">Phân bổ</Button><Button size="sm" variant="ghost" @click="openOperation(row)">Nghiệp vụ</Button></template></div></template>
 </DataTable>
 <template v-if="section==='depreciation'&&data?.enabled"><DataTable :rows="data.runs" :columns="runColumns" row-key="name" storage-key="fin-assets-runs" empty="Chưa có bảng khấu hao được duyệt.">
  <template #cell-state="{row}">{{stateLabel(row.state)}}</template><template #cell-actions="{row}"><Button size="sm" variant="outline" @click="reviewRun(row)">{{row.state==='Pending'?'Xem trước':'Chi tiết'}}</Button><Button v-if="canApprove&&row.state==='Posted'" size="sm" variant="outline" @click="requestCancel('run',row)">Đảo bảng</Button></template>
 </DataTable></template>
 <DataTable v-if="section==='operations'&&data?.enabled" :rows="data.operations" :columns="opColumns" row-key="name" storage-key="fin-assets-operations" empty="Chưa có nghiệp vụ tài sản.">
  <template #cell-posting_date="{row}">{{date(row.posting_date)}}</template><template #cell-kind="{row}">{{kindLabel(row.kind)}}</template><template #cell-state="{row}">{{stateLabel(row.state)}}</template>
  <template #cell-actions="{row}"><div class="fin-assets__actions"><Button size="sm" variant="outline" @click="reviewOperation(row)">{{row.state==='Pending'?'Xem trước':'Chi tiết'}}</Button><Button v-if="row.state!=='Cancelled'&&(row.state==='Pending'?canWrite:canApprove)" size="sm" variant="ghost" @click="requestCancel('operation',row)">Hủy</Button></div></template>
 </DataTable>
 <template v-if="section==='report'&&report"><p>Nguyên giá: {{fmt(report.totals.original)}} đ · Hao mòn: {{fmt(report.totals.accumulated)}} đ · Còn lại: {{fmt(report.totals.remaining)}} đ</p><DataTable :rows="report.rows" :columns="reportColumns" row-key="name" storage-key="fin-assets-report" empty="Chưa có tài sản trong kỳ."/></template>

 <WorkspaceModal :model-value="editor==='asset'" :title="form.name?'Cập nhật hồ sơ tài sản':'Lập hồ sơ tài sản'" width="860px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <form class="fin-assets__form" @submit.prevent="saveAsset"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p>
   <FormField label="Nguồn tài sản"><Select v-model="form.existing" :disabled="!!form.name" aria-label="Nguồn tài sản"><option value="1">Tài sản đầu kỳ</option><option value="0">Mua mới</option></Select></FormField>
   <FormField v-for="[key,label] in [['code','Mã tài sản'],['asset_name','Tên tài sản'],['serial_no','Serial']]" :key="key" :label="label" :error="errors[key]" :required="key!=='serial_no'" v-slot="field"><Input v-bind="field" v-model="form[key]"/></FormField>
   <FormField label="Nhóm tài sản" required :error="errors.asset_category"><Combobox v-model="form.asset_category" :options="options('categories','asset_category_name')" label="Nhóm tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Vị trí" required :error="errors.location"><Combobox v-model="form.location" :options="options('locations','location_name')" label="Vị trí tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Người quản lý"><Combobox v-model="form.custodian" :options="options('employees','employee_name')" label="Người quản lý tài sản" :disabled="!!form.name"/></FormField>
   <FormField v-for="[key,label] in [['posting_date','Ngày nghiệp vụ'],['purchase_date','Ngày mua'],['available_for_use_date','Ngày đưa vào sử dụng']]" :key="key" :label="label" required :error="errors[key]"><DatePicker v-model="form[key]" :label="label" :disabled="!!form.name&&key!=='posting_date'"/></FormField>
   <template v-if="Number(form.existing)===0&&!form.name">
    <FormField label="Hóa đơn mua đã duyệt"><Combobox v-model="form.purchase_invoice" :options="options('purchases')" label="Hóa đơn mua tài sản" @change="loadPurchase"/></FormField>
    <FormField v-if="form.purchase_invoice" label="Dòng tài sản trong hóa đơn"><Combobox v-model="form.purchase_row" :options="purchaseRows.map(r=>({value:r.name,label:r.item_name+' · '+fmt(r.base_net_amount)+' đ'}))" label="Dòng mua tài sản" @change="choosePurchaseRow"/></FormField>
    <FormField v-else label="Nhà cung cấp" required :error="errors.supplier"><Combobox v-model="form.supplier" :options="options('suppliers','supplier_name')" label="Nhà cung cấp tài sản"/></FormField>
   </template>
   <template v-if="Number(form.existing)===0&&!form.name&&!form.purchase_invoice">
    <FormField label="Thuế GTGT đầu vào"><Select v-model="form.vat_code" aria-label="Thuế suất mua tài sản"><option value="KCT">Không chịu thuế</option><option v-for="n in ['0','5','8','10']" :key="n" :value="n">{{n}}%</option></Select></FormField>
    <FormField v-if="form.vat_code!=='KCT'" label="Tài khoản thuế được khấu trừ"><Combobox v-model="form.input_vat_account" :options="accounts('Asset')" label="Thuế đầu vào tài sản"/></FormField>
    <FormField label="Số hóa đơn mua"><Input v-model="form.bill_no"/></FormField>
   </template>
   <FormField v-for="[key,label] in [['amount','Nguyên giá (đ)'],['months','Tổng số tháng khấu hao'],['salvage_value','Giá trị thu hồi (đ)']]" :key="key" :label="label" required :error="errors[key]" v-slot="field"><Input v-bind="field" v-model="form[key]" type="number" min="0" :disabled="key==='amount'&&!!form.name"/></FormField>
   <template v-if="Number(form.existing)===1"><FormField v-for="[key,label] in [['opening_depreciation','Hao mòn đầu kỳ (đ)'],['booked_months','Số kỳ đã trích']]" :key="key" :label="label" :error="errors[key]" v-slot="field"><Input v-bind="field" v-model="form[key]" type="number" min="0" :disabled="!!form.name"/></FormField></template>
   <FormField label="Phương pháp"><Select v-model="form.method" aria-label="Phương pháp khấu hao"><option value="Straight Line">Đường thẳng</option><option value="Written Down Value">Số dư giảm dần</option><option value="Double Declining Balance">Số dư giảm dần kép</option></Select></FormField>
   <FormField label="Vườn"><Combobox v-model="form.lotus_farm" :options="options('farms','farm_name')" label="Vườn tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Lô"><Combobox v-model="form.lotus_farm_block" :options="options('blocks','block_code',r=>!form.lotus_farm||r.farm===form.lotus_farm)" label="Lô tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Vụ"><Combobox v-model="form.lotus_crop_cycle" :options="options('cycles')" label="Vụ tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Công việc"><Combobox v-model="form.lotus_work_type" :options="options('work_types','work_name')" label="Công việc tài sản" :disabled="!!form.name"/></FormField>
   <div class="fin-assets__footer"><Button type="button" variant="outline" @click="editor=''">Đóng</Button><Button type="submit" :disabled="saving">Lưu chờ duyệt</Button></div>
  </form>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='operation'" :title="'Nghiệp vụ · '+(selected?.asset_name||'')" width="800px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <form class="fin-assets__form" @submit.prevent="saveOperation"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p>
   <FormField label="Nghiệp vụ"><Select v-model="form.kind" aria-label="Nghiệp vụ tài sản"><option v-for="[value,label] in kinds" :key="value" :value="value">{{label}}</option></Select></FormField>
   <FormField label="Ngày nghiệp vụ" required><DatePicker v-model="form.posting_date" label="Ngày nghiệp vụ tài sản"/></FormField>
   <template v-if="form.kind==='Move'"><FormField label="Vị trí nhận"><Combobox v-model="form.location" :options="options('locations','location_name')" label="Vị trí nhận tài sản"/></FormField><FormField label="Người nhận"><Combobox v-model="form.custodian" :options="options('employees','employee_name')" label="Người nhận tài sản"/></FormField><FormField label="Vườn nhận"><Combobox v-model="form.lotus_farm" :options="options('farms','farm_name')" label="Vườn nhận"/></FormField><FormField label="Lô nhận"><Combobox v-model="form.lotus_farm_block" :options="options('blocks','block_code',r=>!form.lotus_farm||r.farm===form.lotus_farm)" label="Lô nhận"/></FormField><FormField label="Vụ nhận"><Combobox v-model="form.lotus_crop_cycle" :options="options('cycles')" label="Vụ nhận"/></FormField><FormField label="Công việc"><Combobox v-model="form.lotus_work_type" :options="options('work_types','work_name')" label="Công việc nhận"/></FormField></template>
   <template v-if="['Repair','Upgrade','Sell'].includes(form.kind)"><FormField :label="form.kind==='Sell'?'Giá bán chưa thuế (đ)':'Chi phí (đ)'" required><Input v-model="form.amount" type="number" min="1" aria-label="Số tiền nghiệp vụ tài sản"/></FormField></template>
   <template v-if="['Repair','Upgrade'].includes(form.kind)"><FormField label="Hóa đơn sửa chữa đã duyệt"><Combobox v-model="form.purchase_invoice" :options="options('purchases')" label="Hóa đơn sửa chữa"/></FormField><FormField v-if="!form.purchase_invoice" label="Nhà cung cấp"><Combobox v-model="form.supplier" :options="options('suppliers','supplier_name')" label="Nhà cung cấp sửa chữa"/></FormField><FormField label="Tài khoản chi phí trên hóa đơn"><Combobox v-model="form.expense_account" :options="accounts('Expense')" label="Tài khoản sửa chữa"/></FormField><FormField v-if="form.kind==='Upgrade'" label="Tăng thời gian sử dụng (tháng)"><Input v-model="form.increase_months" type="number" min="0" aria-label="Số tháng tăng thêm"/></FormField></template>
   <template v-if="form.kind==='Sell'"><FormField label="Khách hàng"><Combobox v-model="form.customer" :options="options('customers','customer_name')" label="Khách mua tài sản"/></FormField><FormField label="Tài khoản thu nhập khác"><Combobox v-model="form.income_account" :options="accounts('Income')" label="Thu nhập bán tài sản"/></FormField><FormField label="Thuế GTGT"><Select v-model="form.vat_code" aria-label="Thuế suất bán tài sản"><option value="KCT">Không chịu thuế</option><option v-for="n in ['0','5','8','10']" :key="n" :value="n">{{n}}%</option></Select></FormField><FormField label="Ký hiệu hóa đơn điện tử"><Input v-model="form.einvoice_series"/></FormField><FormField label="Số hóa đơn điện tử"><Input v-model="form.einvoice_no"/></FormField></template>
   <template v-if="['Repair','Upgrade'].includes(form.kind)&&!form.purchase_invoice">
    <FormField label="Thuế GTGT đầu vào"><Select v-model="form.vat_code" aria-label="Thuế suất sửa chữa"><option value="KCT">Không chịu thuế</option><option v-for="n in ['0','5','8','10']" :key="n" :value="n">{{n}}%</option></Select></FormField>
    <FormField v-if="form.vat_code!=='KCT'" label="Tài khoản thuế được khấu trừ"><Combobox v-model="form.input_vat_account" :options="accounts('Asset')" label="Thuế đầu vào sửa chữa"/></FormField>
   </template>
   <FormField label="Lý do / nội dung" required><Input v-model="form.reason" aria-label="Lý do nghiệp vụ tài sản"/></FormField>
   <div class="fin-assets__footer"><Button type="button" variant="outline" @click="editor=''">Đóng</Button><Button type="submit" :disabled="saving">Lưu chờ duyệt</Button></div>
  </form>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='allocation'" :title="'Phân bổ '+(selected?.asset_name||'')+' · '+month" width="1180px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><p v-if="form.inherited_from&&form.inherited_from!==month">Kế thừa phân bổ tháng {{form.inherited_from}}.</p>
  <DataTable :rows="allocation" :columns="allocationColumns" row-key="row_key" storage-key="fin-assets-allocation" :pagination="false">
   <template #cell-percent="{row}"><Input v-model="row.percent" type="number" min="0" max="100" step="0.000001" aria-label="Tỷ lệ phân bổ"/></template>
   <template #cell-expense_account="{row}"><Combobox v-model="row.expense_account" :options="accounts('Expense')" label="Tài khoản phân bổ"/></template>
   <template #cell-cost_center="{row}"><Combobox v-model="row.cost_center" :options="options('cost_centers','cost_center_name')" label="Trung tâm chi phí phân bổ"/></template>
   <template #cell-lotus_farm="{row}"><Combobox v-model="row.lotus_farm" :options="options('farms','farm_name')" label="Vườn phân bổ"/></template>
   <template #cell-lotus_farm_block="{row}"><Combobox v-model="row.lotus_farm_block" :options="options('blocks','block_code',r=>!row.lotus_farm||r.farm===row.lotus_farm)" label="Lô phân bổ"/></template>
   <template #cell-lotus_crop_cycle="{row}"><Combobox v-model="row.lotus_crop_cycle" :options="options('cycles')" label="Vụ phân bổ"/></template>
   <template #cell-lotus_work_type="{row}"><Combobox v-model="row.lotus_work_type" :options="options('work_types','work_name')" label="Công việc phân bổ"/></template>
   <template #cell-remove="{row}"><Button size="sm" variant="ghost" @click="allocation=allocation.filter(r=>r!==row)">Xóa</Button></template>
  </DataTable>
  <div class="fin-assets__actions"><Button variant="outline" @click="allocation.push(allocationRow())">Thêm dòng</Button><span>Tổng: {{allocationTotal}}%</span><Button :disabled="saving||Math.abs(allocationTotal-100)>0.0000001" @click="saveAllocation">Lưu phân bổ</Button></div>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='review'" :title="review?.type==='depreciation'?'Xem trước khấu hao '+review.month:'Xem trước nghiệp vụ tài sản'" width="1000px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <template v-if="review"><p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><p v-for="message in review.errors" :key="message" class="hr-ops-error" role="alert">{{message}}</p><p v-for="message in review.warnings||[]" :key="message">{{message}}</p>
   <template v-if="review.type==='depreciation'"><p>Tổng khấu hao: {{fmt(review.total)}} đ<span v-if="review.approved_by"> · Duyệt bởi {{review.approved_by}}</span></p><p v-if="review.results?.length">Bút toán: <template v-for="r in review.results" :key="r.journal"><a :href="documentUrl({doctype:'Journal Entry',name:r.journal})" target="_blank" rel="noopener">{{r.journal}}</a> <a v-if="r.allocation" :href="documentUrl({doctype:'Journal Entry',name:r.allocation})" target="_blank" rel="noopener">{{r.allocation}}</a> </template></p><DataTable :rows="review.rows" :columns="depreciationColumns" row-key="schedule_row" storage-key="fin-assets-preview"/></template>
   <template v-else><p>{{kindLabel(review.kind)}} · {{date(review.posting_date)}} · {{review.asset||review.summary?.values?.asset_name}}</p><dl class="fin-assets__summary"><template v-for="[key,label] in [['amount','Số tiền'],['original','Nguyên giá'],['remaining','Giá trị còn lại'],['depreciation_to_date','Khấu hao bổ sung'],['proceeds','Giá bán chưa thuế'],['vat','Thuế GTGT'],['gain_loss','Lãi / lỗ']]" :key="key"><template v-if="review.summary?.[key]!=null||review.summary?.values?.[key]!=null"><dt>{{label}}</dt><dd>{{fmt(review.summary[key]??review.summary.values[key])}} đ</dd></template></template></dl><dl class="fin-assets__summary"><template v-for="[key,label] in [['code','Mã tài sản'],['asset_name','Tên tài sản'],['asset_category','Nhóm'],['serial_no','Serial'],['purchase_date','Ngày mua'],['available_for_use_date','Ngày sử dụng'],['location','Vị trí'],['custodian','Người quản lý'],['method','Phương pháp'],['months','Số tháng khấu hao'],['booked_months','Số kỳ đã trích'],['increase_months','Số tháng tăng thêm'],['supplier','Nhà cung cấp'],['purchase_invoice','Hóa đơn mua'],['customer','Khách mua'],['expense_account','Tài khoản chi phí'],['income_account','Tài khoản thu nhập'],['vat_code','Thuế GTGT'],['lotus_farm','Vườn'],['lotus_farm_block','Lô']]" :key="key"><template v-if="review.summary?.values?.[key]!=null&&review.summary.values[key]!==''"><dt>{{label}}</dt><dd>{{key.endsWith('_date')?date(review.summary.values[key]):key==='method'?({'Straight Line':'Đường thẳng','Written Down Value':'Số dư giảm dần','Double Declining Balance':'Số dư giảm dần kép'})[review.summary.values[key]]:review.summary.values[key]}}</dd></template></template></dl><p v-if="review.documents?.length">Chứng từ: <a v-for="d in review.documents" :key="d.name" :href="documentUrl(d)" target="_blank" rel="noopener">{{d.name}} </a></p></template>
   <div class="fin-assets__footer"><Button variant="outline" @click="review.type==='depreciation'?reviewDepreciation():reviewOperation(review)">Xem trước lại</Button><Button v-if="review.type==='depreciation'&&canWrite&&!review.posted" :disabled="saving||!!review.errors?.length||!review.rows?.length" variant="outline" @click="prepare">Lưu bảng chờ duyệt</Button><Button v-if="canApprove&&(review.type==='depreciation'?!review.posted:review.state==='Pending')" :disabled="saving||!!review.errors?.length" @click="approve">Duyệt và ghi sổ</Button></div>
  </template>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='detail'" :title="selected?.asset_name||'Tài sản'" width="950px" @update:model-value="v=>{if(!v)editor=''}"><template v-if="schedule"><p>{{schedule.asset.lotus_asset_code}} · {{schedule.asset.lotus_serial_no||'Chưa có serial'}} · {{schedule.asset.location}}</p><template v-for="book in schedule.schedules" :key="book.name"><p>{{book.finance_book||'Sổ mặc định'}} · {{book.name}}</p><DataTable :rows="book.rows" :columns="scheduleColumns" row-key="name" storage-key="fin-assets-schedule"/></template></template></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='category'" title="Nhóm tài sản và tài khoản" width="720px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form class="fin-assets__form" @submit.prevent="saveCategory"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Tên nhóm" required><Input v-model="form.asset_category_name"/></FormField><FormField v-for="[key,label,root] in [['fixed_asset_account','Tài khoản nguyên giá','Asset'],['accumulated_depreciation_account','Tài khoản hao mòn','Asset'],['depreciation_expense_account','Tài khoản khấu hao','Expense'],['capital_work_in_progress_account','Tài khoản mua sắm chờ ghi tăng','Asset']]" :key="key" :label="label" required><Combobox v-model="form[key]" :options="accounts(root)" :label="label"/></FormField><FormField label="Khấu hao"><Select v-model="form.non_depreciable_category" aria-label="Nhóm có khấu hao"><option value="0">Có khấu hao</option><option value="1">Không khấu hao</option></Select></FormField><div class="fin-assets__footer"><Button type="submit" :disabled="saving">Lưu nhóm</Button></div></form></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='location'" title="Vị trí tài sản" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form @submit.prevent="saveLocation"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Tên vị trí" required v-slot="field"><Input v-bind="field" v-model="form.location_name"/></FormField><Button type="submit" :disabled="saving">Lưu vị trí</Button></form></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='import'" title="Nhập tài sản đầu kỳ từ Excel" width="950px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><div class="fin-assets__actions"><Button variant="outline" @click="download('import_template')">Tải mẫu</Button><input type="file" accept=".xlsx" aria-label="File tài sản đầu kỳ" @change="readFile"/><Button :disabled="!importContent||busy" @click="previewImport">Xem trước</Button></div><template v-if="importPreview"><DataTable :rows="importPreview.rows" :columns="importColumns" row-key="line" storage-key="fin-assets-import"/><Button :disabled="saving||!importPreview.valid" @click="commitImport">Tạo hồ sơ chờ duyệt</Button></template></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='reason'" title="Hủy / đảo nghiệp vụ tài sản" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form @submit.prevent="cancel"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Lý do" required v-slot="field"><Input v-bind="field" v-model="reason" minlength="5"/></FormField><Button type="submit" :disabled="saving||reason.trim().length<5">Xác nhận hủy / đảo</Button></form></WorkspaceModal>
 <p v-if="editor&&error" class="hr-ops-error" role="alert">{{error}}</p>
</section>
</template>

<style>
.fin-assets{display:grid;gap:var(--lotus-space-3)}
.fin-assets__toolbar{display:flex;align-items:center;gap:var(--lotus-space-2);overflow-x:auto;white-space:nowrap}
.fin-assets__toolbar>*{flex-shrink:0}.fin-assets__toolbar>input{min-width:180px;flex:1}
.fin-assets__toolbar>select{width:auto;max-width:240px}
.fin-assets__actions{display:flex;align-items:center;gap:var(--lotus-space-2);flex-wrap:wrap}
.fin-assets__form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3)}
.fin-assets__footer{grid-column:1/-1;display:flex;justify-content:flex-end;gap:var(--lotus-space-2);margin-top:var(--lotus-space-3)}
.fin-assets__summary{display:grid;grid-template-columns:1fr 1fr;gap:var(--lotus-space-2)}.fin-assets__summary dd{margin:0;text-align:right}
.fin-assets__activation{padding:var(--lotus-space-3);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
@media(max-width:640px){.fin-assets__form{grid-template-columns:1fr}}
</style>

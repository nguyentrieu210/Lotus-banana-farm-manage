<script setup>
import {FileInput} from '../ui/file-input'
import {computed,onMounted,ref,watch} from 'vue'
import DataTable from '../DataTable.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import FinanceMasterImport from './FinanceMasterImport.vue'
import MonthPicker from '../MonthPicker.vue'
import {Button} from '../ui/button'
import {Input,MoneyInput} from '../ui/input'
import {FormField} from '../ui/form-field'
import {DatePicker,DateRangePicker} from '../ui/date-picker'
import {Combobox} from '../ui/combobox'
import Select from '../ui/select/Select.vue'
import LotusIcon from '../LotusIcon.vue'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem} from '../ui/dropdown-menu'
import {assetSections,assetView,registerRows,assetStatus,filterRegister,matches} from '../../asset-workspace'
import {call} from '../../api'

const props=defineProps({view:{type:String,default:'assets'}})
const emit=defineEmits(['notice','view-change','go-settings'])
const API='lotus_farm.finance.assets.'
const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Ho_Chi_Minh'})
const month=ref(today.slice(0,7)),section=ref(assetView(props.view)),search=ref(''),data=ref(null),lookups=ref({}),catalog=ref({}),error=ref(''),busy=ref(false),saving=ref(false)
const editor=ref(''),form=ref({}),errors=ref({}),selected=ref(null),review=ref(null),schedule=ref(null),report=ref(null),allocation=ref([]),purchaseRows=ref([])
const reportFarm=ref(''),importContent=ref(''),importPreview=ref(null),reason=ref(''),cancelTarget=ref(null)
const masterImport=ref(''),detailTab=ref('profile'),catalogSelection=ref(null)
const filters=ref({category:'',location:'',farm:'',status:''}),operationState=ref(''),runState=ref(''),accountScope=ref('active'),accountGroup=ref('')
const operationFrom=ref(''),operationTo=ref('')
const kinds=[['Move','Điều chuyển / bàn giao'],['Repair','Sửa chữa'],['Upgrade','Nâng cấp / vốn hóa'],['Suspend','Tạm ngừng sử dụng'],['Resume','Sử dụng lại'],['Sell','Bán tài sản'],['Scrap','Thanh lý / loại bỏ'],['Restore','Phục hồi thanh lý']]
const kindLabel=v=>v==='Create'?'Ghi tăng tài sản':v==='Profile'?'Cập nhật hồ sơ':kinds.find(k=>k[0]===v)?.[1]||v
const stateLabel=v=>({Pending:'Chờ duyệt',Posted:'Đã duyệt',Cancelled:'Đã hủy',Submitted:'Đang sử dụng',Draft:'Nháp',Sold:'Đã bán',Scrapped:'Đã thanh lý',Suspended:'Tạm ngừng · vẫn khấu hao','Partially Depreciated':'Đang khấu hao','Fully Depreciated':'Đã khấu hao hết','In Maintenance':'Đang bảo trì'})[v]||v
const fmt=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const documentUrl=d=>'/desk/'+d.doctype.toLowerCase().replaceAll(' ','-')+'/'+encodeURIComponent(d.name)
const date=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):'—'
const canWrite=computed(()=>!!data.value?.permissions?.write),canApprove=computed(()=>!!data.value?.permissions?.approve)
const register=computed(()=>registerRows(data.value||{}))
const assets=computed(()=>filterRegister(register.value,search.value,filters.value))
const categories=computed(()=>(catalog.value.categories||[]).filter(r=>matches(r,search.value,['asset_category_name','fixed_asset_account','accumulated_depreciation_account','depreciation_expense_account'])))
const locations=computed(()=>(catalog.value.locations||[]).filter(r=>matches(r,search.value,['name','location_name'])))
const accountRows=computed(()=>(catalog.value.accounts||[]).filter(r=>(accountScope.value==='all'||(!r.disabled&&!!r.account_number))&&(!accountGroup.value||(r.categories||[]).includes(accountGroup.value))&&matches(r,search.value,['account_number','account_name','parent_account'])))
const operations=computed(()=>(data.value?.operations||[]).map(r=>({...r,asset_label:operationLabel(r)})).filter(r=>(!operationState.value||r.state===operationState.value)&&(!operationFrom.value||r.posting_date>=operationFrom.value)&&(!operationTo.value||String(r.posting_date).slice(0,10)<=operationTo.value)&&matches(r,search.value,['name','asset','asset_label','reason'])))
const runs=computed(()=>(data.value?.runs||[]).filter(r=>(!runState.value||r.state===runState.value)&&matches(r,search.value,['month','name','approved_by'])))
const counts=computed(()=>({assets:register.value.length,categories:catalog.value.categories?.length||0,locations:catalog.value.locations?.length||0,accounts:(catalog.value.accounts||[]).filter(r=>r.account_number&&!r.disabled).length,depreciation:data.value?.runs?.length||0,operations:data.value?.operations?.length||0}))
const amount=(value)=>value==null?'—':fmt(value)+' đ'
const accountLabel=name=>{const r=(catalog.value.accounts||lookups.value.accounts||[]).find(a=>a.name===name);return r?(r.account_number?r.account_number+' · ':'')+r.account_name:name||'Chưa cấu hình'}
const locationLabel=name=>(catalog.value.locations||lookups.value.locations||[]).find(r=>r.name===name)?.location_name||name||'—'
const farmLabel=name=>(lookups.value.farms||[]).find(r=>r.name===name)?.farm_name||name||'—'
const blockLabel=name=>(lookups.value.blocks||[]).find(r=>r.name===name)?.block_code||name||'—'
const pendingCount=computed(()=>data.value?.pending_assets?.length||0)
const filteredRegister=computed(()=>!!search.value||Object.values(filters.value).some(Boolean))
const options=(key,label='name',filter=()=>true)=>(lookups.value[key]||[]).filter(filter).map(r=>({value:r.name,label:r[label]||r.name,subtitle:r.name}))
const allOptions=(key,label,title)=>[{value:'',label:title},...options(key,label)]
const accounts=kind=>(lookups.value.accounts||[]).filter(r=>!kind||r.root_type===kind).map(r=>({value:r.name,label:(r.account_number||'')+' · '+r.account_name}))
const categoryAccountOptions=key=>{const types={fixed_asset_account:'Fixed Asset',accumulated_depreciation_account:'Accumulated Depreciation',depreciation_expense_account:'Depreciation',capital_work_in_progress_account:'Capital Work in Progress'};return(lookups.value.accounts||[]).filter(r=>r.account_type===types[key]).map(r=>({value:r.name,label:accountLabel(r.name)}))}
const column=(field,headerName,extra={})=>({field,headerName,minWidth:130,flex:1,...(['posting_date','schedule_date','available_for_use_date'].includes(field)?{valueFormatter:p=>date(p.value)}:{}),...(['total_asset_cost','accumulated_depreciation','value_after_depreciation','depreciation_amount','accumulated_depreciation_amount','amount','depreciation','accumulated','remaining'].includes(field)?{valueFormatter:p=>amount(p.value)}:{}),...(field==='actions'?{pinned:'right'}:{}),...extra})
const assetColumns=[column('lotus_asset_code','Mã tài sản',{pinned:'left'}),column('asset_name','Tài sản',{minWidth:220}),column('asset_category','Nhóm',{minWidth:220}),column('location','Vị trí',{valueFormatter:p=>locationLabel(p.value)}),column('lotus_farm','Vườn',{valueFormatter:p=>farmLabel(p.value)}),column('lotus_farm_block','Lô',{valueFormatter:p=>blockLabel(p.value)}),column('available_for_use_date','Ngày sử dụng'),column('total_asset_cost','Nguyên giá'),column('accumulated_depreciation','Hao mòn'),column('value_after_depreciation','Giá trị còn lại'),column('status','Trạng thái',{minWidth:170,valueGetter:p=>stateLabel(assetStatus(p.data))}),column('actions','Thao tác',{minWidth:160,sortable:false})]
const categoryAccounts=[['fixed_asset_account','TK nguyên giá','Asset'],['accumulated_depreciation_account','TK hao mòn','Asset'],['depreciation_expense_account','TK khấu hao','Expense'],['capital_work_in_progress_account','TK chờ ghi tăng','Asset']]
const categoryColumns=[column('asset_category_name','Nhóm tài sản',{minWidth:300}),...categoryAccounts.map(([key,label])=>column(key,label,{minWidth:210,valueFormatter:p=>accountLabel(p.value)})),column('non_depreciable_category','Khấu hao',{valueFormatter:p=>Number(p.value)?'Không khấu hao':'Có khấu hao'}),column('asset_count','Tài sản'),column('pending_count','Chờ duyệt'),column('actions','Thao tác',{minWidth:150,sortable:false})]
const locationColumns=[column('location_name','Vị trí',{minWidth:240}),column('name','Mã vị trí',{minWidth:200}),column('asset_count','Tài sản'),column('pending_count','Chờ duyệt'),column('actions','Thao tác',{sortable:false,minWidth:160})]
const rootLabel=value=>({Asset:'Tài sản',Liability:'Nợ phải trả',Equity:'Vốn chủ sở hữu',Income:'Doanh thu',Expense:'Chi phí'})[value]||value
const typeLabel=value=>({'Fixed Asset':'Tài sản cố định','Accumulated Depreciation':'Hao mòn lũy kế',Depreciation:'Chi phí khấu hao','Capital Work in Progress':'Xây dựng, mua sắm dở dang',Bank:'Ngân hàng',Cash:'Tiền mặt',Stock:'Hàng tồn kho',Payable:'Phải trả',Receivable:'Phải thu',Tax:'Thuế','Expense Account':'Chi phí','Income Account':'Thu nhập','Cost of Goods Sold':'Giá vốn'})[value]||value||'—'
const accountColumns=[column('account_number','Số TK',{minWidth:110}),column('account_name','Tên tài khoản',{minWidth:270}),column('parent_account','Tài khoản cha',{minWidth:240,valueFormatter:p=>accountLabel(p.value)}),column('is_group','Cấp tài khoản',{valueFormatter:p=>Number(p.value)?'Tổng hợp':'Chi tiết'}),column('root_type','Nhóm gốc',{valueFormatter:p=>rootLabel(p.value)}),column('account_type','Loại',{minWidth:200,valueFormatter:p=>typeLabel(p.value)}),column('categories','Nhóm tài sản sử dụng',{minWidth:260,valueFormatter:p=>(p.value||[]).join('; ')||'—'}),column('disabled','Trạng thái',{valueFormatter:p=>Number(p.value)?'Ngừng dùng':'Đang dùng'})]
const opColumns=[column('posting_date','Ngày'),column('kind','Nghiệp vụ'),column('asset_label','Tài sản',{minWidth:220}),column('state','Trạng thái'),column('approved_by','Người duyệt'),column('actions','Thao tác',{minWidth:160,sortable:false})]
const runColumns=[column('month','Tháng'),column('state','Trạng thái'),column('approved_by','Người duyệt'),column('actions','Thao tác',{sortable:false})]
const depreciationColumns=[column('asset_name','Tài sản',{minWidth:200}),column('schedule_date','Ngày trích'),column('amount','Khấu hao'),column('allocation_summary','Phân bổ',{minWidth:300,valueGetter:p=>(p.data.allocations||[]).map(r=>(r.lotus_farm_block||r.lotus_farm||r.expense_account)+': '+r.percent+'% · '+fmt(r.amount)+' đ').join('; ')})]
const allocationColumns=[column('percent','Tỷ lệ %'),column('expense_account','Tài khoản',{minWidth:200}),column('cost_center','Trung tâm chi phí',{minWidth:200}),column('lotus_farm','Vườn',{minWidth:180}),column('lotus_farm_block','Lô',{minWidth:180}),column('lotus_crop_cycle','Vụ',{minWidth:180}),column('lotus_work_type','Công việc',{minWidth:180}),column('remove','',{minWidth:70,sortable:false})]
const scheduleColumns=[column('schedule_date','Ngày trích'),column('depreciation_amount','Khấu hao'),column('accumulated_depreciation_amount','Lũy kế'),column('journal_entry','Bút toán')]
const historyColumns=[column('posting_date','Ngày'),column('kind','Nghiệp vụ',{valueFormatter:p=>kindLabel(p.value)}),column('state','Trạng thái',{valueFormatter:p=>stateLabel(p.value)}),column('reason','Lý do',{minWidth:240}),column('approved_by','Người duyệt')]
const reportColumns=[...assetColumns.slice(0,4),column('total_asset_cost','Nguyên giá'),column('depreciation','Khấu hao đã ghi'),column('accumulated','Hao mòn lũy kế'),column('remaining','Giá trị còn lại')]
let allocationRowKey=0
const allocationRow=(row={percent:0})=>({...row,row_key:'allocation-'+(++allocationRowKey)})
const importColumns=[column('line','Dòng'),column('code','Mã',{valueGetter:p=>p.data.values.code}),column('asset_name','Tài sản',{valueGetter:p=>p.data.values.asset_name}),column('errors','Lỗi',{minWidth:300,valueGetter:p=>Object.values(p.data.errors||{}).join('; ')})]

async function task(fn){busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message||String(e)}finally{busy.value=false}}
async function load(){return task(async()=>{const result=await Promise.all([call(API+'overview',{month:month.value}),call(API+'lookups'),call(API+'catalogs')]);[data.value,lookups.value,catalog.value]=result;if(section.value==='report')await loadReport()})}
async function mutate(fn,notice){saving.value=true;errors.value={};error.value='';try{const result=await fn();if(result?.errors&&Object.keys(result.errors).length){errors.value=result.errors;return}emit('notice',notice);editor.value='';await load();return result}catch(e){error.value=e.message||String(e)}finally{saving.value=false}}
async function activate(){await mutate(()=>call(API+'activate',{on:1},true),'Đã bật quản lý tài sản; khấu hao chờ kế toán trưởng duyệt.')}
async function showAsset(row){if(row.pending)return reviewOperation({name:row.operation});await task(async()=>{selected.value=row;detailTab.value='profile';schedule.value=await call(API+'detail',{asset:row.name});editor.value='detail'})}
async function openAsset(row){errors.value={};error.value='';selected.value=row||null;purchaseRows.value=[]
 if(row?.pending){form.value={...row.values,existing:row.values.existing?'1':'0',operation:row.operation,modified:row.modified,posting_date:String(row.posting_date).slice(0,10)};if(form.value.purchase_invoice)await loadPurchase(form.value.purchase_invoice)}
 else if(row){const detail=await task(()=>call(API+'detail',{asset:row.name}));if(!detail)return;const a=detail.asset,b=a.finance_books?.[0]||{}
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
function openCategory(row){errors.value={};error.value='';form.value=row?{...row,non_depreciable_category:String(Number(row.non_depreciable_category))}:{asset_category_name:'',non_depreciable_category:'0'};editor.value='category'}
async function saveCategory(){await mutate(()=>call(API+'save_category',{values:JSON.stringify(form.value)},true),'Đã lưu nhóm tài sản.')}
async function importedMasters(result){emit('notice',`Đã nhập ${result.count} ${result.kind==='accounts'?'tài khoản':'nhóm tài sản'}; bỏ qua ${result.skipped} dòng đã có.`);await load()}
function openLocation(row){error.value='';form.value=row?{...row}:{location_name:''};editor.value='location'}
async function saveLocation(){await mutate(()=>call(API+'save_location',{location_name:form.value.location_name,name:form.value.name,modified:form.value.modified},true),'Đã lưu vị trí tài sản.')}
function showCatalog(row,type){catalogSelection.value={row,type};editor.value='catalog-detail'}
function viewAssets(key,value){search.value='';filters.value={category:'',location:'',farm:'',status:'',[key]:value};section.value='assets'}
function openImport(){error.value='';importPreview.value=null;importContent.value='';editor.value='import'}
function clearAssetFilters(){search.value='';filters.value={category:'',location:'',farm:'',status:''}}
function operationLabel(op){const a=(data.value?.assets||[]).find(a=>a.name===op.asset);if(a)return a.lotus_asset_code+' · '+a.asset_name;try{const v=typeof op.payload==='string'?JSON.parse(op.payload):op.payload;return v?.asset_name?((v.code||'')+' · '+v.asset_name):op.asset||'—'}catch{return op.asset||'—'}}
async function loadReport(){report.value=await call(API+'report',{farm:reportFarm.value||undefined,on_date:month.value+'-'+new Date(Number(month.value.slice(0,4)),Number(month.value.slice(5,7)),0).getDate()})}
function download(method){window.location.href='/api/method/'+API+method+(method==='export'?'?on_date='+encodeURIComponent(month.value+'-'+new Date(Number(month.value.slice(0,4)),Number(month.value.slice(5,7)),0).getDate())+(reportFarm.value?'&farm='+encodeURIComponent(reportFarm.value):''):'')}
async function readFile(event){const file=event.target.files?.[0];importPreview.value=null;importContent.value='';if(!file)return;if(file.size>5_000_000){error.value='File vượt quá 5 MB.';return}const reader=new FileReader();reader.onload=()=>{importContent.value=String(reader.result)};reader.readAsDataURL(file)}
async function previewImport(){await task(async()=>{importPreview.value=await call(API+'import_preview',{content:importContent.value},true)})}
async function commitImport(){await mutate(()=>call(API+'import_commit',{content:importContent.value,fingerprint:importPreview.value.fingerprint},true),'Đã tạo hồ sơ tài sản chờ duyệt; chưa ghi số dư đầu kỳ.')}
watch(month,()=>{review.value=null;load()})
watch(reportFarm,()=>{if(section.value==='report')task(loadReport)})
watch(()=>props.view,value=>{if(section.value!==assetView(value))section.value=assetView(value)})
watch(section,async value=>{error.value='';search.value='';if(value!==assetView(props.view))emit('view-change',value);if(value==='report')await task(loadReport)})
onMounted(load)
defineExpose({load})
</script>

<template>
<section class="fin-assets" aria-label="Tài sản cố định">
 <nav class="fin-assets__nav" aria-label="Các mục tài sản cố định"><Button v-for="item in assetSections" :key="item.id" variant="ghost" :aria-current="section===item.id?'page':undefined" :class="{'is-active':section===item.id}" :aria-label="item.label" @click="section=item.id"><LotusIcon :name="item.icon"/>{{item.label}}<span v-if="counts[item.id]!=null" class="fin-assets__count">{{counts[item.id]}}</span></Button></nav>
 <div class="fin-assets__toolbar">
  <template v-if="data?.enabled&&canWrite">
   <Button v-if="section==='assets'" :disabled="saving" @click="openAsset()">Thêm tài sản</Button>
   <Button v-if="section==='assets'" variant="outline" @click="openImport">Nhập Excel</Button>
   <Button v-if="section==='depreciation'" :disabled="busy" @click="reviewDepreciation">Lập bảng khấu hao</Button>
  </template>
  <template v-if="section==='categories'&&canApprove"><Button :disabled="saving" @click="openCategory()">Thêm nhóm</Button><Button variant="outline" @click="masterImport='categories'">Nhập nhóm Excel</Button></template>
  <Button v-if="section==='locations'&&canWrite" :disabled="saving" @click="openLocation()">Thêm vị trí</Button>
  <template v-if="section==='accounts'"><Button v-if="canApprove" variant="outline" @click="masterImport='accounts'">Nhập tài khoản Excel</Button><Button variant="outline" @click="emit('go-settings')">Mở Thiết lập</Button></template>

  <template v-if="section==='assets'"><Combobox v-model="filters.category" :options="allOptions('categories','asset_category_name','Tất cả nhóm')" label="Lọc nhóm tài sản" placeholder="Tất cả nhóm"/><Combobox v-model="filters.location" :options="allOptions('locations','location_name','Tất cả vị trí')" label="Lọc vị trí tài sản" placeholder="Tất cả vị trí"/><Combobox v-model="filters.farm" :options="allOptions('farms','farm_name','Tất cả vườn')" label="Lọc vườn tài sản" placeholder="Tất cả vườn"/><Select v-model="filters.status" aria-label="Trạng thái tài sản"><option value="">Tất cả trạng thái</option><option v-for="state in ['Pending','Submitted','Partially Depreciated','Fully Depreciated','Suspended','Sold','Scrapped','Cancelled']" :key="state" :value="state">{{stateLabel(state)}}</option></Select></template>
  <MonthPicker v-if="['depreciation','report'].includes(section)" v-model="month" :label="section==='report'?'Tháng báo cáo':'Tháng lập khấu hao'"/>
  <DateRangePicker v-if="section==='operations'" v-model:from="operationFrom" v-model:to="operationTo" label="Ngày biến động tài sản"/>
  <Select v-if="section==='operations'" v-model="operationState" aria-label="Trạng thái biến động"><option value="">Tất cả trạng thái</option><option v-for="state in ['Pending','Posted','Cancelled']" :key="state" :value="state">{{stateLabel(state)}}</option></Select>
  <Select v-if="section==='depreciation'" v-model="runState" aria-label="Trạng thái bảng khấu hao"><option value="">Tất cả trạng thái</option><option v-for="state in ['Pending','Posted','Cancelled']" :key="state" :value="state">{{stateLabel(state)}}</option></Select>
  <template v-if="section==='accounts'"><Select v-model="accountScope" aria-label="Phạm vi tài khoản"><option value="active">Có mã, đang dùng</option><option value="all">Tất cả tài khoản</option></Select><Combobox v-model="accountGroup" :options="allOptions('categories','asset_category_name','Tất cả nhóm sử dụng')" label="Nhóm sử dụng tài khoản" placeholder="Tất cả nhóm sử dụng"/></template>
  <Button variant="outline" :disabled="busy||saving" @click="load">Làm mới</Button>
  <Input v-if="section!=='report'" v-model="search" type="search" :placeholder="section==='assets'?'Tìm mã, tên, serial…':'Tìm kiếm…'" :aria-label="'Tìm '+(assetSections.find(s=>s.id===section)?.label.toLowerCase()||'tài sản')"/>
  <Combobox v-if="section==='report'" v-model="reportFarm" :options="options('farms','farm_name')" label="Vườn báo cáo tài sản" placeholder="Tất cả vườn"/>
  <Button v-if="section==='report'" variant="outline" @click="download('export')">Xuất Excel</Button>
 </div>
 <p v-if="busy" role="status">Đang tải tài sản…</p>
 <p v-if="error&&!editor" class="hr-ops-error" role="alert">{{error}}</p>
 <div v-if="data&&!data.enabled" class="fin-assets__activation">
  <p>Quản lý tài sản chưa bật. Khi bật, khấu hao chuyển sang xem trước và kế toán trưởng duyệt; hệ thống không tự tạo tài sản hay ghi số dư.</p>
  <Button v-if="canApprove" :disabled="saving" @click="activate">Bật quản lý tài sản</Button>
 </div>
 <template v-if="section==='assets'&&data?.enabled">
 <p v-if="!busy&&!register.length" class="fin-assets__empty-note" role="status">Chưa có hồ sơ tài sản. Đã có {{counts.categories}} nhóm và {{counts.locations}} vị trí để chọn khi nhập hồ sơ.</p>
 <p v-else-if="!busy&&!assets.length" class="fin-assets__empty-note" role="status">Không có tài sản khớp bộ lọc.</p>
 <DataTable :rows="assets" :columns="assetColumns" row-key="row_key" storage-key="fin-assets-register-v2" :loading="busy" show-empty-headers :empty="filteredRegister?'Không có tài sản khớp bộ lọc.':'Chưa có hồ sơ tài sản.'">
  <template #cell-total_asset_cost="{row}"><span>{{amount(row.total_asset_cost??row.net_purchase_amount)}}</span><small v-if="row.pending" class="fin-assets__muted">Đề nghị ghi nhận</small></template>
  <template #cell-status="{row}"><span class="fin-assets__status" :class="{'is-pending':row.pending}">{{stateLabel(assetStatus(row))}}</span></template>
  <template #cell-actions="{row}"><DropdownMenu><DropdownMenuTrigger as-child><Button size="sm" variant="outline" :aria-label="'Thao tác '+row.lotus_asset_code">Thao tác<LotusIcon name="chevron-down"/></Button></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuItem @select="showAsset(row)">{{row.pending?'Xem trước':'Chi tiết'}}</DropdownMenuItem><template v-if="canWrite&&row.docstatus!==2"><DropdownMenuItem @select="openAsset(row)">Sửa hồ sơ</DropdownMenuItem><DropdownMenuItem v-if="row.pending" @select="requestCancel('operation',{name:row.operation})">Hủy hồ sơ chờ duyệt</DropdownMenuItem><template v-else><DropdownMenuItem @select="openAllocation(row)">Phân bổ</DropdownMenuItem><DropdownMenuItem @select="openOperation(row)">Nghiệp vụ</DropdownMenuItem></template></template></DropdownMenuContent></DropdownMenu></template>
 </DataTable>
 <div v-if="!busy&&!assets.length" class="fin-assets__actions"><Button v-if="filteredRegister" variant="outline" @click="clearAssetFilters">Xóa bộ lọc</Button><template v-else><template v-if="canWrite"><Button @click="openAsset()">Tạo hồ sơ tài sản</Button><Button variant="outline" @click="openImport">Nhập danh sách đầu kỳ</Button></template><Button variant="outline" @click="section='categories'">Xem nhóm đã có</Button></template></div>
 <p v-if="register.length" class="fin-assets__muted">{{assets.length}} / {{register.length}} hồ sơ · {{pendingCount}} chờ duyệt. Giá trị sổ sách: nguyên giá {{amount(data.totals?.original)}} · còn lại {{amount(data.totals?.remaining)}}.</p>
 </template>
 <DataTable v-if="section==='categories'" :rows="categories" :columns="categoryColumns" :loading="busy" row-key="name" storage-key="fin-assets-categories" :empty="search?'Không có nhóm khớp tìm kiếm.':'Chưa có nhóm tài sản.'"><template #cell-actions="{row}"><DropdownMenu><DropdownMenuTrigger as-child><Button size="sm" variant="outline" :aria-label="'Thao tác nhóm '+row.name">Thao tác<LotusIcon name="chevron-down"/></Button></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuItem @select="showCatalog(row,'category')">Chi tiết</DropdownMenuItem><DropdownMenuItem @select="viewAssets('category',row.name)">Xem tài sản</DropdownMenuItem><DropdownMenuItem v-if="row.can_edit" @select="openCategory(row)">Sửa cấu hình</DropdownMenuItem></DropdownMenuContent></DropdownMenu></template></DataTable>
 <DataTable v-if="section==='locations'" :rows="locations" :columns="locationColumns" :loading="busy" row-key="name" storage-key="fin-assets-locations" :empty="search?'Không có vị trí khớp tìm kiếm.':'Chưa có vị trí tài sản.'"><template #cell-actions="{row}"><DropdownMenu><DropdownMenuTrigger as-child><Button size="sm" variant="outline" :aria-label="'Thao tác vị trí '+row.name">Thao tác<LotusIcon name="chevron-down"/></Button></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuItem @select="showCatalog(row,'location')">Chi tiết</DropdownMenuItem><DropdownMenuItem @select="viewAssets('location',row.name)">Xem tài sản</DropdownMenuItem><DropdownMenuItem v-if="row.can_edit" @select="openLocation(row)">Sửa tên hiển thị</DropdownMenuItem></DropdownMenuContent></DropdownMenu></template></DataTable>
 <DataTable v-if="section==='accounts'" :rows="accountRows" :columns="accountColumns" :loading="busy" row-key="name" storage-key="fin-assets-accounts" empty="Không có tài khoản khớp bộ lọc."/>
 <template v-if="section==='depreciation'&&data?.enabled"><DataTable :rows="runs" :columns="runColumns" :loading="busy" row-key="name" storage-key="fin-assets-runs" :empty="search||runState?'Không có bảng khấu hao khớp bộ lọc.':'Chưa có bảng khấu hao. Chọn tháng để lập và xem trước.'">
  <template #cell-state="{row}">{{stateLabel(row.state)}}</template><template #cell-actions="{row}"><Button size="sm" variant="outline" @click="reviewRun(row)">{{row.state==='Pending'?'Xem trước':'Chi tiết'}}</Button><Button v-if="canApprove&&row.state==='Posted'" size="sm" variant="outline" @click="requestCancel('run',row)">Đảo bảng</Button></template>
 </DataTable></template>
 <DataTable v-if="section==='operations'&&data?.enabled" :rows="operations" :columns="opColumns" :loading="busy" row-key="name" storage-key="fin-assets-operations-v2" :empty="search||operationState?'Không có biến động khớp bộ lọc.':'Chưa có nghiệp vụ tài sản.'">
  <template #cell-posting_date="{row}">{{date(row.posting_date)}}</template><template #cell-kind="{row}">{{kindLabel(row.kind)}}</template><template #cell-state="{row}">{{stateLabel(row.state)}}</template>
  <template #cell-actions="{row}"><div class="fin-assets__actions"><Button size="sm" variant="outline" @click="reviewOperation(row)">{{row.state==='Pending'?'Xem trước':'Chi tiết'}}</Button><Button v-if="row.state!=='Cancelled'&&(row.state==='Pending'?canWrite:canApprove)" size="sm" variant="ghost" @click="requestCancel('operation',row)">Hủy</Button></div></template>
 </DataTable>
 <template v-if="section==='report'&&report"><p>Nguyên giá: {{amount(report.totals.original)}} · Hao mòn: {{amount(report.totals.accumulated)}} · Còn lại: {{amount(report.totals.remaining)}}</p><DataTable :rows="report.rows" :columns="reportColumns" :loading="busy" row-key="name" storage-key="fin-assets-report" empty="Chưa có tài sản trong kỳ."/></template>

 <WorkspaceModal :model-value="editor==='asset'" :title="form.name?'Cập nhật hồ sơ tài sản':form.operation?'Sửa hồ sơ chờ duyệt':'Lập hồ sơ tài sản'" width="900px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <form class="fin-assets__form" @submit.prevent="saveAsset"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p>
   <fieldset class="fin-assets__group"><legend>Hồ sơ và nguồn hình thành</legend>
   <FormField label="Nguồn tài sản"><Select v-model="form.existing" :disabled="!!form.name" aria-label="Nguồn tài sản"><option value="1">Tài sản đầu kỳ</option><option value="0">Mua mới</option></Select></FormField>
   <FormField v-for="[key,label] in [['code','Mã tài sản'],['asset_name','Tên tài sản'],['serial_no','Số sê-ri']]" :key="key" :label="label" :error="errors[key]" :required="key!=='serial_no'" v-slot="field"><Input v-bind="field" v-model="form[key]"/></FormField>
   <FormField label="Nhóm tài sản" required :error="errors.asset_category"><Combobox v-model="form.asset_category" :options="options('categories','asset_category_name')" label="Nhóm tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Vị trí" required :error="errors.location"><Combobox v-model="form.location" :options="options('locations','location_name')" label="Vị trí tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Người quản lý"><Combobox v-model="form.custodian" :options="options('employees','employee_name')" label="Người quản lý tài sản" :disabled="!!form.name"/></FormField>
   <FormField v-for="[key,label] in [['posting_date','Ngày nghiệp vụ'],['purchase_date','Ngày mua'],['available_for_use_date','Ngày đưa vào sử dụng']]" :key="key" :label="label" required :error="errors[key]"><DatePicker v-model="form[key]" :label="label" :disabled="!!form.name&&key!=='posting_date'"/></FormField>
   </fieldset>
   <fieldset v-if="Number(form.existing)===0&&!form.name" class="fin-assets__group"><legend>Thông tin mua tài sản</legend>
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
   </fieldset>
   <fieldset class="fin-assets__group"><legend>{{Number(form.existing)===1?'Giá trị đầu kỳ và khấu hao':'Giá trị và khấu hao'}}</legend>
   <FormField v-for="[key,label] in [['amount','Nguyên giá (đ)'],['months','Tổng số tháng khấu hao'],['salvage_value','Giá trị thu hồi (đ)']]" :key="key" :label="label" required :error="errors[key]" v-slot="field"><component :is="key==='months'?Input:MoneyInput" v-bind="field" v-model="form[key]" type="number" min="0" :disabled="key==='amount'&&!!form.name"/></FormField>
   <template v-if="Number(form.existing)===1"><FormField v-for="[key,label] in [['opening_depreciation','Hao mòn đầu kỳ (đ)'],['booked_months','Số kỳ đã trích']]" :key="key" :label="label" :error="errors[key]" v-slot="field"><component :is="key==='booked_months'?Input:MoneyInput" v-bind="field" v-model="form[key]" type="number" min="0" :disabled="!!form.name"/></FormField></template>
   <FormField label="Phương pháp"><Select v-model="form.method" aria-label="Phương pháp khấu hao"><option value="Straight Line">Đường thẳng</option><option value="Written Down Value">Số dư giảm dần</option><option value="Double Declining Balance">Số dư giảm dần kép</option></Select></FormField>
   <p v-if="Number(form.existing)===1" class="fin-assets__hint">Hồ sơ đầu kỳ lưu nguyên giá và hao mòn để đối chiếu với số dư đầu kỳ đã nhập.</p>
   </fieldset>
   <fieldset class="fin-assets__group"><legend>Quản lý và phạm vi phân bổ</legend>
   <FormField label="Vườn"><Combobox v-model="form.lotus_farm" :options="options('farms','farm_name')" label="Vườn tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Lô"><Combobox v-model="form.lotus_farm_block" :options="options('blocks','block_code',r=>!form.lotus_farm||r.farm===form.lotus_farm)" label="Lô tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Vụ"><Combobox v-model="form.lotus_crop_cycle" :options="options('cycles')" label="Vụ tài sản" :disabled="!!form.name"/></FormField>
   <FormField label="Công việc"><Combobox v-model="form.lotus_work_type" :options="options('work_types','work_name')" label="Công việc tài sản" :disabled="!!form.name"/></FormField>
   <p class="fin-assets__hint">Tỷ lệ và tài khoản phân bổ được thiết lập theo tháng sau khi hồ sơ được duyệt.</p>
   </fieldset>
   <div class="fin-assets__footer"><Button type="button" variant="outline" @click="editor=''">Đóng</Button><Button type="submit" :disabled="saving">Lưu chờ duyệt</Button></div>
  </form>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='operation'" :title="'Nghiệp vụ · '+(selected?.asset_name||'')" width="800px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}">
  <form class="fin-assets__form" @submit.prevent="saveOperation"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p>
   <FormField label="Nghiệp vụ"><Select v-model="form.kind" aria-label="Nghiệp vụ tài sản"><option v-for="[value,label] in kinds" :key="value" :value="value">{{label}}</option></Select></FormField>
   <FormField label="Ngày nghiệp vụ" required><DatePicker v-model="form.posting_date" label="Ngày nghiệp vụ tài sản"/></FormField>
   <template v-if="form.kind==='Move'"><FormField label="Vị trí nhận"><Combobox v-model="form.location" :options="options('locations','location_name')" label="Vị trí nhận tài sản"/></FormField><FormField label="Người nhận"><Combobox v-model="form.custodian" :options="options('employees','employee_name')" label="Người nhận tài sản"/></FormField><FormField label="Vườn nhận"><Combobox v-model="form.lotus_farm" :options="options('farms','farm_name')" label="Vườn nhận"/></FormField><FormField label="Lô nhận"><Combobox v-model="form.lotus_farm_block" :options="options('blocks','block_code',r=>!form.lotus_farm||r.farm===form.lotus_farm)" label="Lô nhận"/></FormField><FormField label="Vụ nhận"><Combobox v-model="form.lotus_crop_cycle" :options="options('cycles')" label="Vụ nhận"/></FormField><FormField label="Công việc"><Combobox v-model="form.lotus_work_type" :options="options('work_types','work_name')" label="Công việc nhận"/></FormField></template>
   <template v-if="['Repair','Upgrade','Sell'].includes(form.kind)"><FormField :label="form.kind==='Sell'?'Giá bán chưa thuế (đ)':'Chi phí (đ)'" required><MoneyInput v-model="form.amount" aria-label="Số tiền nghiệp vụ tài sản"/></FormField></template>
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
 <WorkspaceModal :model-value="editor==='detail'" :title="selected?.asset_name||'Tài sản'" width="1000px" @update:model-value="v=>{if(!v)editor=''}">
  <template v-if="schedule">
   <nav class="fin-assets__nav" aria-label="Chi tiết tài sản"><Button v-for="[key,label] in [['profile','Hồ sơ'],['schedule','Lịch khấu hao'],['history','Lịch sử biến động'],['documents','Chứng từ']]" :key="key" variant="ghost" :aria-current="detailTab===key?'page':undefined" :class="{'is-active':detailTab===key}" @click="detailTab=key">{{label}}</Button></nav>
   <template v-if="detailTab==='profile'">
    <dl class="fin-assets__summary"><template v-for="[key,label] in [['lotus_asset_code','Mã tài sản'],['asset_name','Tên tài sản'],['asset_category','Nhóm tài sản'],['lotus_serial_no','Serial'],['location','Vị trí'],['custodian','Người quản lý'],['purchase_date','Ngày mua'],['available_for_use_date','Ngày sử dụng'],['lotus_farm','Vườn'],['lotus_farm_block','Lô']]" :key="key"><dt>{{label}}</dt><dd>{{key==='location'?locationLabel(schedule.asset[key]):key==='lotus_farm'?farmLabel(schedule.asset[key]):key==='lotus_farm_block'?blockLabel(schedule.asset[key]):key.endsWith('_date')?date(schedule.asset[key]):schedule.asset[key]||'—'}}</dd></template><dt>Nguyên giá</dt><dd>{{amount(schedule.asset.total_asset_cost??schedule.asset.net_purchase_amount)}}</dd><dt>Giá trị còn lại</dt><dd>{{amount(schedule.asset.value_after_depreciation)}}</dd><dt>Trạng thái</dt><dd>{{stateLabel(assetStatus(schedule.asset))}}</dd></dl>
    <dl v-for="(book,index) in schedule.asset.finance_books||[]" :key="index" class="fin-assets__summary"><dt>Phương pháp</dt><dd>{{({'Straight Line':'Đường thẳng','Written Down Value':'Số dư giảm dần','Double Declining Balance':'Số dư giảm dần kép'})[book.depreciation_method]||book.depreciation_method}}</dd><dt>Tổng số tháng khấu hao</dt><dd>{{book.total_number_of_depreciations}}</dd><dt>Giá trị thu hồi</dt><dd>{{amount(book.expected_value_after_useful_life)}}</dd></dl>
   </template>
   <template v-if="detailTab==='schedule'"><p v-if="!schedule.schedules.length" role="status">Tài sản chưa có lịch khấu hao.</p><template v-for="book in schedule.schedules" :key="book.name"><p>{{book.finance_book||'Sổ mặc định'}} · {{book.name}}</p><DataTable :rows="book.rows" :columns="scheduleColumns" row-key="name" storage-key="fin-assets-schedule"><template #cell-journal_entry="{row}"><a v-if="row.journal_entry" :href="documentUrl({doctype:'Journal Entry',name:row.journal_entry})" target="_blank" rel="noopener">{{row.journal_entry}}</a><span v-else>Chưa ghi</span></template></DataTable></template></template>
   <DataTable v-if="detailTab==='history'" :rows="schedule.history||[]" :columns="historyColumns" row-key="name" storage-key="fin-assets-history" empty="Chưa có biến động tài sản."/>
   <div v-if="detailTab==='documents'" class="fin-assets__documents"><p v-if="!schedule.documents?.length" role="status">Chưa có chứng từ liên quan.</p><a v-for="doc in schedule.documents||[]" :key="doc.doctype+doc.name" :href="documentUrl(doc)" target="_blank" rel="noopener">{{doc.doctype}} · {{doc.name}}</a></div>
  </template>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='catalog-detail'" :title="catalogSelection?.row.asset_category_name||catalogSelection?.row.location_name||'Chi tiết danh mục'" width="760px" @update:model-value="v=>{if(!v)editor=''}">
  <template v-if="catalogSelection"><dl class="fin-assets__summary"><dt>Mã định danh</dt><dd>{{catalogSelection.row.name}}</dd><dt>Tài sản đã ghi nhận</dt><dd>{{catalogSelection.row.asset_count}}</dd><dt>Hồ sơ chờ duyệt</dt><dd>{{catalogSelection.row.pending_count}}</dd><template v-if="catalogSelection.type==='category'"><template v-for="[key,label] in categoryAccounts" :key="key"><dt>{{label}}</dt><dd>{{accountLabel(catalogSelection.row[key])}}</dd></template><dt>Khấu hao</dt><dd>{{Number(catalogSelection.row.non_depreciable_category)?'Không khấu hao':'Có khấu hao'}}</dd></template></dl><p v-if="catalogSelection.type==='category'&&!catalogSelection.row.configured" role="alert" class="hr-ops-error">Chưa cấu hình đủ tài khoản cho công ty hiện tại.</p><p v-if="catalogSelection.type==='category'&&canApprove&&!catalogSelection.row.can_edit" class="fin-assets__muted">Nhóm đã có tài sản được duyệt; tạo nhóm mới nếu thay đổi chính sách tài khoản.</p><div class="fin-assets__footer"><Button variant="outline" @click="editor='';viewAssets(catalogSelection.type==='category'?'category':'location',catalogSelection.row.name)">Xem tài sản</Button><Button v-if="catalogSelection.row.can_edit" @click="catalogSelection.type==='category'?openCategory(catalogSelection.row):openLocation(catalogSelection.row)">Chỉnh sửa</Button></div></template>
 </WorkspaceModal>
 <WorkspaceModal :model-value="editor==='category'" title="Nhóm tài sản và tài khoản" width="720px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form class="fin-assets__form" @submit.prevent="saveCategory"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Tên nhóm" required><Input v-model="form.asset_category_name" :readonly="!!form.name" aria-label="Tên nhóm tài sản" required/></FormField><FormField v-for="[key,label,root] in [['fixed_asset_account','Tài khoản nguyên giá','Asset'],['accumulated_depreciation_account','Tài khoản hao mòn','Asset'],['depreciation_expense_account','Tài khoản khấu hao','Expense'],['capital_work_in_progress_account','Tài khoản mua sắm chờ ghi tăng','Asset']]" :key="key" :label="label" required><Combobox v-model="form[key]" :options="categoryAccountOptions(key)" :label="label"/></FormField><FormField label="Khấu hao"><Select v-model="form.non_depreciable_category" aria-label="Nhóm có khấu hao"><option value="0">Có khấu hao</option><option value="1">Không khấu hao</option></Select></FormField><div class="fin-assets__footer"><Button type="submit" :disabled="saving">Lưu nhóm</Button></div></form></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='location'"  :title="form.name?'Sửa tên hiển thị vị trí':'Thêm vị trí tài sản'" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form @submit.prevent="saveLocation"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Tên vị trí" required v-slot="field"><Input v-bind="field" v-model="form.location_name"/></FormField><Button type="submit" :disabled="saving">Lưu vị trí</Button></form></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='import'" title="Nhập tài sản đầu kỳ từ Excel" width="950px" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><div class="fin-assets__actions"><Button variant="outline" @click="download('import_template')">Tải mẫu</Button><FileInput accept=".xlsx" aria-label="File tài sản đầu kỳ" @change="readFile"/><Button :disabled="!importContent||busy" @click="previewImport">Xem trước</Button></div><template v-if="importPreview"><DataTable :rows="importPreview.rows" :columns="importColumns" row-key="line" storage-key="fin-assets-import"/><Button :disabled="saving||!importPreview.valid" @click="commitImport">Tạo hồ sơ chờ duyệt</Button></template></WorkspaceModal>
 <WorkspaceModal :model-value="editor==='reason'" title="Hủy / đảo nghiệp vụ tài sản" :busy="saving" @update:model-value="v=>{if(!v)editor=''}"><form @submit.prevent="cancel"><p v-if="error" class="hr-ops-error fin-assets__footer" role="alert">{{error}}</p><FormField label="Lý do" required v-slot="field"><Input v-bind="field" v-model="reason" minlength="5"/></FormField><Button type="submit" :disabled="saving||reason.trim().length<5">Xác nhận hủy / đảo</Button></form></WorkspaceModal>
 <FinanceMasterImport :model-value="!!masterImport" :kind="masterImport||'categories'" @update:model-value="v=>{if(!v)masterImport=''}" @imported="importedMasters"/>
</section>
</template>

<style>
.fin-assets{display:grid;gap:var(--lotus-space-3);min-width:0;max-width:100%}
.fin-assets__nav{display:flex;align-items:center;gap:var(--lotus-space-1);overflow-x:auto;min-width:0;border-bottom:1px solid var(--lotus-border);padding-bottom:var(--lotus-space-2)}
.fin-assets__nav>button{flex-shrink:0;white-space:nowrap}.fin-assets__nav>button.is-active{color:var(--lotus-primary-text);background:var(--lotus-primary-subtle)}
.fin-assets__count{font-size:var(--lotus-text-xs);font-variant-numeric:tabular-nums;border-radius:var(--lotus-radius-sm);padding:0 var(--lotus-space-1);background:var(--lotus-hover)}
.fin-assets__toolbar{display:flex;align-items:center;gap:var(--lotus-space-2);overflow-x:auto;white-space:nowrap}
.fin-assets__toolbar>*{flex-shrink:0}.fin-assets__toolbar>input{min-width:160px;flex:1}
.fin-assets__toolbar>select{width:auto;max-width:150px}
.fin-assets__toolbar>.lotus-combobox{width:130px}
.fin-assets__actions{display:flex;align-items:center;gap:var(--lotus-space-2);flex-wrap:wrap}
.fin-assets__form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3)}
.workspace-modal .fin-assets__form>.fin-assets__group{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3);grid-column:1/-1;border:0;padding:var(--lotus-space-3) 0;margin:0;min-width:0}
.fin-assets__group>legend{font-weight:600;font-size:var(--lotus-text-base);padding-top:var(--lotus-space-2);border-bottom:1px solid var(--lotus-border);width:100%}
.fin-assets__hint{grid-column:1/-1;color:var(--lotus-muted);font-size:var(--lotus-text-sm);margin:0}
.fin-assets__muted{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}small.fin-assets__muted{display:block}
.fin-assets__empty-note{color:var(--lotus-muted);margin:0;padding:var(--lotus-space-2) 0}
.fin-assets__status{font-size:var(--lotus-text-sm)}.fin-assets__status.is-pending{color:var(--lotus-warning)}
.fin-assets__documents{display:grid;gap:var(--lotus-space-3);padding-block:var(--lotus-space-3)}
.fin-assets__footer{grid-column:1/-1;display:flex;justify-content:flex-end;gap:var(--lotus-space-2);margin-top:var(--lotus-space-3)}
.fin-assets__summary{display:grid;grid-template-columns:minmax(100px,1fr) minmax(0,2fr);gap:var(--lotus-space-2);padding-block:var(--lotus-space-3)}.fin-assets__summary dd{margin:0;text-align:right;overflow-wrap:anywhere}
.fin-assets__activation{padding:var(--lotus-space-3);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
@media(max-width:640px){.fin-assets__form,.workspace-modal .fin-assets__form>.fin-assets__group{grid-template-columns:1fr}}
</style>

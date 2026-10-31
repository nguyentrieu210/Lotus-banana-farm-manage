<script setup>
import {computed,nextTick,reactive,ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LotusField from '../form/LotusField.vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
import StockReceiptReason from '../StockReceiptReason.vue'
import StockEvidence from './StockEvidence.vue'
import DocumentReader from '../DocumentReader.vue'
import {unitLabel} from '../../units'
import {fmt} from '../../stock-columns'
import {itemUnits,conversionFactor,stockQuantity,quantityLimit} from '../../stock-units'
// Phiếu nhập không theo đơn · xuất kho · chuyển kho · kiểm kê, saved as an ERPNext draft (lotus_farm.warehouse.create_draft).
// open(kind) starts a new draft; edit(detail) reopens a draft from the detail dialog.
// openQuick() is Mua hàng › Mua nhanh: goods already bought, reason fixed to Purchase, saved and posted to stock at once
// (create_draft post=1; stays a draft when the user may not submit). The accountant invoices it later from Hóa đơn.
const props=defineProps({company:String,warehouse:String,warehouses:{type:Array,default:()=>[]},session:Object})
const emit=defineEmits(['saved'])
const api=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const titles={receipt:'Nhập kho không theo đơn',issue:'Xuất kho',transfer:'Chuyển kho',count:'Kiểm kê kho'}
const issueModes={Manual:'Thủ công',Plan:'Theo kế hoạch đã duyệt',Request:'Theo yêu cầu đã duyệt'}
const open=ref(false),saving=ref(false),error=ref(''),reasonFields=ref(null),quick=ref(false),showCosts=ref(false)
const form=reactive({kind:'receipt',receipt_reason:'',supplier:'',count_purpose:'Stock Reconciliation',posting_date:'',source:'',target:'',notes:'',lines:[],issue_mode:'Manual',work_plan:'',receiver:'',receiver_employee:'',additional_costs:[],existing_name:'',base_modified:'',client_event_id:''})
const employees=ref([]),blockCodes=ref([]),accounts=ref([]),defaultAccount=ref(''),accountsLoading=ref(false)
const issueSources=ref([]),issueSource=ref(''),issueNote=ref(''),issueLoading=ref(false)
let issueVersion=0
const money=computed(()=>props.session?.companies?.find(c=>c.name===props.company)?.default_currency||'VND')
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:money.value})
const warehouseOptions=computed(()=>props.warehouses.map(w=>({value:w.name,label:w.warehouse_name||w.name})))
const employeeOptions=computed(()=>employees.value.map(employee=>({value:employee.value,label:employee.label})))
const needsSource=computed(()=>['issue','transfer'].includes(form.kind))
const needsTarget=computed(()=>['receipt','transfer','count'].includes(form.kind))
const manual=computed(()=>form.kind!=='issue'||form.issue_mode==='Manual')
const priced=computed(()=>form.kind==='receipt'||(form.kind==='count'&&form.count_purpose==='Opening Stock'))
const basic=computed(()=>form.lines.reduce((sum,row)=>sum+Number(row.qty||0)*Number(row.rate||0),0))
const charges=computed(()=>form.additional_costs.reduce((sum,row)=>sum+Number(row.amount||0),0))
const title=computed(()=>(form.existing_name?'Sửa phiếu nháp · ':'')+(quick.value?'Mua nhanh':titles[form.kind]))

async function searchItems(search){
 const result=await api('overview',{company:props.company,warehouse:form.kind==='count'?form.target:form.source||form.target||props.warehouse,search})
 return result.items.map(item=>({value:item.name,label:item.item_name,uom:item.stock_uom,uoms:item.uoms,pack_uom:item.pack_uom,pack_factor:item.pack_factor,actual_qty:item.actual_qty}))
}
function selectItem(row,option){
 Object.assign(row,{item_name:option.label,uom:option.uom,stock_uom:option.uom,uoms:option.uoms||[],pack_uom:option.pack_uom||'',pack_factor:Number(option.pack_factor)||0,actual_qty:option.actual_qty})
 // Kiểm kê starts from the book quantity of the counted warehouse.
 if(form.kind==='count'&&form.target)row.qty=option.actual_qty??row.qty
}
function changeUnit(row,unit){
 const quantity=stockQuantity(row)
 row.uom=unit
 if(!manual.value&&Number.isFinite(quantity))row.qty=quantity/conversionFactor(row)
}
const lineColumns=computed(()=>{
 const count=form.kind==='count',issue=form.kind==='issue'
 const cols=[{field:'item',label:'Vật tư',type:'combobox',fetchOptions:searchItems,displayValue:r=>r.item_name||'',required:true,readonly:()=>!manual.value,onSelect:selectItem,props:{hideValues:true,placeholder:'Chọn vật tư…'},width:'minmax(220px,2.2fr)'},
  {field:'qty',label:count?'Tồn thực đếm':'Số lượng',type:'number',required:true,width:'minmax(110px,1fr)',
   props:r=>({min:count||!manual.value?0:0.000001,max:!manual.value?quantityLimit(r):undefined}),
   hint:r=>['receipt','issue'].includes(form.kind)&&r.uom&&r.stock_uom&&r.uom!==r.stock_uom?'= '+fmt(stockQuantity(r))+' '+unitLabel(r.stock_uom):unitLabel(r.uom||r.stock_uom)||''}]
 if(form.kind==='receipt'||issue)cols.push({field:'uom',label:issue?'Đơn vị xuất':'Đơn vị nhập hàng',type:'select',required:true,width:'minmax(150px,1fr)',options:row=>itemUnits(row).map(u=>({value:u.uom,label:unitLabel(u.uom)+(u.uom!==row.stock_uom?' (1 = '+fmt(u.conversion_factor)+' '+unitLabel(row.stock_uom)+')':'')})),props:{emptyOption:null}})
 if(priced.value)cols.push({field:'rate',label:'Đơn giá ('+money.value+')',type:'money',required:true,width:'minmax(130px,1fr)',props:{min:0},hint:r=>'Thành tiền '+cash(Number(r.qty||0)*Number(r.rate||0))})
 if(issue||(form.kind==='receipt'&&form.receipt_reason==='Recovery'))cols.push({field:'area',label:issue?'Khu vực / lô sử dụng':'Lô thu hồi về',type:'combobox',options:blockCodes.value.map(b=>({value:b.code,label:b.label||b.code})),required:true,width:'minmax(160px,1.4fr)',readonly:r=>!manual.value&&r.fixed_area,props:{allowCustom:true,placeholder:'VD: A-1 / thửa 2'},
  hint:r=>manual.value?'Bắt đầu bằng mã lô để chi phí vào đúng lô.':'Duyệt '+fmt(r.required_qty)+' · Đã cấp/giữ '+fmt(r.allocated_qty)+' · Còn '+fmt(r.remaining_qty)+' '+unitLabel(r.stock_uom||r.uom)})
 return cols
})
const costColumns=computed(()=>[{field:'description',label:'Khoản chi phí',required:true,props:{maxlength:140,placeholder:'Vận chuyển, bốc xếp…'},width:'minmax(180px,1.6fr)'},{field:'amount',label:'Số tiền ('+money.value+')',type:'money',required:true,props:{min:0.000001},width:'minmax(140px,1fr)'},{field:'expense_account',label:'Tài khoản chi phí',type:'select',required:true,options:accounts.value.map(a=>({value:a.name,label:a.account_name})),width:'minmax(180px,1.4fr)'}])
const newLine=()=>({item:'',qty:form.kind==='count'?0:1,area:'',rate:0})

watch(()=>[form.kind,form.source,open.value],async([kind,source,visible])=>{if(!visible||kind!=='issue')return;try{blockCodes.value=await call('lotus_farm.finance.stock.block_codes',{warehouse:source||undefined})}catch{blockCodes.value=[]}})
async function loadAccounts(){accountsLoading.value=true;try{const result=await api('receipt_accounts',{company:props.company});accounts.value=result.accounts;defaultAccount.value=result.default_account||''}catch(e){error.value=e.message}finally{accountsLoading.value=false}}
async function changeIssueMode(mode){
 const version=++issueVersion
 Object.assign(form,{issue_mode:mode,work_plan:'',lines:mode==='Manual'?[newLine()]:[]});issueSource.value='';issueSources.value=[];issueNote.value='';error.value=''
 issueLoading.value=mode!=='Manual';if(mode==='Manual')return
 try{const result=await api('issue_sources',{company:props.company,mode});if(version===issueVersion){issueSources.value=result.rows;issueNote.value=result.note}}
 catch(e){if(version===issueVersion)error.value=e.message}finally{if(version===issueVersion)issueLoading.value=false}
}
async function selectIssueSource(name){
 const version=++issueVersion;issueSource.value=name;form.lines=[];form.work_plan=form.issue_mode==='Plan'?name:''
 if(!name)return
 issueLoading.value=true;error.value=''
 try{const result=await api('issue_lines',{company:props.company,mode:form.issue_mode,name});if(version===issueVersion){form.lines=result.rows.map(r=>({...r,qty:r.remaining_qty,fixed_area:!!r.area}));issueNote.value=result.note}}
 catch(e){if(version===issueVersion)error.value=e.message}finally{if(version===issueVersion)issueLoading.value=false}
}
const evidence=ref(null),pendingFiles=ref([]),aiNote=ref('')
// AI-read delivery note / invoice: fill supplier and lines (item, quantity, unit, price); the read file is kept as evidence.
async function applyDocument(result,stored){
 if(result.supplier.match)form.supplier=result.supplier.match.name
 if(!form.receipt_reason&&(result.supplier.match||result.supplier.text))form.receipt_reason='Purchase'
 const rows=[]
 for(const line of result.lines.filter(l=>l.item)){
  const option=(await searchItems(line.item.label)).find(o=>o.value===line.item.code)
  if(!option)continue
  const row={...newLine(),item:option.value};selectItem(row,option)
  row.qty=line.qty||1
  if(line.uom&&line.uom===option.pack_uom)row.uom=option.pack_uom
  if(line.rate!=null)row.rate=line.rate
  rows.push(row)
 }
 if(rows.length)form.lines=[...form.lines.filter(r=>r.item),...rows]
 const doc=result.document
 if(!form.notes&&(doc.number||result.supplier.text))form.notes=['Theo chứng từ',doc.number&&'số '+doc.number,doc.date&&'ngày '+doc.date.split('-').reverse().join('/'),result.supplier.text&&'của '+result.supplier.text].filter(Boolean).join(' ')
 pendingFiles.value=[...pendingFiles.value,{file_url:stored.file_url,file_name:stored.file_name}]
}
async function start(kind){
 pendingFiles.value=[]
 issueVersion++;error.value='';issueSource.value='';issueSources.value=[];issueNote.value='';issueLoading.value=false
 const first=props.warehouse||props.warehouses[0]?.name||''
 Object.assign(form,{kind,client_event_id:crypto.randomUUID(),receipt_reason:'',supplier:'',issue_mode:'Manual',work_plan:'',receiver:'',receiver_employee:'',count_purpose:'Stock Reconciliation',posting_date:props.session?.today||'',source:first,target:kind==='transfer'?'':first,notes:'',existing_name:'',base_modified:'',additional_costs:[],lines:[newLine()]})
 if(kind==='issue')employees.value=await call('lotus_farm.warehouse_masters.employee_choices',{company:props.company})
 open.value=true
 if(kind==='receipt')await loadAccounts()
}
async function openNew(kind){quick.value=false;showCosts.value=true;try{await start(kind)}catch(e){error.value=e.message;open.value=true}}
async function openQuick(){
 quick.value=true;showCosts.value=false
 try{await start('receipt');form.receipt_reason='Purchase'}catch(e){error.value=e.message;open.value=true}
}
async function edit(current){
 const kind={'Material Receipt':'receipt','Material Issue':'issue','Material Transfer':'transfer'}[current.kind]||'count'
 await openNew(kind);await nextTick()
 Object.assign(form,{receipt_reason:current.receipt_reason||'',supplier:current.supplier||'',existing_name:current.name,base_modified:current.modified,posting_date:current.posting_date,count_purpose:current.kind,source:current.items[0]?.source||'',target:current.items[0]?.target||'',notes:current.notes||'',receiver:current.receiver||'',receiver_employee:current.receiver_employee||'',issue_mode:current.issue_mode||'Manual',additional_costs:(current.additional_costs||[]).map(row=>({...row})),lines:current.items.map(row=>({...row,rate:row.rate||0}))})
}
async function save(){
 if(saving.value)return
 saving.value=true;error.value=''
 try{
  if(form.kind==='receipt'){const message=await reasonFields.value.validate(form.lines);if(message)throw new Error(message)}
  const lines=manual.value?form.lines:form.lines.filter(r=>Number(r.qty)>0)
  if(!lines.length)throw new Error('Chọn ít nhất một dòng vật tư có số lượng cấp lớn hơn 0.')
  const result=await api('create_draft',{company:props.company,...form,lines,post:quick.value&&!form.existing_name?1:0},true)
  // Evidence uploads once the draft exists. If it fails the draft is still saved; the detail view opens so files can be added again.
  let warning=''
  try{await evidence.value?.flush(result.doctype,result.name)}catch(e){warning='Chưa gắn được chứng từ: '+e.message+'. Thêm lại ở mục chứng từ của phiếu.'}
  open.value=false;emit('saved',{...result,form_kind:form.kind,quick:quick.value,warning})
 }catch(e){error.value=e.message}finally{saving.value=false}
}
defineExpose({open:openNew,openQuick,edit,hasChanges:()=>open.value,discardChanges:()=>{open.value=false}})
</script>

<template>
 <ModalForm v-model="open" :title="title" :busy="saving" :error="error" width="1080px" :submit-label="form.existing_name?'Lưu thay đổi':quick?'Lưu & nhập kho':'Lưu phiếu nháp'" :submit-disabled="issueLoading||!form.lines.length" @submit="save">
  <p v-if="quick" class="lotus-modal-form__description">Hàng đã mua và đã về: chụp hoặc chọn hóa đơn để AI điền sẵn, kiểm tra nhà cung cấp, số lượng, giá rồi bấm <b>Lưu &amp; nhập kho</b>. Kế toán lập hóa đơn và công nợ từ phiếu này sau.</p>
  <p v-else-if="form.kind==='receipt'" class="lotus-modal-form__description">Chọn kho nhận, vật tư và số lượng thực nhận. Có thể nhập đơn giá theo kg, bao hoặc can nếu đã khai báo quy đổi.</p>
  <FormSection title="Thông tin phiếu">
   <DocumentReader v-if="form.kind==='receipt'&&manual" :camera="quick" :disabled="saving" label="Đọc phiếu giao hàng / hóa đơn bằng AI" @read="applyDocument"/>
   <StockReceiptReason v-if="form.kind==='receipt'" ref="reasonFields" :fixed="quick" v-model:reason="form.receipt_reason" v-model:supplier="form.supplier"/>
   <FormGrid :columns="3">
    <LotusField v-if="form.kind==='issue'" :model-value="form.issue_mode" label="Hình thức xuất kho" :options="Object.entries(issueModes).map(([value,label])=>({value,label}))" :searchable="false" :empty-option="null" :disabled="saving||!!form.existing_name" @update:model-value="changeIssueMode"/>
    <LotusField v-if="form.kind==='issue'&&form.issue_mode!=='Manual'" :model-value="issueSource" :label="form.issue_mode==='Plan'?'Kế hoạch đã duyệt':'Yêu cầu vật tư đã duyệt'" :options="issueSources.map(r=>({value:r.name,label:r.name+' · '+r.date}))" :searchable="false" :empty-option="issueLoading?'Đang tải…':form.issue_mode==='Plan'?'Chọn kế hoạch':'Chọn yêu cầu'" :disabled="issueLoading||saving" required @update:model-value="selectIssueSource"/>
    <LotusField v-model="form.posting_date" label="Ngày" type="date" required/>
    <LotusField v-if="form.kind==='count'" v-model="form.count_purpose" label="Loại kiểm kê" :options="[{value:'Stock Reconciliation',label:'Kiểm kê định kỳ'},{value:'Opening Stock',label:'Tồn đầu kỳ khi bắt đầu'}]" :searchable="false" :empty-option="null"/>
    <LotusField v-if="needsSource" v-model="form.source" label="Kho xuất" :options="warehouseOptions" :searchable="false" empty-option="Chọn kho" required/>
    <LotusField v-if="needsTarget" v-model="form.target" :label="form.kind==='count'?'Kho kiểm kê':'Kho nhận'" :options="warehouseOptions" :searchable="false" empty-option="Chọn kho" required/>
    <LotusField v-if="form.kind==='issue'" v-model="form.receiver_employee" label="Người nhận vật tư (HRMS)" :options="employeeOptions" empty-option="Chọn nhân viên đang làm việc" :required="!form.existing_name||!form.receiver" :hint="form.existing_name&&form.receiver&&!form.receiver_employee?'Phiếu cũ: '+form.receiver+'. Chọn một nhân viên HRMS để cập nhật.':''"/>
   </FormGrid>
   <p v-if="form.kind==='issue'&&form.issue_mode!=='Manual'&&!issueLoading&&!issueSources.length" class="lotus-form-note">{{form.issue_mode==='Plan'?'Chưa có kế hoạch đã duyệt trong công ty này.':'Chưa có yêu cầu cấp vật tư đã duyệt trong công ty này.'}}</p>
   <p v-if="issueNote" class="lotus-form-note">{{issueNote}}</p>
  </FormSection>
  <FormSection>
   <LineItemsEditor v-model="form.lines" title="Hàng hóa trên phiếu" add-label="Thêm vật tư" :columns="lineColumns" :new-row="newLine" :fixed="!manual" :empty-text="issueSource&&!issueLoading?'Nguồn này chưa có nhu cầu vật tư đã duyệt còn được cấp. Không có dòng nào để xuất.':'Chưa có dòng nào.'">
    <template #cell-uom="{row,index,column}"><LotusField :model-value="row.uom" :aria-label="column.label+' dòng '+(index+1)" :options="column.options(row)" :empty-option="null" :disabled="!row.item" required @update:model-value="unit=>changeUnit(row,unit)"/></template>
   </LineItemsEditor>
  </FormSection>
  <div v-if="form.kind==='receipt'&&!showCosts&&!form.additional_costs.length"><button type="button" class="lotus-link-button" @click="showCosts=true">+ Thêm chi phí vận chuyển, bốc xếp</button></div>
  <FormSection v-if="form.kind==='receipt'&&(showCosts||form.additional_costs.length)" title="Chi phí nhập kho" description="Phân bổ chi phí theo giá trị vật tư. Cần có đơn giá để tính phân bổ.">
   <p v-if="!accountsLoading&&!accounts.length" class="lotus-form-note">Cần quyền đọc tài khoản chi phí của công ty để thêm chi phí.</p>
   <LineItemsEditor v-model="form.additional_costs" title="Các khoản chi phí" add-label="Thêm chi phí" empty-text="Chưa có chi phí vận chuyển, bốc xếp…" :columns="costColumns" :min="0" :max="30" :readonly="accountsLoading||!accounts.length" :new-row="()=>({description:'',amount:0,expense_account:defaultAccount})"/>
   <dl class="lotus-form-totals"><div><dt>Tiền vật tư</dt><dd>{{cash(basic)}}</dd></div><div><dt>Chi phí</dt><dd>{{cash(charges)}}</dd></div><div><dt>Tổng giá trị nhập</dt><dd>{{cash(basic+charges)}}</dd></div></dl>
  </FormSection>
  <FormSection>
   <StockEvidence ref="evidence" v-model:pending="pendingFiles" :doctype="form.kind==='count'?'Stock Reconciliation':'Stock Entry'" :name="form.existing_name||''" :disabled="saving" :title="form.kind==='issue'?'Ảnh bằng chứng xuất kho':form.kind==='receipt'?'Chứng từ nhập kho (phiếu giao hàng, hóa đơn, ảnh)':'Chứng từ, ảnh bằng chứng'"/>
  </FormSection>
  <FormSection v-if="form.kind!=='count'">
   <LotusField v-model="form.notes" :label="form.kind==='issue'&&form.issue_mode==='Manual'?'Lý do xuất thủ công':'Ghi chú'" type="textarea" maxlength="2000" :required="form.kind==='issue'&&form.issue_mode==='Manual'" placeholder="Mục đích cấp vật tư…"/>
  </FormSection>
 </ModalForm>
</template>

<style>
.lotus-link-button{padding:0;border:0;background:none;color:var(--lotus-primary);font:inherit;font-size:var(--lotus-text-sm);font-weight:600;cursor:pointer}
.lotus-link-button:hover{text-decoration:underline}
.lotus-form-note{margin:0;color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-form-totals{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px 24px;margin:0}
.lotus-form-totals div{display:grid;gap:2px;text-align:right}
.lotus-form-totals dt{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-form-totals dd{margin:0;font-weight:600;font-variant-numeric:tabular-nums}
</style>

<script setup>
import {computed,onUnmounted,reactive,ref,watch} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import ErpFields from './ErpFields.vue'
import {erp,erpSchema,erpFileUrl,newClientKey,setPendingDocument,takePendingDocument} from '../../erp-api'
import {docstatusLabel,layout,required,visible} from '../../erp-meta'
import {systemLabel} from '../../system-translations.js'
// One ERP document: native metadata, permissions, workflow and controllers on the server (lotus_farm.erp_workbench).
// Save / submit / cancel go through one idempotent action (client key); "Tạo tiếp" uses the native mappers.
const props=defineProps({doctype:{type:String,required:true},name:String,label:String,company:String,currency:String,confirm:{type:Function,required:true},modal:Boolean})
const emit=defineEmits(['saved','open-new','back','dirty','title'])
// Documents whose rows ERPNext prices from the item (get_item_details) and whose totals/taxes it recomputes.
const ITEM_TYPES=['Purchase Order','Purchase Receipt','Purchase Invoice','Supplier Quotation','Sales Order','Delivery Note','Sales Invoice','Quotation','Material Request','Stock Entry','Stock Reconciliation']
const PREVIEW_TYPES=['Purchase Order','Purchase Receipt','Purchase Invoice','Supplier Quotation','Sales Order','Delivery Note','Sales Invoice','Quotation']
const schema=ref(null),loaded=ref(null),doc=ref(null),busy=ref(false),error=ref(''),notice=ref('')
let clientKey=newClientKey(),snapshot='',loadVersion=0
const snap=value=>JSON.stringify(value)
const dirty=computed(()=>!!doc.value&&snap(doc.value)!==snapshot)
watch(dirty,value=>emit('dirty',value))
function adopt(result){
 loaded.value=result
 doc.value=reactive(JSON.parse(JSON.stringify(result.doc)))
 for(const table of Object.values(schema.value?.tables||{}))for(const f of schema.value.fields.filter(x=>x.options===table.doctype))for(const row of doc.value[f.fieldname]||[])row._key??=row.name||crypto.randomUUID()
 snapshot=snap(doc.value)  // a mapped / amended document is marked unsaved by load()
}
async function load(){
 const version=++loadVersion;error.value='';notice.value='';busy.value=true
 try{
  const meta=await erpSchema(props.doctype)
  const pending=props.name?null:takePendingDocument(props.doctype)
  const result=pending||await erp('document',{doctype:props.doctype,name:props.name||undefined,company:props.company})
  if(version!==loadVersion)return
  schema.value=meta;adopt(result)
  if(pending)snapshot=''
  clientKey=newClientKey()
 }catch(e){if(version===loadVersion)error.value='Không mở được chứng từ: '+e.message}
 finally{if(version===loadVersion)busy.value=false}
}
watch(()=>[props.doctype,props.name],load,{immediate:true})

const permissions=computed(()=>loaded.value?.permissions||{})
const isNew=computed(()=>!!loaded.value?.is_new)
const docstatus=computed(()=>Number(doc.value?.docstatus||0))
const canWrite=computed(()=>docstatus.value===0?!!(isNew.value?permissions.value.create:permissions.value.write):docstatus.value===1)
const locked=computed(()=>docstatus.value>0)
const title=computed(()=>{const d=doc.value;if(!d)return props.label||props.doctype;const t=schema.value?.title_field&&d[schema.value.title_field];return isNew.value?'Mới · '+(props.label||props.doctype):(t&&t!==d.name?t+' · '+d.name:d.name)})
// In a modal the dialog header shows the title; keep it in step with the document.
watch(()=>title.value,value=>emit('title',value),{immediate:true})
const statusText=computed(()=>{const d=doc.value;if(!d)return '';const s=d.status||d.workflow_state;return [schema.value?.is_submittable?docstatusLabel(docstatus.value):'',s?systemLabel(s):''].filter((v,i,a)=>v&&a.indexOf(v)===i).join(' · ')})

// Required fields left empty (visible ones only), checked before the server does.
function missing(){
 const out=[]
 const scan=(fields,record,parent,prefix)=>{for(const f of fields){if(['Section Break','Column Break','Tab Break'].includes(f.fieldtype))continue
  if(!visible(f,record,parent))continue
  if(['Table','Table MultiSelect'].includes(f.fieldtype)){const child=schema.value.tables[f.options];(record[f.fieldname]||[]).forEach((row,i)=>child&&scan(child.fields,row,record,f.label+' dòng '+(i+1)+': '));if(f.reqd&&!(record[f.fieldname]||[]).length)out.push(prefix+f.label);continue}
  if(!f.read_only&&required(f,record,parent)&&(record[f.fieldname]==null||record[f.fieldname]===''))out.push(prefix+f.label)}}
 scan(schema.value.fields,doc.value,null,'')
 return out
}
async function run(action,extra={}){
 if(busy.value)return
 if(['save','submit'].includes(action)){const gaps=missing();if(gaps.length){error.value='Cần nhập: '+gaps.slice(0,8).join(', ')+(gaps.length>8?'…':'');return}}
 if(action==='submit'&&!await props.confirm('Ghi sổ '+(props.label||props.doctype)+'? Sau khi ghi sổ, chứng từ chỉ sửa được bằng cách hủy rồi sửa đổi.','Ghi sổ chứng từ'))return
 if(action==='cancel'&&!await props.confirm('Hủy chứng từ '+doc.value.name+'? Sổ kho / sổ cái của chứng từ sẽ được đảo lại.','Hủy chứng từ'))return
 busy.value=true;error.value='';notice.value=''
 try{
  const result=await erp('action',{doctype:props.doctype,action,client_key:clientKey,values:doc.value,name:isNew.value?null:doc.value.name,modified:isNew.value?null:doc.value.modified,company:props.company,...extra},true)
  const wasNew=isNew.value
  adopt(result);clientKey=newClientKey()
  notice.value={save:'Đã lưu.',submit:'Đã ghi sổ.',cancel:'Đã hủy chứng từ.',workflow:'Đã chuyển bước duyệt.'}[action]
  emit('saved',{name:result.doc.name,created:wasNew})
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function amend(){
 busy.value=true;error.value=''
 try{const result=await erp('amend',{doctype:props.doctype,name:doc.value.name,modified:doc.value.modified,company:props.company},true);setPendingDocument(result);emit('open-new',props.doctype)}
 catch(e){error.value=e.message}finally{busy.value=false}
}
async function next(action){
 if(dirty.value&&!await props.confirm('Có thay đổi chưa lưu. Bỏ thay đổi để tạo chứng từ tiếp theo?','Tạo tiếp'))return
 busy.value=true;error.value=''
 try{const result=await erp('map_document',{doctype:props.doctype,name:doc.value.name,target:action.target,company:props.company},true);result.mapped=true;setPendingDocument(result);emit('open-new',result.doc.doctype)}
 catch(e){error.value=e.message}finally{busy.value=false}
}
function print(){window.open(erpFileUrl('print_document',{doctype:props.doctype,name:doc.value.name}),'_blank','noopener')}

// --- what Desk does in JavaScript, done with the native server methods -------------------------------------
const childFields=table=>new Set((schema.value.tables[table]?.fields||[]).map(f=>f.fieldname))
const headerFields=computed(()=>new Set((schema.value?.fields||[]).map(f=>f.fieldname)))
function assign(target,values,allowed){for(const [k,v] of Object.entries(values||{}))if(allowed.has(k)&&v!==undefined&&!(Array.isArray(v)))target[k]=v}
async function linkSelected({field,value,row,childtype}){
 if(!value)return
 const target=row||doc.value,allowed=row?childFields(childtype):headerFields.value
 try{
  if(row&&field.fieldname==='item_code'&&ITEM_TYPES.includes(props.doctype)){
   const header=Object.fromEntries(Object.entries(doc.value).filter(([,v])=>v==null||typeof v!=='object'))
   const plain=Object.fromEntries(Object.entries(row).filter(([,v])=>v==null||typeof v!=='object'))
   assign(row,await erp('item_details',{doctype:props.doctype,item_code:value,company:props.company||doc.value.company,row:plain,header},true),allowed)
  }
  if(!row&&['customer','supplier'].includes(field.fieldname)&&(props.company||doc.value.company)){
   const party=await erp('party_details',{doctype:props.doctype,party_type:field.fieldname==='customer'?'Customer':'Supplier',party:value,company:props.company||doc.value.company,posting_date:doc.value.posting_date||doc.value.transaction_date,currency:doc.value.currency})
   assign(doc.value,party,headerFields.value)
  }
  assign(target,await erp('linked_values',{doctype:props.doctype,fieldname:field.fieldname,value,childtype:row?childtype:undefined}),allowed)
 }catch(e){error.value=e.message}
 schedulePreview()
}
// Totals and taxes: ERPNext's calculate_taxes_and_totals on the unsaved document (debounced), copied back field by field.
let previewTimer=null,previewVersion=0
const previewKey=computed(()=>doc.value&&PREVIEW_TYPES.includes(props.doctype)&&docstatus.value===0?snap([doc.value.items?.map(r=>[r.item_code,r.qty,r.rate,r.uom,r.discount_percentage,r.price_list_rate]),doc.value.taxes_and_charges,doc.value.taxes?.map(t=>[t.charge_type,t.rate,t.tax_amount,t.account_head]),doc.value.additional_discount_percentage,doc.value.discount_amount,doc.value.apply_discount_on]):'')
watch(previewKey,(value,old)=>{if(old&&value!==old)schedulePreview()})
function schedulePreview(){if(!PREVIEW_TYPES.includes(props.doctype)||docstatus.value!==0)return;clearTimeout(previewTimer);previewTimer=setTimeout(preview,500)}
onUnmounted(()=>clearTimeout(previewTimer))
async function preview(){
 const version=++previewVersion
 try{
  const result=await erp('preview',{doctype:props.doctype,values:doc.value,company:props.company||doc.value.company},true)
  if(version!==previewVersion||!doc.value)return
  const computedHeader=new Set(schema.value.fields.filter(f=>f.read_only||['taxes','total_taxes_and_charges','grand_total','rounded_total','net_total','total','base_grand_total','outstanding_amount','in_words'].includes(f.fieldname)).map(f=>f.fieldname))
  for(const [k,v] of Object.entries(result)){
   if(k==='taxes'&&Array.isArray(v)){doc.value.taxes=v.map(t=>({...t,_key:t.name||crypto.randomUUID()}));continue}
   if(k==='items'&&Array.isArray(v)){const readonlyRow=new Set((schema.value.tables[schema.value.fields.find(f=>f.fieldname==='items')?.options]?.fields||[]).filter(f=>f.read_only).map(f=>f.fieldname));v.forEach((row,i)=>{const mine=doc.value.items?.[i];if(mine)for(const key of readonlyRow)if(key in row)mine[key]=row[key]});continue}
   if(computedHeader.has(k)&&!Array.isArray(v))doc.value[k]=v
  }
 }catch{/* totals stay as entered; the server recomputes them on save */}
}
const tabsCount=computed(()=>schema.value?layout(schema.value.fields).length:0)
defineExpose({hasChanges:()=>dirty.value})
</script>

<template>
 <section class="erp-form" :aria-label="title" :aria-busy="busy">
  <header class="erp-form__header">
   <UiButton v-if="!modal" variant="ghost" size="sm" class="erp-form__back" aria-label="Về danh sách" title="Về danh sách" @click="emit('back')"><LotusIcon name="arrow-left"/></UiButton>
   <div class="erp-form__title"><h2 v-if="!modal">{{title}}</h2><span v-if="statusText" class="erp-form__status" :class="'erp-form__status--'+docstatus">{{statusText}}</span><span v-if="dirty" class="erp-form__dirty">Chưa lưu</span></div>
   <div v-if="doc" class="erp-form__actions" role="group" aria-label="Thao tác chứng từ">
    <UiButton v-if="docstatus===0&&canWrite" :disabled="busy" :variant="schema?.is_submittable?'outline':'default'" @click="run('save')">{{busy?'Đang lưu…':'Lưu'}}</UiButton>
    <UiButton v-if="docstatus===0&&schema?.is_submittable&&permissions.submit" :disabled="busy" @click="run('submit')">Ghi sổ</UiButton>
    <UiButton v-if="docstatus===1&&canWrite&&dirty" :disabled="busy" variant="outline" @click="run('save')">Lưu thay đổi được phép</UiButton>
    <UiButton v-for="t in loaded?.transitions||[]" :key="t.action" variant="outline" :disabled="busy||dirty" @click="run('workflow',{transition:t.action})">{{systemLabel(t.action)}}</UiButton>
    <UiButton v-for="a in loaded?.actions||[]" :key="a.target" variant="outline" :disabled="busy" @click="next(a)"><LotusIcon name="send"/>{{a.target==='Return'?a.label:a.target==='Payment Entry'?'Tạo phiếu thu/chi':'Tạo '+systemLabel(a.label)}}</UiButton>
    <UiButton v-if="docstatus===2&&permissions.amend" variant="outline" :disabled="busy" @click="amend">Sửa đổi (tạo bản mới)</UiButton>
    <UiButton v-if="!isNew&&permissions.print" variant="outline" :disabled="busy" @click="print"><LotusIcon name="printer"/>In</UiButton>
    <UiButton v-if="docstatus===1&&permissions.cancel" variant="destructive" :disabled="busy" @click="run('cancel')">Hủy chứng từ</UiButton>
   </div>
  </header>
  <p v-if="error" class="erp-form__error" role="alert">{{error}}</p>
  <p v-if="notice" class="erp-form__notice" role="status">{{notice}}</p>
  <p v-if="busy&&!doc" class="erp-form__loading" role="status">Đang mở chứng từ…</p>
  <ErpFields v-if="doc&&schema" :fields="schema.fields" :tables="schema.tables" :doc="doc" :doctype="doctype" :locked="locked" :can-write="canWrite" :company="company||doc.company" :currency="doc.currency||currency" :tabs="tabsCount>1"
    @link-select="linkSelected" @row-link-select="linkSelected"/>
 </section>
</template>

<style>
.erp-form{display:grid;gap:12px;min-width:0}
.erp-form__header{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 0;background:var(--lotus-bg,var(--lotus-surface))}
.erp-form__back svg{width:18px;height:18px}
.erp-form__title{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;flex:1;min-width:220px}
.erp-form__title h2{margin:0;font-size:var(--lotus-text-lg,1.1rem)}
.erp-form__status{padding:2px 8px;border-radius:999px;background:var(--lotus-soft);font-size:var(--lotus-text-sm)}
.erp-form__status--1{background:var(--lotus-success-soft);color:var(--lotus-success)}
.erp-form__status--2{background:var(--lotus-danger-soft);color:var(--lotus-danger)}
.erp-form__dirty{font-size:var(--lotus-text-sm);color:var(--lotus-warning-800)}
.erp-form__actions{display:flex;flex-wrap:wrap;gap:6px}
.erp-form__actions svg{width:15px;height:15px}
.erp-form__error,.erp-form__notice,.erp-form__loading{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);font-size:var(--lotus-text-sm);white-space:pre-wrap}
.erp-form__error{background:var(--lotus-danger-soft);color:var(--lotus-danger)}
.erp-form__notice{background:var(--lotus-success-soft);color:var(--lotus-success)}
.erp-form__loading{background:var(--lotus-soft);color:var(--lotus-muted)}
</style>

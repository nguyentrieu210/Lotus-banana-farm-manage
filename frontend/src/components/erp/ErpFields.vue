<script setup>
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import WorkspaceTabs from '../WorkspaceTabs.vue'
import ErpChildTable from './ErpChildTable.vue'
import {erp} from '../../erp-api'
import {upload} from '../../api'
import {layout,visible,required,readonly,control,selectOptions,display,dynamicTarget} from '../../erp-meta'
// The fields of one ERP document (or one child row) laid out like Desk: tabs → sections → columns, with
// depends_on / mandatory_depends_on / read_only_depends_on from the DocType. Link picks go to the parent form (fetch_from, party, item).
const props=defineProps({fields:{type:Array,required:true},tables:{type:Object,default:()=>({})},doc:{type:Object,required:true},
 doctype:{type:String,required:true},childtype:String,parent:Object,locked:Boolean,canWrite:Boolean,company:String,currency:String,tabs:{type:Boolean,default:true}})
const emit=defineEmits(['link-select','row-link-select'])
// Declared before the immediate tab watcher below, which calls them on setup.
const fieldShown=f=>visible(f,props.doc,props.parent)
function sectionShown(s){return visible({depends_on:s.depends_on},props.doc,props.parent)&&s.columns.some(c=>c.some(fieldShown))}
const structure=computed(()=>layout(props.fields))
const shownTabs=computed(()=>structure.value.filter(tab=>tab.sections.some(s=>sectionShown(s))))
const activeTab=ref('')
watch(shownTabs,tabs=>{if(!tabs.some(t=>t.label===activeTab.value))activeTab.value=tabs[0]?.label||''},{immediate:true})
const tabItems=computed(()=>shownTabs.value.map(t=>({id:t.label,label:t.label})))
const currentSections=computed(()=>props.tabs&&shownTabs.value.length>1?(shownTabs.value.find(t=>t.label===activeTab.value)?.sections||[]):shownTabs.value.flatMap(t=>t.sections))
const isReadonly=f=>!props.canWrite||readonly(f,props.doc,{locked:props.locked,parent:props.parent})
const isRequired=f=>!isReadonly(f)&&required(f,props.doc,props.parent)
async function linkOptions(f,search){
 const rows=await erp('link_options',{doctype:props.doctype,fieldname:f.fieldname,search,company:props.company,childtype:props.childtype,link_type:f.fieldtype==='Dynamic Link'?dynamicTarget(f,props.doc):undefined})
 return rows.map(r=>({value:r.value,label:r.label&&r.label!==r.value?r.label+' · '+r.value:r.value,hint:r.description}))
}
function setValue(f,value){props.doc[f.fieldname]=value}
function picked(f,option){emit('link-select',{field:f,value:option?.value??props.doc[f.fieldname],row:props.childtype?props.doc:null})}
const toInput=v=>v?String(v).replace(' ','T').slice(0,16):''
const fromInput=v=>v?v.replace('T',' ')+(v.length===16?':00':''):''
const uploading=ref('')
async function attach(f,event){
 const file=event?.target?.files?.[0];if(!file)return
 uploading.value=f.fieldname
 try{const stored=await upload(file,props.childtype?null:props.doctype,props.childtype||props.doc.__islocal?null:props.doc.name);props.doc[f.fieldname]=stored.file_url}
 finally{uploading.value=''}
}
</script>

<template>
 <div class="erp-fields">
  <WorkspaceTabs v-if="tabs&&tabItems.length>1" :items="tabItems" v-model="activeTab" label="Nhóm thông tin"/>
  <template v-for="(section,si) in currentSections" :key="si">
   <component :is="section.collapsible?'details':'section'" v-if="sectionShown(section)" class="erp-section" :class="{'erp-section--collapsible':section.collapsible}">
    <component :is="section.collapsible?'summary':'h3'" v-if="section.label||section.collapsible" class="erp-section__title">{{section.label||'Thông tin thêm'}}</component>
    <div class="erp-section__columns" :style="{'--erp-columns':section.columns.filter(c=>c.some(fieldShown)).length||1}">
     <div v-for="(column,ci) in section.columns.filter(c=>c.some(fieldShown))" :key="ci" class="erp-section__column">
      <template v-for="f in column" :key="f.fieldname">
       <template v-if="fieldShown(f)">
        <ErpChildTable v-if="control(f)==='table'" class="erp-field--wide" :field="f" :schema="tables[f.options]" v-model="doc[f.fieldname]" :parent="doc" :doctype="doctype"
          :locked="locked&&!f.allow_on_submit" :can-write="canWrite&&!isReadonly(f)" :company="company" :currency="currency" @link-select="e=>emit('row-link-select',{...e,table:f})"/>
        <div v-else-if="isReadonly(f)" class="erp-readonly" :class="{'erp-field--wide':control(f)==='textarea'}">
         <span class="erp-readonly__label">{{f.label}}</span>
         <a v-if="control(f)==='attach'&&doc[f.fieldname]" class="erp-readonly__value" :href="doc[f.fieldname]" target="_blank" rel="noopener">Xem tệp</a>
         <span v-else class="erp-readonly__value">{{display(doc[f.fieldname],f,doc.currency||currency)}}</span>
        </div>
        <LotusField v-else-if="control(f)==='link'" type="combobox" :label="f.label" :model-value="doc[f.fieldname]||''" :display-value="doc[f.fieldname]||''" :fetch-options="search=>linkOptions(f,search)"
          :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)" @select="option=>picked(f,option)"/>
        <LotusField v-else-if="control(f)==='select'" type="select" :label="f.label" :model-value="doc[f.fieldname]??''" :options="selectOptions(f)" :searchable="false" :empty-option="isRequired(f)?null:'—'"
          :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)"/>
        <LotusField v-else-if="control(f)==='checkbox'" type="checkbox" :label="f.label" :model-value="!!Number(doc[f.fieldname])" @update:model-value="v=>setValue(f,v?1:0)"/>
        <LotusField v-else-if="control(f)==='money'" type="money" :label="f.label" :model-value="doc[f.fieldname]" :currency="doc.currency||currency" :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)"/>
        <LotusField v-else-if="control(f)==='number'" type="number" :label="f.label" :model-value="doc[f.fieldname]" :required="isRequired(f)" :hint="f.description" step="any" @update:model-value="v=>setValue(f,v===''?null:Number(v))"/>
        <LotusField v-else-if="control(f)==='date'" type="date" :label="f.label" :model-value="doc[f.fieldname]||''" :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)"/>
        <LotusField v-else-if="control(f)==='datetime'" type="datetime-local" :label="f.label" :model-value="toInput(doc[f.fieldname])" :required="isRequired(f)" @update:model-value="v=>setValue(f,fromInput(v))"/>
        <LotusField v-else-if="control(f)==='time'" type="time" :label="f.label" :model-value="String(doc[f.fieldname]||'').slice(0,8)" :required="isRequired(f)" @update:model-value="v=>setValue(f,v)"/>
        <LotusField v-else-if="control(f)==='textarea'" type="textarea" wide :label="f.label" :model-value="doc[f.fieldname]||''" :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)"/>
        <div v-else-if="control(f)==='attach'" class="erp-attach">
         <LotusField type="file" :label="f.label" :required="isRequired(f)&&!doc[f.fieldname]" :hint="uploading===f.fieldname?'Đang tải lên…':f.description" @change="e=>attach(f,e)"/>
         <a v-if="doc[f.fieldname]" :href="doc[f.fieldname]" target="_blank" rel="noopener">Tệp hiện tại</a>
        </div>
        <LotusField v-else :label="f.label" :model-value="doc[f.fieldname]??''" :required="isRequired(f)" :hint="f.description" @update:model-value="v=>setValue(f,v)"/>
       </template>
      </template>
     </div>
    </div>
   </component>
  </template>
 </div>
</template>

<style>
.erp-fields{display:grid;gap:12px;min-width:0}
.erp-section{border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);padding:12px 14px;min-width:0}
.erp-section__title{margin:0 0 10px;font-size:var(--lotus-text-sm);font-weight:700;color:var(--lotus-text)}
.erp-section--collapsible>summary{cursor:pointer;margin:0}
.erp-section--collapsible[open]>summary{margin-bottom:10px}
.erp-section__columns{display:grid;grid-template-columns:repeat(var(--erp-columns),minmax(0,1fr));gap:10px 16px}
.erp-section__column{display:grid;gap:10px;align-content:start;min-width:0}
.erp-field--wide{grid-column:1/-1}
.erp-readonly{display:grid;gap:2px;min-width:0}
.erp-readonly__label{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.erp-readonly__value{font-weight:500;overflow-wrap:anywhere;white-space:pre-wrap}
.erp-attach{display:grid;gap:4px}
@media(max-width:900px){.erp-section__columns{grid-template-columns:minmax(0,1fr)}}
</style>

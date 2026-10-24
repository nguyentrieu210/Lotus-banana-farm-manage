<script setup>
import {computed,ref,watch} from 'vue'
import {formTabs,visibleField,requiredField,readonlyField} from '../../erp-form.js'
import WorkspaceTabs from '../WorkspaceTabs.vue'
import ErpField from './ErpField.vue'
import ErpChildTable from './ErpChildTable.vue'
const props=defineProps({schema:{type:Object,required:true},model:{type:Object,required:true},doctype:String,childtype:String,parent:Object,company:String,readonly:Boolean,child:Boolean})
const emit=defineEmits(['change','select','open-link','quick-create','error'])
const tab=ref(''),errors=ref({})
const tabs=computed(()=>formTabs(props.schema.fields).map(t=>({...t,sections:t.sections.filter(s=>!s.field.fieldname||visibleField(s.field,props.model,props.parent)).map(s=>({...s,columns:s.columns.map(c=>c.filter(f=>!['HTML','Button','Image','Heading'].includes(f.fieldtype)&&visibleField(f,props.model,props.parent)))})).filter(s=>s.columns.some(c=>c.length))})).filter(t=>t.sections.length))
watch(tabs,rows=>{if(!rows.some(t=>t.id===tab.value))tab.value=rows[0]?.id||''},{immediate:true})
function update(field,value,row=props.model,childtype=props.childtype){row[field.fieldname]=value;delete errors.value[field.fieldname];emit('change',{field,value,row,childtype})}
function validate(){errors.value={};let firstTab='';for(const t of tabs.value)for(const s of t.sections)for(const c of s.columns)for(const f of c){if(readonlyField(f,props.model,props.parent))continue;const v=props.model[f.fieldname];if(requiredField(f,props.model,props.parent)&&(v==null||v===''||Array.isArray(v)&&!v.length)){errors.value[f.fieldname]='Bắt buộc nhập '+f.label;if(!firstTab)firstTab=t.id}if(f.fieldtype==='Table'&&Array.isArray(v)){const fields=props.schema.tables?.[f.options]?.fields||[];for(let i=0;i<v.length;i++)for(const child of fields){if(visibleField(child,v[i],props.model)&&!readonlyField(child,v[i],props.model)&&requiredField(child,v[i],props.model)&&[null,undefined,''].includes(v[i][child.fieldname])){errors.value[f.fieldname]='Dòng '+(i+1)+': bắt buộc nhập '+child.label;if(!firstTab)firstTab=t.id}}}}if(firstTab)tab.value=firstTab;return !firstTab}

defineExpose({validate})
</script>
<template>
 <div class="erp-form" :class="{'erp-form--child':child}">
  <WorkspaceTabs v-if="!child&&tabs.length>1" v-model="tab" :items="tabs.map(t=>({id:t.id,label:t.label}))" label="Các phần của chứng từ"/>
  <div v-for="t in tabs" :key="t.id" v-show="child||t.id===tab" class="erp-form-tab">
   <section v-for="section in t.sections" :key="section.id" class="erp-form-section"><h3 v-if="section.label">{{section.label}}</h3><div class="erp-form-columns" :style="{'--erp-form-columns':Math.min(3,section.columns.length)}"><div v-for="(fields,i) in section.columns" :key="i" class="erp-form-column">
    <template v-for="field in fields" :key="field.fieldname">
     <ErpChildTable v-if="['Table','Table MultiSelect'].includes(field.fieldtype)" :field="field" :rows="model[field.fieldname]||[]" :schema="schema.tables?.[field.options]||{fields:[]}" :doctype="doctype||schema.doctype" :company="company" :parent="model" :readonly="readonly||readonlyField(field,model,parent)" :error="errors[field.fieldname]" @update:rows="update(field,$event)" @change="emit('change',$event)" @select="emit('select',$event)" @quick-create="emit('quick-create',$event)" @open-link="emit('open-link',$event)" @error="emit('error',$event)"/>
     <ErpField v-else :field="field" :model-value="model[field.fieldname]" :doc="model" :parent="parent" :doctype="doctype||schema.doctype" :childtype="childtype" :company="company" :readonly="readonly" :error="errors[field.fieldname]" @update:model-value="update(field,$event)" @select="emit('select',{field,row:model,childtype,option:$event})" @quick-create="emit('quick-create',{...$event,field,row:model,childtype})" @open-link="emit('open-link',$event)" @error="emit('error',$event)"/>
    </template>
   </div></div></section>
  </div>
 </div>
</template>

<script setup>
import {computed,ref} from 'vue'
import ProcurementField from '../ProcurementField.vue'
import {FormField} from '../ui/form-field'
import {Input} from '../ui/input'
import {Button} from '../ui/button'
import {DateRangePicker} from '../ui/date-picker'
import {call,upload} from '../../api'
import {requiredField,readonlyField} from '../../erp-form.js'
import {erpText,erpOption,erpValue,erpLinkLabel} from '../../erp-language'
const props=defineProps({field:{type:Object,required:true},modelValue:{default:''},doc:{type:Object,default:()=>({})},parent:Object,doctype:String,childtype:String,company:String,readonly:Boolean,compact:Boolean,report:String,error:String})
const emit=defineEmits(['update:modelValue','select','open-link','quick-create','error'])
const uploading=ref(false)
const f=computed(()=>props.field),type=computed(()=>f.value.fieldtype)
const isReadonly=computed(()=>props.readonly||readonlyField(f.value,props.doc,props.parent||props.doc))
const required=computed(()=>!isReadonly.value&&requiredField(f.value,props.doc,props.parent||props.doc))
const linkType=computed(()=>f.value.dynamic_options?props.doc[f.value.dynamic_options]:type.value==='Dynamic Link'?props.doc[f.value.options]:f.value.options)
const linked=computed(()=>['Link','Dynamic Link','MultiSelectList','Table MultiSelect'].includes(type.value))
const label=computed(()=>props.compact?undefined:erpText(f.value.label||f.value.fieldname))
const inputType=computed(()=>({Date:'date',Datetime:'datetime-local',Time:'time',Int:'number',Float:'number',Currency:'number',Percent:'number',Text:'textarea','Small Text':'textarea','Long Text':'textarea','Text Editor':'textarea',Code:'textarea'})[type.value]||'text')
const options=computed(()=>{if(!['Select','Autocomplete'].includes(type.value))return undefined;let o=f.value.options||[];if(typeof o==='string')o=o.split('\n');return Array.isArray(o)?o.map(erpOption):[]})
const rawOptions=async search=>props.report?call('lotus_farm.erp_workbench.report_link_options',{name:props.report,fieldname:f.value.fieldname,search,company:props.company,link_type:linkType.value}):call('lotus_farm.erp_workbench.link_options',{doctype:props.doctype,fieldname:f.value.fieldname,childtype:props.childtype,search,company:props.company,link_type:linkType.value})
const fetchOptions=async search=>(await rawOptions(search)).map(row=>({...row,label:erpLinkLabel(row.label||row.value,linkType.value)}))
const list=computed(()=>Array.isArray(props.modelValue)?props.modelValue:props.modelValue?[props.modelValue]:[])
function update(value){emit('update:modelValue',type.value==='Int'&&value!==''?Number(value):value)}
function selected(row){if(type.value==='MultiSelectList'){if(!list.value.includes(row.value))emit('update:modelValue',[...list.value,row.value])}else emit('select',row)}
async function attach(e){const file=e.target.files?.[0];if(!file)return;uploading.value=true;try{const root=props.parent||props.doc;const r=await upload(file,props.doctype,root.__islocal?undefined:root.name);emit('update:modelValue',r.file_url)}catch(error){emit('error',error.message)}finally{uploading.value=false}}
</script>
<template>
 <div class="erp-field" :class="{'erp-field--compact':compact}">
  <FormField v-if="type==='Check'" :label="label" :error="error"><input type="checkbox" :aria-label="erpText(f.label||f.fieldname)" :checked="!!Number(modelValue)" :disabled="isReadonly" @change="emit('update:modelValue',$event.target.checked?1:0)"></FormField>
  <FormField v-else-if="isReadonly" :label="label" :error="error"><output class="erp-read-value">{{String(erpValue(modelValue,f)??'').replace(/<[^>]+>/g,'')||'—'}}</output><Button v-if="linked&&modelValue&&type!=='MultiSelectList'" variant="link" size="sm" @click="emit('open-link',{doctype:linkType,name:modelValue})">Mở</Button></FormField>
  <template v-else-if="type==='MultiSelectList'"><ProcurementField :model-value="''" :label="label" :fetch-options="fetchOptions" :required="required&&!list.length" :error="error" :placeholder="'Thêm '+erpText(f.label||'lựa chọn')" @select="selected"/><div class="erp-selected-values"><Button v-for="value in list" :key="value" variant="outline" size="sm" :aria-label="'Bỏ '+value" @click="emit('update:modelValue',list.filter(v=>v!==value))">{{erpLinkLabel(value,linkType)}} ×</Button></div></template>
  <FormField v-else-if="['Attach','Attach Image','Signature'].includes(type)" :label="label" :required="required" :error="error"><a v-if="modelValue" :href="modelValue" target="_blank" rel="noopener">Tệp đã đính kèm</a><Input type="file" :accept="type==='Attach Image'?'image/*':undefined" :disabled="uploading" :aria-label="erpText(f.label)" @change="attach"/></FormField>
  <FormField v-else-if="type==='DateRange'" :label="label" :error="error"><DateRangePicker :from="modelValue?.[0]||''" :to="modelValue?.[1]||''" @change="emit('update:modelValue',[$event.from,$event.to])"/></FormField>
  <ProcurementField v-else :label="label" :aria-label="erpText(f.label||f.fieldname)" :model-value="modelValue??''" :type="inputType" :options="options" :fetch-options="linked?fetchOptions:undefined" :searchable="true" :required="required" :error="error" :hint="!compact&&f.description?erpText(f.description).replace(/<[^>]+>/g,''):undefined" :step="type==='Int'?1:'any'" :min="f.non_negative?0:undefined" @update:model-value="update" @select="selected"/>
  <Button v-if="linked&&f.can_create&&!isReadonly" variant="link" size="sm" @click="emit('quick-create',{doctype:linkType})">Thêm {{erpText(f.label||linkType)}}</Button>
 </div>
</template>
<style scoped>
.erp-field{min-width:0}.erp-field input[type=checkbox]{width:18px;height:18px;accent-color:var(--lotus-primary)}
.erp-read-value{display:block;min-height:34px;padding:7px 10px;background:var(--lotus-soft);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);font-size:var(--lotus-text-sm);overflow-wrap:anywhere;white-space:pre-wrap}
.erp-field--compact :deep(.lotus-field){gap:0}.erp-field--compact :deep(input),.erp-field--compact :deep(select){height:30px;font-size:var(--lotus-text-sm)}
.erp-selected-values{display:flex;flex-wrap:wrap;gap:var(--lotus-space-1);margin-top:var(--lotus-space-1)}
</style>

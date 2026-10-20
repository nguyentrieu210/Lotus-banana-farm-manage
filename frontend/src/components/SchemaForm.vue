<script setup>
import {unitLabel,unitOptions} from '../units'
import LinkPicker from './LinkPicker.vue'
import UiSelect from './ui/select/Select.vue'
import {computed,reactive} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import {Textarea as UiTextarea} from './ui/textarea'
import {FormField} from './ui/form-field'
import {DatePicker} from './ui/date-picker'
import {consoleAPI} from '../api'
import {label,stateLabel,uiFarmLabel} from '../labels'
const props=defineProps({schema:Object,model:Object,readonly:Boolean,scope:Object,child:Boolean,linkTitles:Object,linkOptions:Function})

const fields=computed(()=>props.schema.fields.filter(f=>f.fieldname!=='farm_plot'&&!['Section Break','Column Break','Tab Break','HTML','Button','Password'].includes(f.fieldtype)))
async function options(field,search=''){if(field.options==='UOM'){const rows=await consoleAPI('link_options',{doctype:'UOM',search:'',farm:props.scope?.farm,company:props.scope?.company});return unitOptions(rows,search)}return props.linkOptions?await props.linkOptions(field,search):await consoleAPI('link_options',{doctype:field.options,search,farm:props.model.farm||props.scope?.farm,company:props.scope?.company,
 context_field:field.fieldname,block:props.model.farm_block||null,cycle:props.model.crop_cycle||null,on_date:props.model.operation_date||props.model.harvest_date||props.model.posting_date||null,operation_type:props.model.operation_type||null})}
function selectLink(field,row){if(field.fieldname!=='source_cut_operation'||!row?.context)return;for(const key of ['farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch'])props.model[key]=row.context[key]||'';props.model[props.schema.doctype==='Bunch Operation'?'bunch_tag':'ribbon_color']=row.context.tag||''}
function add(field){const row={};for(const c of props.schema.tables[field.options])if(c.default!=null)row[c.fieldname]=c.default;(props.model[field.fieldname]??=[]).push(row)}
const fieldCaption=f=>uiFarmLabel(f.display_label||label(f.fieldname,f.label))
const fieldValue=f=>f.options==='UOM'?unitLabel(props.model[f.fieldname]):f.fieldtype==='Select'?stateLabel(props.model[f.fieldname]??'—'):f.fieldtype==='Check'?(Number(props.model[f.fieldname])?'Có':'Không'):(props.model[f.fieldname]??'—')
const inputType=f=>({Date:'date',Datetime:'datetime-local',Int:'number',Float:'number',Currency:'number',Percent:'number',Check:'checkbox'})[f.fieldtype]||'text'
</script>
<template>
 <div class="schema-grid" :class="{child}">
  <template v-for="field in fields" :key="field.fieldname">
   <section v-if="field.fieldtype==='Table'" class="child-table">
    <div class="section-title"><h3>{{fieldCaption(field)}}</h3><UiButton type="button" v-if="!readonly&&!field.read_only" @click="add(field)">Thêm dòng</UiButton></div>
    <div v-for="(row,index) in model[field.fieldname]||[]" :key="index" class="child-row">
     <strong>Dòng {{index+1}}</strong>
     <SchemaForm :schema="{fields:schema.tables[field.options],tables:{}}" :model="row" :scope="scope" :link-titles="linkTitles" :link-options="linkOptions" :readonly="readonly||!!field.read_only" child/>
     <UiButton type="button" v-if="!readonly&&!field.read_only" @click="model[field.fieldname].splice(index,1)">Xóa dòng</UiButton>
    </div>
    <p v-if="!(model[field.fieldname]||[]).length" class="muted">Chưa có dòng.</p>
   </section>
   <FormField v-else :class="{wide:field.fieldtype==='Code'||field.fieldtype==='Small Text'}" :label="fieldCaption(field)" :hint="field.description" :required="!!field.reqd&&!field.read_only&&!readonly" v-slot="attrs">
    <span v-if="readonly||field.read_only" :id="attrs.id" class="field-value">{{fieldValue(field)}}</span>
    <UiTextarea v-else-if="['Code','Small Text','Text','Long Text'].includes(field.fieldtype)" v-bind="attrs" v-model="model[field.fieldname]" rows="3"/>
    <UiSelect v-else-if="field.fieldtype==='Select'" v-bind="attrs" v-model="model[field.fieldname]">
     <option value="">Chọn…</option>
     <option v-for="option in (field.options||'').split('\n').filter(Boolean)" :key="option" :value="option">{{stateLabel(option)}}</option>
    </UiSelect>
    <input v-else-if="field.fieldtype==='Check'" v-bind="attrs" :checked="model[field.fieldname]===true||Number(model[field.fieldname])===1" type="checkbox" @change="model[field.fieldname]=$event.target.checked?1:0"/>
    <UiInput v-else-if="['Int','Float','Currency','Percent'].includes(field.fieldtype)" v-bind="attrs" v-model.number="model[field.fieldname]" :type="inputType(field)" :step="field.fieldtype==='Int'?'1':'any'"/>
    <LinkPicker v-else-if="field.fieldtype==='Link'" v-bind="attrs" v-model="model[field.fieldname]" :hide-values="field.options==='UOM'" :display-value="field.options==='UOM'?unitLabel(model[field.fieldname]):linkTitles?.[field.options]?.[model[field.fieldname]]" :fetch-options="search=>options(field,search)" @select="selectLink(field,$event)"/>
    <DatePicker v-else-if="field.fieldtype==='Date'" v-bind="attrs" v-model="model[field.fieldname]" :label="fieldCaption(field)"/>
    <UiInput v-else v-bind="attrs" v-model="model[field.fieldname]" :type="inputType(field)"/>
   </FormField>
  </template>
 </div>
</template>

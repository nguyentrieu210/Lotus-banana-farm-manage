<script setup>
import {computed,ref} from 'vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
import ModalForm from '../form/ModalForm.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import ErpFields from './ErpFields.vue'
import {erp} from '../../erp-api'
import {childColumns,control,readonly,required,selectOptions} from '../../erp-meta'
// A child table (items, taxes, payment schedule…): the grid shows the Desk grid columns; "Chi tiết" edits every field of a row.
const props=defineProps({field:{type:Object,required:true},schema:Object,modelValue:{type:Array,default:()=>[]},parent:{type:Object,required:true},
 doctype:{type:String,required:true},locked:Boolean,canWrite:Boolean,company:String,currency:String})
const emit=defineEmits(['update:modelValue','link-select'])
const rows=computed({get:()=>props.modelValue||[],set:value=>emit('update:modelValue',value)})
const types={link:'combobox',select:'select',checkbox:'checkbox',money:'money',number:'number',date:'date'}
const columns=computed(()=>props.schema?[...childColumns(props.schema.fields).map(f=>({
 field:f.fieldname,label:f.label,type:types[control(f)]||'text',width:control(f)==='link'?'minmax(170px,1.6fr)':'minmax(110px,1fr)',
 options:control(f)==='select'?selectOptions(f):undefined,searchable:control(f)==='select'?false:undefined,
 fetchOptions:control(f)==='link'?(search=>linkOptions(f,search)):undefined,displayValue:row=>row[f.fieldname]||'',
 required:row=>!isReadonly(f,row)&&required(f,row,props.parent),readonly:row=>isReadonly(f,row),
 onSelect:control(f)==='link'?((row,option)=>emit('link-select',{field:f,value:option?.value??row[f.fieldname],row,childtype:props.schema.doctype})):undefined
})),{field:'__detail',label:'',width:'40px'}]:[])
const isReadonly=(f,row)=>!props.canWrite||readonly(f,row,{locked:props.locked,parent:props.parent})
async function linkOptions(f,search){
 const rows=await erp('link_options',{doctype:props.doctype,fieldname:f.fieldname,search,company:props.company,childtype:props.schema.doctype})
 return rows.map(r=>({value:r.value,label:r.label&&r.label!==r.value?r.label+' · '+r.value:r.value}))
}
function newRow(){
 const row={doctype:props.schema.doctype,__islocal:1,_key:crypto.randomUUID()}
 for(const f of props.schema.fields)if(f.default!=null&&f.default!==''&&!['Section Break','Column Break','Tab Break'].includes(f.fieldtype))row[f.fieldname]=f.default
 return row
}
const detail=ref(null)
const detailOpen=computed({get:()=>!!detail.value,set:v=>{if(!v)detail.value=null}})
</script>

<template>
 <div class="erp-child">
  <p v-if="!schema" class="erp-child__missing">{{field.label}}: chưa đọc được cấu trúc bảng con.</p>
  <LineItemsEditor v-else v-model="rows" :columns="columns" :new-row="newRow" :title="field.label" :min="0" :max="500" :readonly="!canWrite" :empty-text="'Chưa có dòng '+field.label.toLowerCase()+'.'">
   <template #cell-__detail="{row,index}"><UiButton type="button" variant="ghost" size="sm" class="erp-child__detail" :aria-label="'Chi tiết dòng '+(index+1)" title="Chi tiết dòng" @click="detail=row"><LotusIcon name="more"/></UiButton></template>
  </LineItemsEditor>
  <ModalForm v-if="detail" v-model="detailOpen" :title="field.label+' · dòng '+(rows.indexOf(detail)+1)" width="900px" :readonly="true" cancel-label="Đóng">
   <ErpFields :fields="schema.fields" :doc="detail" :doctype="doctype" :childtype="schema.doctype" :parent="parent" :locked="locked" :can-write="canWrite" :company="company" :currency="currency" :tabs="false"
     @link-select="e=>emit('link-select',{...e,row:detail,childtype:schema.doctype})"/>
  </ModalForm>
 </div>
</template>

<style>
.erp-child{min-width:0}
.erp-child__missing{margin:0;color:var(--lotus-muted)}
.erp-child__detail svg{width:16px;height:16px}
</style>

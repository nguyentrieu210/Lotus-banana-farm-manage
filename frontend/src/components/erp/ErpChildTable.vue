<script setup>
import {computed,ref,watch} from 'vue'
import ErpField from './ErpField.vue'
import ErpForm from './ErpForm.vue'
import DataTable from '../DataTable.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
import {visibleField,readonlyField} from '../../erp-form.js'
const props=defineProps({field:Object,rows:{type:Array,default:()=>[]},schema:Object,doctype:String,company:String,parent:Object,readonly:Boolean,error:String})
const emit=defineEmits(['update:rows','change','select','open-link','quick-create','error'])
const editing=ref(null),modal=ref(false)
const fields=computed(()=>{const all=(props.schema?.fields||[]).filter(f=>!['Tab Break','Section Break','Column Break','HTML','Button','Image','Password'].includes(f.fieldtype)&&!f.hidden);const selected=all.filter(f=>f.in_list_view);return (selected.length?selected:all).slice(0,8)})
const rows=computed(()=>props.rows.map((r,i)=>{if(!r._erp_row_id)r._erp_row_id=r.name||crypto.randomUUID();return r}))
const columns=computed(()=>[...fields.value.map(f=>({field:f.fieldname,headerName:f.label,minWidth:['Link','Dynamic Link'].includes(f.fieldtype)?210:140})),{field:'_actions',headerName:'',minWidth:100,maxWidth:120,sortable:false}])
function update(row,field,value){row[field.fieldname]=value;emit('change',{field,value,row,childtype:props.field.options})}
function add(){const row={doctype:props.field.options,name:'new-'+crypto.randomUUID(),__islocal:1};for(const f of props.schema.fields||[]){if(f.default!=null&&f.default!=='')row[f.fieldname]=['Today','today'].includes(f.default)?(props.parent.transaction_date||props.parent.posting_date||new Date().toISOString().slice(0,10)):String(f.default).startsWith(':')?props.parent[String(f.default).slice(1).toLowerCase()]:f.default;else if(['company','schedule_date','cost_center'].includes(f.fieldname)&&props.parent[f.fieldname])row[f.fieldname]=props.parent[f.fieldname]}if(props.parent.set_warehouse)row.warehouse=props.parent.set_warehouse;if(props.parent.from_warehouse)row.s_warehouse=props.parent.from_warehouse;if(props.parent.to_warehouse)row.t_warehouse=props.parent.to_warehouse;emit('update:rows',[...props.rows,row])}
function remove(row){emit('update:rows',props.rows.filter(r=>r!==row))}
function edit(row){editing.value=row;modal.value=true}
</script>
<template>
 <section class="erp-child-table"><header><strong>{{field.label}}</strong><span>{{rows.length}} dòng</span></header><p v-if="error" role="alert" class="erp-error">{{error}}</p>
  <DataTable :rows="rows" :columns="columns" row-key="_erp_row_id" :storage-key="'erp-child-'+field.options" empty="Chưa có dòng."><template #cell="{row,column}"><div v-if="column.field==='_actions'" class="erp-row-actions"><Button variant="ghost" size="sm" :aria-label="'Sửa dòng '+(rows.indexOf(row)+1)" @click="edit(row)"><LotusIcon name="edit"/></Button><Button v-if="!readonly" variant="ghost" size="sm" :aria-label="'Xóa dòng '+(rows.indexOf(row)+1)" @click="remove(row)"><LotusIcon name="trash"/></Button></div><ErpField v-else-if="fields.find(f=>f.fieldname===column.field)" :field="fields.find(f=>f.fieldname===column.field)" :model-value="row[column.field]" :doc="row" :parent="parent" :doctype="doctype" :childtype="field.options" :company="company" :readonly="readonly" compact @update:model-value="update(row,fields.find(f=>f.fieldname===column.field),$event)" @select="emit('select',{field:fields.find(f=>f.fieldname===column.field),row,childtype:field.options,option:$event})" @quick-create="emit('quick-create',{...$event,row,field:fields.find(f=>f.fieldname===column.field),childtype:field.options})" @open-link="emit('open-link',$event)" @error="emit('error',$event)"/></template></DataTable>
  <Button v-if="!readonly" variant="outline" size="sm" @click="add">Thêm dòng</Button>
  <WorkspaceModal v-model="modal" :title="field.label+' · chi tiết dòng'" width="1100px"><ErpForm v-if="editing" :schema="schema" :model="editing" :doctype="doctype" :childtype="field.options" :parent="parent" :company="company" :readonly="readonly" child @change="emit('change',$event)" @select="emit('select',$event)" @quick-create="emit('quick-create',$event)" @open-link="emit('open-link',$event)" @error="emit('error',$event)"/></WorkspaceModal>
 </section>
</template>

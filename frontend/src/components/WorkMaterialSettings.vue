<script setup>
import LotusField from './form/LotusField.vue'
import {computed,nextTick,ref} from 'vue'
import WorkspaceModal from './WorkspaceModal.vue'
import SchemaForm from './SchemaForm.vue'
import {Button as UiButton} from './ui/button'
import {call,consoleAPI} from '../api'
import {cleanFields} from '../domain'
import {stateLabel} from '../labels'
import {unitLabel} from '../units'
const props=defineProps({work:Object,farm:String,date:String,data:Object,disabled:Boolean})
const emit=defineEmits(['saved'])
const dialog=ref(null),model=ref(null),schema=ref(null),error=ref(''),busy=ref(false)
const basisDialog=ref(null),basis=ref({}),basisError=ref(''),basisBusy=ref(false)
async function openBasis(){basis.value={basis_code:'',basis_name:'',uom:props.work.uom,active:1};basisError.value='';await nextTick();basisDialog.value.showModal()}
async function saveBasis(){basisBusy.value=true;basisError.value='';try{const saved=await consoleAPI('save',{doctype:'Norm Basis',values:basis.value},true);for(const row of model.value.lines||[])if(!row.norm_basis)row.norm_basis=saved.name;basisDialog.value.close();emit('saved')}catch(e){basisError.value=e.message}finally{basisBusy.value=false}}
const profiles=computed(()=>(props.data.norms||[]).filter(n=>n.work_type===props.work.name))
const editable=computed(()=>model.value?.approval_state!=='Approved'&&schema.value?.permissions?.[model.value?.name?'write':'create'])
const formSchema=computed(()=>schema.value?{...schema.value,fields:schema.value.fields.filter(f=>!['farm','work_type'].includes(f.fieldname)).map(f=>({...f,display_label:({profile_name:'Tên bộ định mức',lines:'Vật tư định mức'})[f.fieldname],reqd:f.reqd||(f.fieldname==='valid_to'&&model.value.approval_state==='Approved')}))}:null)
const titles=computed(()=>({'Norm Basis':Object.fromEntries((props.data.bases||[]).map(b=>[b.name,b.basis_name]))}))
async function open(name=null,defaults={}){error.value='';try{
 schema.value=await consoleAPI('schema',{doctype:'Material Norm Profile'})
 schema.value.tables['Material Norm Line']=schema.value.tables['Material Norm Line'].map(f=>({...f,default:['basis_qty','frequency','conversion_factor'].includes(f.fieldname)?1:f.default}))
 model.value=name?await consoleAPI('detail',{doctype:'Material Norm Profile',name}):{doctype:'Material Norm Profile',farm:props.farm,work_type:props.work.name,profile_name:props.work.work_name,version:1,valid_from:props.date,approval_state:'Draft',lines:[{norm_qty:null,basis_qty:1,frequency:1,conversion_factor:1}],...defaults}
 await nextTick();if(!dialog.value.open)dialog.value.showModal()
 }catch(e){error.value=e.message}}
function options(field,search){return call('lotus_farm.farm_workspace.norm_options',{farm:props.farm,doctype:field.options,search,work_type:props.work.name})}
function nextVersion(){const source=model.value;open(null,{profile_name:source.profile_name,version:Math.max(source.version,...profiles.value.filter(p=>p.profile_name===source.profile_name).map(p=>p.version))+1,lines:cleanFields(schema.value,source).lines})}
async function save(){busy.value=true;error.value='';try{const d=model.value;await consoleAPI('save',{doctype:d.doctype,name:d.name,base_modified:d.modified,values:cleanFields(schema.value,d)},true);dialog.value.close();emit('saved')}catch(e){error.value=e.message}finally{busy.value=false}}
</script>
<template>
 <section class="work-material-settings"><div class="section-title"><h3>Định mức vật tư · {{data.farm_name}}</h3><UiButton v-if="data.permissions?.['Material Norm Profile']?.create" type="button" variant="outline" :disabled="disabled||!work.name" @click="open()">＋ Thêm định mức vật tư</UiButton></div>
 <p v-if="!work.name" class="farm-muted">Lưu công việc trước để cấu hình vật tư.</p><p v-else-if="!profiles.length" class="farm-muted">Công việc này chưa có định mức vật tư tại vườn đang chọn.</p>
 <div v-for="n in profiles" :key="n.name" class="farm-check"><span>{{n.profile_name}} · Phiên bản {{n.version}} · {{stateLabel(n.approval_state)}}<small> · {{n.valid_from}} → {{n.valid_to||'Chưa đặt ngày kết thúc'}}</small></span><UiButton type="button" variant="outline" :disabled="disabled" @click="open(n.name)">{{n.approval_state==='Approved'?'Xem / tạo phiên bản':'Cấu hình vật tư'}}</UiButton></div>
 <p v-if="error&&!dialog?.open" class="stock-error" role="alert">{{error}}</p>
 </section>
 <Teleport to="body"><WorkspaceModal title="Định mức vật tư của công việc" ref="dialog" class="farm-editor" aria-label="Định mức vật tư của công việc" @cancel="busy&&$event.preventDefault()"><form v-if="model&&schema" @submit.prevent="save"><p v-if="error" class="stock-error" role="alert">{{error}}</p><p class="farm-muted">{{data.farm_name}} · Khối lượng cơ sở tính theo đơn vị của công việc ({{unitLabel(work.uom)}}).</p><UiButton v-if="editable&&data.permissions?.['Norm Basis']?.create" type="button" variant="outline" :disabled="busy" @click="openBasis">＋ Tạo cơ sở định mức</UiButton><SchemaForm :schema="formSchema" :model="model" :readonly="!editable||busy" :scope="{farm,company:data.company}" :link-options="options" :link-titles="titles"/><footer><UiButton v-if="!editable&&data.permissions?.['Material Norm Profile']?.create" type="button" variant="outline" @click="nextVersion">Tạo phiên bản mới</UiButton><UiButton type="button" variant="outline" :disabled="busy" @click="dialog.close()">Đóng</UiButton><UiButton v-if="editable" type="submit" :disabled="busy">{{busy?'Đang lưu…':'Lưu định mức vật tư'}}</UiButton></footer></form></WorkspaceModal>
 <WorkspaceModal title="Tạo cơ sở định mức" ref="basisDialog" class="farm-editor" aria-label="Tạo cơ sở định mức" @cancel="basisBusy&&$event.preventDefault()"><form @submit.prevent="saveBasis"><p v-if="basisError" class="stock-error" role="alert">{{basisError}}</p><div class="schema-grid"><LotusField label="Mã cơ sở định mức" v-model="basis.basis_code" required :disabled="basisBusy" maxlength="140"/><LotusField label="Tên cơ sở định mức" v-model="basis.basis_name" required :disabled="basisBusy" maxlength="140"/><label>Đơn vị<span class="field-value">{{unitLabel(work.uom)}}</span></label></div><footer><UiButton type="button" variant="outline" :disabled="basisBusy" @click="basisDialog.close()">Đóng</UiButton><UiButton type="submit" :disabled="basisBusy">Lưu cơ sở định mức</UiButton></footer></form></WorkspaceModal></Teleport>
</template>

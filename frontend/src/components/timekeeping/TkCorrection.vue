<script setup>
// Sửa công đã duyệt: replaces the approved day by an amended one with a reason (lotus_farm.shift_admin.correct_attendance).
import {computed,reactive,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import UiSelect from '../ui/select/Select.vue'
import {Textarea as UiTextarea} from '../ui/textarea'
import {FormField} from '../ui/form-field'
import {call} from '../../api'

const props=defineProps({modelValue:Boolean,company:String,row:{type:Object,default:null},shifts:{type:Array,default:()=>[]}})
const emit=defineEmits(['update:modelValue','saved'])
const form=reactive({}),saving=ref(false),error=ref('')
const local=v=>v?String(v).replace(' ','T').slice(0,16):''
const statuses=[['Present','Có mặt'],['Half Day','Nửa ngày'],['Absent','Vắng'],['Work From Home','Làm từ xa']]
const hours=computed(()=>{if(!form.in_time||!form.out_time)return null;const h=(new Date(form.out_time)-new Date(form.in_time))/36e5;return h>0?Math.round(h*100)/100:null})
watch(()=>props.modelValue,open=>{if(!open||!props.row)return;error.value='';const r=props.row
 Object.assign(form,{status:r.status,shift:r.shift||'',in_time:local(r.in_time),out_time:local(r.out_time),working_hours:Number(r.working_hours||0),overtime_hours:Number(r.overtime_hours||r.lotus_overtime_hours||0),note:r.note||r.lotus_note||'',reason:''})},{immediate:true})
async function save(){
 saving.value=true;error.value=''
 try{
  const values={status:form.status,shift:form.shift||null,working_hours:form.working_hours,overtime_hours:form.status==='Absent'?0:form.overtime_hours,note:form.note,
   in_time:form.in_time?form.in_time.replace('T',' ')+':00':null,out_time:form.out_time?form.out_time.replace('T',' ')+':00':null}
  const r=await call('lotus_farm.shift_admin.correct_attendance',{company:props.company,name:props.row.name,modified:props.row.modified,values,reason:form.reason},true)
  emit('saved',r);emit('update:modelValue',false)
 }catch(e){error.value=e.message||String(e)}finally{saving.value=false}
}
</script>

<template>
<WorkspaceModal :model-value="modelValue" :title="'Sửa công đã duyệt · '+(row?.employee_name||'')" :busy="saving" width="720px" @update:model-value="emit('update:modelValue',$event)">
 <form v-if="row" class="tk-shift-form" @submit.prevent="save">
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <p class="tk-hint">Phiếu {{row.name}} sẽ được hủy và thay bằng bản sửa (giữ lịch sử). Chỉ sửa được khi tháng chưa khóa công.</p>
  <div class="tk-pair"><FormField label="Trạng thái" v-slot="f"><UiSelect v-bind="f" v-model="form.status"><option v-for="[v,l] in statuses" :key="v" :value="v">{{l}}</option></UiSelect></FormField>
   <FormField label="Ca" v-slot="f"><UiSelect v-bind="f" v-model="form.shift"><option value="">Không theo ca</option><option v-for="s in shifts" :key="s.name" :value="s.name">{{s.name}}</option></UiSelect></FormField></div>
  <div class="tk-pair"><FormField label="Giờ vào" v-slot="f"><UiInput v-bind="f" v-model="form.in_time" type="datetime-local"/></FormField><FormField label="Giờ ra" hint="Ca đêm: chọn ngày hôm sau" v-slot="f"><UiInput v-bind="f" v-model="form.out_time" type="datetime-local"/></FormField></div>
  <div class="tk-pair"><FormField label="Giờ làm" :hint="hours!==null?'Theo giờ vào/ra: '+hours+' giờ':''" v-slot="f"><UiInput v-bind="f" v-model.number="form.working_hours" type="number" min="0" max="24" step="0.25"/></FormField>
   <FormField label="Giờ tăng ca được duyệt" v-slot="f"><UiInput v-bind="f" v-model.number="form.overtime_hours" type="number" min="0" max="16" step="0.25" :disabled="form.status==='Absent'"/></FormField></div>
  <FormField label="Ghi chú" v-slot="f"><UiInput v-bind="f" v-model="form.note" maxlength="2000"/></FormField>
  <FormField label="Lý do sửa" required hint="Lưu cùng phiếu sửa và phiếu cũ" v-slot="f"><UiTextarea v-bind="f" v-model="form.reason" minlength="5" maxlength="2000" required/></FormField>
  <div class="hr-form-footer"><UiButton type="button" variant="outline" :disabled="saving" @click="emit('update:modelValue',false)">Quay lại</UiButton><UiButton type="submit" :disabled="saving||String(form.reason||'').trim().length<5">{{saving?'Đang lưu…':'Lưu bản sửa'}}</UiButton></div>
 </form>
</WorkspaceModal>
</template>

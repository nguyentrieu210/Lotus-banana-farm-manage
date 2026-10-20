<script setup>
// Add or edit a shift (HRMS Shift Type) — Administrator, System Manager and HR Manager only (lotus_farm.shift_admin).
import {computed,reactive,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import {FormField} from '../ui/form-field'
import {call} from '../../api'

const props=defineProps({modelValue:Boolean,company:String,shift:{type:Object,default:null}})
const emit=defineEmits(['update:modelValue','saved'])
const COLORS=['#c43224','#d97706','#2563eb','#7c3aed','#0f766e','#4b5563']
const blank={name:'',start_time:'06:00',end_time:'14:00',late_grace:10,early_grace:10,check_in_before:60,check_out_after:120,half_day_hours:4,absent_hours:2,color:COLORS[0]}
const form=reactive({...blank}),saving=ref(false),error=ref('')
const editing=computed(()=>!!props.shift?.name)
const hhmm=v=>String(v||'').slice(0,5)
const overnight=computed(()=>form.start_time&&form.end_time&&form.end_time<=form.start_time)
const length=computed(()=>{if(!form.start_time||!form.end_time)return 0;const [a,b]=[form.start_time,form.end_time].map(t=>Number(t.slice(0,2))*60+Number(t.slice(3,5)));return ((b-a+1440)%1440||1440)/60})
watch(()=>props.modelValue,open=>{if(!open)return;error.value='';Object.assign(form,blank,props.shift?{...props.shift,start_time:hhmm(props.shift.start_time),end_time:hhmm(props.shift.end_time),color:props.shift.color||COLORS[0]}:{})},{immediate:true})
async function save(){
 saving.value=true;error.value=''
 try{
  const values={...form}
  const row=editing.value?await call('lotus_farm.shift_admin.update_shift',{name:props.shift.name,modified:props.shift.modified,values},true)
   :await call('lotus_farm.shift_admin.create_shift',{company:props.company,name:form.name,values},true)
  emit('saved',row);emit('update:modelValue',false)
 }catch(e){error.value=e.message||String(e)}finally{saving.value=false}
}
</script>

<template>
<WorkspaceModal :model-value="modelValue" :title="editing?'Sửa ca · '+shift.name:'Thêm ca làm việc'" :busy="saving" @update:model-value="emit('update:modelValue',$event)">
 <form class="tk-shift-form" @submit.prevent="save">
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <FormField v-if="!editing" label="Tên ca" required hint="VD: Ca 1, Ca 2, Ca 3" v-slot="f"><UiInput v-bind="f" v-model="form.name" maxlength="140" required/></FormField>
  <div class="tk-pair"><FormField label="Giờ vào" required v-slot="f"><UiInput v-bind="f" v-model="form.start_time" type="time" required/></FormField><FormField label="Giờ ra" required v-slot="f"><UiInput v-bind="f" v-model="form.end_time" type="time" required/></FormField></div>
  <p class="tk-hint">Ca dài {{length}} giờ<template v-if="overnight"> · <b>qua đêm</b>: giờ ra là sáng hôm sau, công tính cho ngày vào ca</template>.</p>
  <div class="tk-pair"><FormField label="Cho phép đi muộn (phút)" v-slot="f"><UiInput v-bind="f" v-model.number="form.late_grace" type="number" min="0" max="240"/></FormField><FormField label="Cho phép về sớm (phút)" v-slot="f"><UiInput v-bind="f" v-model.number="form.early_grace" type="number" min="0" max="240"/></FormField></div>
  <div class="tk-pair"><FormField label="Nhận lượt chấm trước ca (phút)" hint="Chấm sớm hơn mức này không tính cho ca" v-slot="f"><UiInput v-bind="f" v-model.number="form.check_in_before" type="number" min="0" max="720"/></FormField><FormField label="Nhận lượt chấm sau ca (phút)" hint="Đủ dài để tính tăng ca" v-slot="f"><UiInput v-bind="f" v-model.number="form.check_out_after" type="number" min="0" max="720"/></FormField></div>
  <div class="tk-pair"><FormField label="Dưới số giờ này tính nửa ngày" v-slot="f"><UiInput v-bind="f" v-model.number="form.half_day_hours" type="number" min="0" max="24" step="0.5"/></FormField><FormField label="Dưới số giờ này tính vắng" v-slot="f"><UiInput v-bind="f" v-model.number="form.absent_hours" type="number" min="0" max="24" step="0.5"/></FormField></div>
  <FormField label="Màu trên lịch ca"><div class="tk-swatches" role="radiogroup" aria-label="Màu ca"><button v-for="c in COLORS" :key="c" type="button" role="radio" :aria-checked="form.color===c?'true':'false'" :aria-label="'Màu '+c" :style="{'--swatch':c}" :class="{on:form.color===c}" @click="form.color=c"></button></div></FormField>
  <p v-if="editing" class="tk-banner is-info" role="note">Công đã duyệt giữ nguyên giờ ca lúc chấm, lương không đổi ngược về trước. Ngày chưa duyệt sẽ tính theo giờ mới khi bấm Lấy công từ máy.<template v-if="shift.assigned"> Ca đang xếp cho {{shift.assigned}} lượt lịch.</template></p>
  <div class="hr-form-footer"><UiButton type="button" variant="outline" :disabled="saving" @click="emit('update:modelValue',false)">Hủy</UiButton><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':editing?'Lưu thay đổi':'Tạo ca'}}</UiButton></div>
 </form>
</WorkspaceModal>
</template>

<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import DataTable from './DataTable.vue'
import LotusField from './form/LotusField.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
const props=defineProps({farm:String,blocks:{type:Array,default:()=>[]},validFrom:String,validTo:String})
const emit=defineEmits(['changed'])
const state=ref(null),busy=ref(false),error=ref(''),open=ref(false),form=ref({}),notice=ref(''),readOnly=ref(false)
const confirm=useWorkspaceConfirm()
const fields=[
 ['wave_1_share','Trổ đợt 1 (%)','%'],['wave_2_share','Trổ đợt 2 (%)','%'],['wave_3_share','Trổ đợt 3 (%)','%'],['wave_4_share','Trổ đợt 4 (%)','%'],
 ['wave_window_days','Số ngày mỗi đợt','ngày'],['wave_step_days','Khoảng cách hai đợt','ngày'],['sucker_to_flower_months','Chọn chồi → trổ','tháng'],['shoot_to_inject_days','Trổ → chích','ngày'],['inject_to_cut_days','Chích → cắt bắp','ngày'],['cut_to_harvest_days','Cắt bắp → thu','ngày'],
 ['flowering_rate','Tỷ lệ trổ / cây (%)','%'],['cut_rate_per_tree','Cắt bắp / cây (%)','%'],['cut_rate_per_flowered_bunch','Cắt bắp / buồng trổ (%)','%'],['harvest_rate','Thu / cắt bắp (%)','%'],['pack_rate','Buồng đóng gói / buồng thu (%)','%'],
 ['kg_cycle_1','Kg/buồng vụ 1','kg'],['kg_cycle_2','Kg/buồng vụ 2','kg'],['kg_cycle_3','Kg/buồng vụ 3+','kg'],['kg_per_carton','Kg/thùng','kg'],['cartons_per_container','Thùng/container 40ft','thùng'],['census_sucker_yield','Chồi hữu hiệu tham khảo (%)','%']]
const blockOptions=computed(()=>[{value:'',label:'Toàn vườn'},...props.blocks.map(b=>({value:b.name,label:b.block_name||b.block_code||b.name}))])
const dateFmt=value=>value?String(value).slice(8,10)+'/'+String(value).slice(5,7)+'/'+String(value).slice(0,4):'—'
const columns=[{field:'profile_name',headerName:'Bộ thông số'},{field:'version',headerName:'Phiên bản'},{field:'farm_block',headerName:'Lô (trống: toàn vườn)',valueFormatter:p=>p.value?(props.blocks.find(b=>b.name===p.value)?.block_name||props.blocks.find(b=>b.name===p.value)?.block_code||p.value):'Toàn vườn'},{field:'approval_state',headerName:'Trạng thái',valueFormatter:p=>p.value==='Approved'?'Đã duyệt':'Nháp'},{field:'valid_from',headerName:'Từ ngày',valueFormatter:p=>dateFmt(p.value)},{field:'valid_to',headerName:'Đến ngày',valueFormatter:p=>dateFmt(p.value)},{field:'approved_by',headerName:'Người duyệt'},{field:'actions',headerName:'Thao tác',minWidth:250,sortable:false}]
async function load(){if(!props.farm)return;busy.value=true;error.value='';try{state.value=await call('lotus_farm.forecast_profiles.list_profiles',{farm:props.farm})}catch(e){error.value=e.message}finally{busy.value=false}}
function edit(row,view=false){
 readOnly.value=view
 const values={...(state.value?.defaults||{}),...(row||{})}
 if(!row){Object.assign(values,{profile_name:'Thông số dự thu 36 tháng',farm_block:'',valid_from:props.validFrom||new Date().toLocaleDateString('en-CA'),valid_to:props.validTo||'',source_reference:'Book2 26/10/2026',notes:''})}
 for(const [key,,unit] of fields)if(unit==='%')values[key]=Math.round(Number(values[key]||0)*1000000)/10000
 if(row?.approval_state==='Approved'&&!view){delete values.name;delete values.modified}
 values.apply_sucker_yield_to_counted_trees=0;form.value=values;error.value='';open.value=true
}
async function save(){
 busy.value=true;error.value=''
 try{
  const values={...form.value};for(const [key,,unit] of fields)if(unit==='%')values[key]=Number(values[key])/100
  await call('lotus_farm.forecast_profiles.save_draft',{farm:props.farm,values,name:form.value.name||null,modified:form.value.modified||null},true)
  open.value=false;notice.value='Đã lưu bộ thông số nháp.';await load();emit('changed')
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function approve(row){
 if(!await confirm.ask('Duyệt bộ thông số '+row.profile_name+' phiên bản '+row.version+'? Sau khi duyệt, bộ này được khóa và dùng để tính dự thu, lập kế hoạch trong thời gian hiệu lực.','Duyệt bộ thông số'))return
 busy.value=true;error.value=''
 try{await call('lotus_farm.forecast_profiles.approve',{name:row.name,modified:row.modified},true);notice.value='Đã duyệt bộ thông số.';await load();emit('changed')}catch(e){error.value=e.message}finally{busy.value=false}
}
watch(()=>props.farm,()=>{open.value=false;state.value=null;load()})
onMounted(load)
</script>
<template>
 <div>
  <div class="land-actions"><UiButton v-if="state?.can_create" :disabled="busy" @click="edit()">Thêm bộ thông số</UiButton><UiButton variant="outline" :disabled="busy" @click="load">Làm mới</UiButton></div>
  <p v-if="error&&!open" role="alert" class="land-bad">{{error}}</p><p v-if="notice" role="status">{{notice}}</p>
  <DataTable :rows="state?.rows||[]" :columns="columns" :totals="false" row-key="name" storage-key="forecast-profile-management" empty="Chưa có bộ thông số. Tạo bản nháp để nhập và duyệt.">
   <template #cell-actions="{row}"><div class="forecast-profile-actions"><UiButton variant="outline" :disabled="busy" @click="edit(row,true)">Xem</UiButton><UiButton v-if="row.approval_state==='Draft'&&state?.can_write||row.approval_state==='Approved'&&state?.can_create" variant="outline" :disabled="busy" @click="edit(row)">{{row.approval_state==='Approved'?'Tạo phiên bản mới':'Sửa'}}</UiButton><UiButton v-if="row.approval_state==='Draft'&&state?.can_approve" :disabled="busy" @click="approve(row)">Duyệt</UiButton></div></template>
  </DataTable>
  <WorkspaceModal v-model="open" :title="readOnly?'Xem bộ thông số':form.name?'Sửa bộ thông số nháp':'Thêm bộ thông số'" :busy="busy">
   <form class="forecast-profile-form" @submit.prevent="save">
    <p v-if="error" role="alert" class="land-bad">{{error}}</p>
    <fieldset :disabled="readOnly" class="form-grid">
     <LotusField v-model="form.profile_name" label="Tên bộ thông số" required/>
     <LotusField v-model="form.farm_block" label="Phạm vi lô" :options="blockOptions"/>
     <LotusField v-model="form.valid_from" label="Hiệu lực từ" type="date" required/>
     <LotusField v-model="form.valid_to" label="Hiệu lực đến" type="date" hint="Bắt buộc khi duyệt."/>
     <LotusField v-model="form.source_reference" label="Nguồn thông số" required/>
     <LotusField v-model="form.notes" label="Căn cứ xác nhận kỹ thuật" type="textarea" hint="Ghi căn cứ và các giả định được chấp nhận trước khi duyệt."/>
     <LotusField v-for="[key,label,unit] in fields" :key="key" v-model="form[key]" :label="label" type="number" :min="0" :max="unit==='%'?100:undefined" :step="unit==='%'||unit==='kg'?'any':1" required/>
    </fieldset>
    <p class="land-note">Không nhân lại hệ số chồi vào số cây gốc đã chốt.</p>
    <UiButton v-if="!readOnly" type="submit" :disabled="busy">Lưu bản nháp</UiButton>
   </form>
  </WorkspaceModal>
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" @answer="confirm.finish"/>
 </div>
</template>
<style>
.forecast-profile-actions{display:inline-flex;gap:var(--lotus-space-1);align-items:center}
</style>

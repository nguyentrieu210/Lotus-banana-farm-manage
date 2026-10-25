<script setup>
import {computed,reactive,ref} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import FormGrid from '../form/FormGrid.vue'
import LotusField from '../form/LotusField.vue'
import {Button as UiButton} from '../ui/button'
import {unitLabel,stockItemUomOptions} from '../../units'
import {fmt} from '../../stock-columns'
// Thêm / sửa danh mục kho: vật tư, nhóm vật tư, kho, đơn vị tính. open(kind) creates, open(kind,name) edits.
const props=defineProps({company:String,session:Object})
const emit=defineEmits(['saved'])
const api=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const masterAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_masters.'+name,args,write)
const titles={item:'vật tư',group:'nhóm vật tư',warehouse:'kho',uom:'đơn vị tính'}
const open=ref(false),kind=ref('item'),editing=ref(null),busy=ref(false),error=ref(''),deleting=ref(false),clearDefaults=ref(false)
const catalog=ref({groups:[],uoms:[],parents:[]}),employees=ref([])
const blank={name:'',code:'',group:'',uom:'',parent:'',description:'',new_group:'',group_parent:'',minimum_stock:0,pack_uom:'',pack_factor:0,lotus_address:'',lotus_contact_employee:'',lotus_contact_name:'',lotus_contact_phone:'',lotus_receiving_hours:'',lotus_default_lead_days:0,lotus_delivery_note:'',enabled:true,must_be_whole_number:false}
const master=reactive({...blank})
const title=computed(()=>(editing.value?'Sửa ':'Thêm ')+titles[kind.value])
const readonly=computed(()=>!!editing.value&&!editing.value.can_write)
const permissions=computed(()=>props.session?.permissions||{})
const uomOptions=computed(()=>stockItemUomOptions(catalog.value.uoms,[master.uom,master.pack_uom]).map(u=>({value:u.name,label:unitLabel(u.name)})))
const packOptions=computed(()=>uomOptions.value.filter(u=>u.value!==master.uom))
const groupOptions=computed(()=>catalog.value.groups.map(g=>({value:g.name,label:g.name})))
const parentGroupOptions=computed(()=>catalog.value.groups.filter(g=>g.is_group).map(g=>({value:g.name,label:g.name})))
const parentWarehouseOptions=computed(()=>catalog.value.parents.map(w=>({value:w.name,label:w.warehouse_name})))
const employeeOptions=computed(()=>employees.value.map(employee=>({value:employee.value,label:employee.label})))
const warehouseCode=computed(()=>{const n=String(master.name||'').trim(),abbr=props.session?.companies?.find(c=>c.name===props.company)?.abbr;return n&&abbr?(n.endsWith(' - '+abbr)?n:n+' - '+abbr):n})
const packHint=computed(()=>Number(master.pack_factor)>0?'Ví dụ: 1 '+unitLabel(master.pack_uom)+' = '+fmt(master.pack_factor)+' '+unitLabel(master.uom)+'. Quy đổi theo từng vật tư.':'')
const deleteBlocked=computed(()=>kind.value==='warehouse'&&(editing.value?.default_item_count||editing.value?.stock_default)&&!clearDefaults.value)

async function show(nextKind,name=''){
 kind.value=nextKind;editing.value=null;deleting.value=false;clearDefaults.value=false;error.value='';Object.assign(master,blank)
 busy.value=true;open.value=true
 try{
  if(nextKind==='warehouse')employees.value=await masterAPI('employee_choices',{company:props.company})
  if(nextKind!=='uom'){catalog.value=await api('catalogue',{company:props.company})
   const root=catalog.value.groups.find(g=>g.is_group&&!g.parent_item_group)?.name||catalog.value.groups.find(g=>g.is_group)?.name||''
   Object.assign(master,{uom:catalog.value.uoms.find(u=>u.name==='Kg')?.name||catalog.value.uoms[0]?.name||'',parent:nextKind==='warehouse'?catalog.value.parents[0]?.name||'':root,group_parent:root})}
  if(name){const result=await masterAPI('read_master',{company:props.company,kind:nextKind,name});editing.value=result
   Object.assign(master,{name:result.name,code:result.code,group:result.group||'',uom:result.uom||'',parent:result.parent||'',description:result.description||'',minimum_stock:result.minimum_stock||0,pack_uom:result.pack_uom||'',pack_factor:result.pack_factor||0,enabled:result.enabled!==0,must_be_whole_number:!!result.must_be_whole_number,
    ...Object.fromEntries(['lotus_address','lotus_contact_employee','lotus_contact_name','lotus_contact_phone','lotus_receiving_hours','lotus_default_lead_days','lotus_delivery_note'].map(k=>[k,result[k]??blank[k]]))})}
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function save(){
 busy.value=true;error.value=''
 try{
  const values={...master}
  const result=editing.value?await masterAPI('save_master',{company:props.company,kind:kind.value,name:editing.value.id,modified:editing.value.modified,values},true):await api('create_master',{company:props.company,kind:kind.value,values},true)
  open.value=false;emit('saved',{kind:kind.value,name:result.name})
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function remove(){
 busy.value=true;error.value=''
 try{await masterAPI('delete_master',{company:props.company,kind:kind.value,name:editing.value.id,modified:editing.value.modified,clear_defaults:clearDefaults.value},true);open.value=false;emit('saved',{kind:kind.value,name:editing.value.id,deleted:true})}
 catch(e){error.value=e.message}finally{busy.value=false}
}
defineExpose({open:show,hasChanges:()=>open.value,discardChanges:()=>{open.value=false}})
</script>

<template>
 <ModalForm v-model="open" :title="title" :busy="busy" :error="error" :readonly="readonly" width="760px" :submit-label="'Lưu '+titles[kind]" @submit="save">
  <div v-if="deleting" class="lotus-delete-confirm" role="alert">
   <p>Xóa {{titles[kind]}} này? Hệ thống chỉ cho xóa khi chưa được sử dụng.</p>
   <LotusField v-if="kind==='warehouse'&&(editing?.default_item_count||editing?.stock_default)" v-model="clearDefaults" type="checkbox" :label="'Gỡ kho mặc định của '+(editing?.default_item_count||0)+' vật tư'+(editing?.stock_default?' và thiết lập kho chung':'')+' trước khi xóa'"/>
   <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="deleting=false">Giữ lại</UiButton><UiButton type="button" variant="destructive" :disabled="busy||deleteBlocked" @click="remove">Xác nhận xóa</UiButton></div>
  </div>
  <FormGrid>
   <template v-if="kind==='item'">
    <LotusField v-model="master.code" label="Mã vật tư" :readonly="!!editing||readonly" maxlength="140" placeholder="VD: PB-NPK-001" required/>
    <LotusField v-model="master.name" label="Tên vật tư" :readonly="readonly" maxlength="140" placeholder="VD: Phân NPK 16-16-8" required/>
    <LotusField v-model="master.group" label="Nhóm vật tư" :options="groupOptions" :required="!master.new_group" :disabled="!!master.new_group||readonly"/>
    <LotusField v-if="!editing&&permissions['Item Group']" v-model="master.new_group" label="Hoặc tạo nhóm mới" maxlength="140" placeholder="Để trống nếu dùng nhóm đã có"/>
    <LotusField v-model="master.uom" label="Đơn vị tồn kho gốc" :options="uomOptions" :searchable="false" :readonly="readonly" required/>
    <LotusField v-model="master.minimum_stock" :label="'Tồn tối thiểu chung toàn bộ kho ('+unitLabel(master.uom)+')'" type="number" min="0" :readonly="readonly" required hint="Áp dụng trên tổng tồn các kho của công ty, không chọn kho riêng."/>
    <LotusField v-model="master.pack_uom" label="Đơn vị đóng gói / quy đổi" :options="packOptions" :searchable="false" empty-option="Không sử dụng đơn vị phụ" :readonly="readonly"/>
    <LotusField v-if="master.pack_uom" v-model="master.pack_factor" :label="'1 '+unitLabel(master.pack_uom)+' = bao nhiêu '+unitLabel(master.uom)+'?'" type="number" min="0.000001" :readonly="readonly" required :hint="packHint"/>
    <LotusField v-model="master.description" label="Ghi chú (không bắt buộc)" type="textarea" wide maxlength="2000" :readonly="readonly" placeholder="Quy cách đóng gói, thông tin nhận biết…"/>
   </template>
   <template v-else-if="kind==='group'">
    <LotusField v-model="master.name" label="Tên nhóm vật tư" maxlength="140" placeholder="VD: Phân bón" :readonly="readonly" required/>
    <LotusField v-if="!editing&&parentGroupOptions.length>1" v-model="master.parent" label="Nhóm cha" :options="parentGroupOptions" :searchable="false" :empty-option="null" required/>
   </template>
   <template v-else-if="kind==='warehouse'">
    <LotusField v-model="master.name" label="Tên kho" maxlength="140" placeholder="VD: Kho phân bón farm" :readonly="readonly" required/>
    <LotusField :model-value="warehouseCode" label="Mã kho (tự sinh theo tên)" readonly hint="Mã theo tên kho và viết tắt công ty; khi đổi tên kho, ERPNext cập nhật liên kết liên quan."/>
    <LotusField v-if="!editing&&parentWarehouseOptions.length>1" v-model="master.parent" label="Thuộc nhóm kho" :options="parentWarehouseOptions" :searchable="false" required/>
    <LotusField v-model="master.lotus_contact_employee" label="Người phụ trách kho (nhân sự HRMS)" :options="employeeOptions" empty-option="Chưa phân công" :readonly="readonly" :hint="employees.length?'':'Chưa có nhân sự đang làm việc, cần tiếp nhận tại module Nhân sự.'"/>
    <LotusField :model-value="master.lotus_contact_phone" label="Số điện thoại người phụ trách" readonly placeholder="Tự lấy từ hồ sơ HRMS" hint="Đồng bộ theo hồ sơ nhân sự khi lưu; không nhập thủ công."/>
    <LotusField v-model="master.lotus_receiving_hours" label="Giờ nhận hàng" maxlength="140" :readonly="readonly" placeholder="Ví dụ: Thứ Hai–Thứ Bảy, 7:00–17:00"/>
    <LotusField v-model="master.lotus_default_lead_days" label="Thời gian chờ hàng mặc định (ngày)" type="number" min="0" max="365" step="1" :readonly="readonly" hint="Chỉ dùng để gợi ý, ngày giao do NCC xác nhận sẽ được ưu tiên."/>
    <LotusField v-model="master.lotus_address" label="Địa chỉ kho / điểm nhận hàng" type="textarea" wide maxlength="500" :readonly="readonly" placeholder="Địa chỉ giao hàng, xã, tỉnh, hướng dẫn đến cổng kho"/>
    <LotusField v-model="master.lotus_delivery_note" label="Ghi chú giao nhận" type="textarea" wide maxlength="500" :readonly="readonly" placeholder="Cổng giao hàng, giờ nghỉ, yêu cầu bốc dỡ…"/>
   </template>
   <template v-else>
    <LotusField v-model="master.name" label="Tên đơn vị tính" maxlength="140" :readonly="!!editing||readonly" placeholder="VD: Thùng" :hint="editing?'Tên đơn vị đã dùng trên chứng từ nên không đổi được.':''" required/>
    <LotusField v-if="editing" :model-value="unitLabel(master.code)" label="Tên hiển thị" readonly/>
    <LotusField v-model="master.must_be_whole_number" type="checkbox" label="Chỉ nhập số nguyên (bao, can, cái…)" :readonly="readonly"/>
    <LotusField v-if="editing" v-model="master.enabled" type="checkbox" label="Đang sử dụng" :readonly="readonly" hint="Bỏ chọn để ngừng dùng; không ngừng được khi còn là đơn vị gốc của vật tư đang dùng."/>
   </template>
  </FormGrid>
  <template #secondary><UiButton v-if="editing?.can_delete&&!deleting" type="button" variant="destructive" :disabled="busy" @click="deleting=true">Xóa danh mục</UiButton></template>
 </ModalForm>
</template>


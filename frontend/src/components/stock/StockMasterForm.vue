<script setup>
import {computed,reactive,ref} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
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
// Vật tư: loại hàng quyết định cách ghi sổ. VPP, sửa chữa… là "mua dùng ngay": không theo dõi tồn, hóa đơn vào chi phí 642 / 627.
const itemBlank={conversions:[],kind:'Material',asset_category:'',disabled:false,is_purchase_item:true,is_sales_item:false,has_batch_no:false,has_expiry_date:false,shelf_life_in_days:0,lead_time_days:0,min_order_qty:0,default_supplier:'',default_warehouse:''}
const itemKinds=[
 {value:'Material',label:'Vật tư (theo dõi tồn kho)',hint:'Phân bón, thuốc, bao bì… Nhập vào 152, xuất dùng thì tính vào chi phí lô / vườn.'},
 {value:'Tool',label:'Công cụ dụng cụ (theo dõi tồn kho)',hint:'Cuốc, bình phun, kéo… Nhập vào 153, xuất dùng thì phân bổ chi phí.'},
 {value:'Asset',label:'Tài sản cố định (khấu hao)',hint:'Máy móc, xe, nhà lưới… Không vào kho: hóa đơn ghi nguyên giá 211 và trích khấu hao theo nhóm tài sản.'},
 {value:'Service',label:'Mua dùng ngay – vào chi phí (VPP, dịch vụ…)',hint:'Văn phòng phẩm, sửa chữa, vận chuyển, điện nước… Không theo dõi tồn: hóa đơn vào chi phí quản lý 642, hoặc 627 khi ghi cho vườn / lô.'}]
const blank={name:'',code:'',group:'',uom:'',parent:'',description:'',new_group:'',group_parent:'',minimum_stock:0,pack_uom:'',pack_factor:0,lotus_address:'',lotus_contact_employee:'',lotus_contact_name:'',lotus_contact_phone:'',lotus_receiving_hours:'',lotus_default_lead_days:0,lotus_delivery_note:'',enabled:true,must_be_whole_number:false,is_group:false,
 ...itemBlank}
const master=reactive({...blank})
const stockItem=computed(()=>['Material','Tool'].includes(master.kind))
const codePrefix=computed(()=>({Material:'VT',Tool:'CC',Asset:'TS',Service:'DV'})[master.kind]||'VT')
const kindOptions=computed(()=>itemKinds.filter(k=>!editing.value?.used||['Material','Tool'].includes(editing.value.kind)===['Material','Tool'].includes(k.value)&&(['Material','Tool'].includes(k.value)||k.value===editing.value.kind)))
const kindHint=computed(()=>itemKinds.find(k=>k.value===master.kind)?.hint+(editing.value?.used?' Mã đã phát sinh chứng từ nên chỉ đổi được giữa vật tư và công cụ dụng cụ.':''))
const money=n=>Number(n||0).toLocaleString('vi-VN')+' đ'
const title=computed(()=>(editing.value?'Sửa ':'Thêm ')+titles[kind.value])
const readonly=computed(()=>!!editing.value&&!editing.value.can_write)
const permissions=computed(()=>props.session?.permissions||{})
const uomOptions=computed(()=>stockItemUomOptions(catalog.value.uoms,[master.uom,...(master.conversions||[]).map(r=>r.uom)]).map(u=>({value:u.name,label:unitLabel(u.name)})))
// Đơn vị quy đổi: 1 đơn vị = hệ số × đơn vị gốc (bao 50 kg, tấn 1.000 kg…). After stock movements a used unit keeps its factor.
const conversionColumns=computed(()=>[{field:'uom',label:'Đơn vị quy đổi',required:true,options:packOptions.value,searchable:true,disabled:r=>usedFactor(r),width:'minmax(160px,1fr)'},{field:'conversion_factor',label:'1 đơn vị = bao nhiêu '+unitLabel(master.uom),type:'number',required:true,props:{min:0.000001},disabled:r=>usedFactor(r),width:'minmax(160px,1fr)',hint:r=>r.uom&&Number(r.conversion_factor)>0?'1 '+unitLabel(r.uom)+' = '+fmt(r.conversion_factor)+' '+unitLabel(master.uom):''}])
const usedFactor=row=>editing.value?.has_ledger&&(editing.value.conversions||[]).some(c=>c.uom===row.uom)
const packOptions=computed(()=>uomOptions.value.filter(u=>u.value!==master.uom))
// Nhóm là cây: show the path (Vật tư nông nghiệp › Phân bón); items go in leaf groups, children in parent groups.
const groupPath=name=>{const byName=new Map(catalog.value.groups.map(g=>[g.name,g]));const parts=[];let cur=byName.get(name);while(cur&&cur.parent_item_group){parts.unshift(cur.name);cur=byName.get(cur.parent_item_group)}return parts.join(' › ')||'Tất cả nhóm hàng (cấp cao nhất)'}
const groupOptions=computed(()=>catalog.value.groups.filter(g=>!g.is_group).map(g=>({value:g.name,label:groupPath(g.name)})).sort((a,b)=>a.label.localeCompare(b.label,'vi')))
const parentGroupOptions=computed(()=>catalog.value.groups.filter(g=>g.is_group&&g.name!==editing.value?.id).map(g=>({value:g.name,label:groupPath(g.name)})).sort((a,b)=>a.label.localeCompare(b.label,'vi')))
const parentWarehouseOptions=computed(()=>catalog.value.parents.filter(w=>w.name!==editing.value?.id).map(w=>({value:w.name,label:w.name.startsWith('All Warehouses')?'Tất cả kho (cấp cao nhất)':w.warehouse_name})))
const employeeOptions=computed(()=>employees.value.map(employee=>({value:employee.value,label:employee.label})))
const warehouseCode=computed(()=>{const n=String(master.name||'').trim(),abbr=props.session?.companies?.find(c=>c.name===props.company)?.abbr;return n&&abbr?(n.endsWith(' - '+abbr)?n:n+' - '+abbr):n})
const deleteBlocked=computed(()=>kind.value==='warehouse'&&(editing.value?.default_item_count||editing.value?.stock_default)&&!clearDefaults.value)

async function show(nextKind,name='',defaults={}){
 kind.value=nextKind;editing.value=null;deleting.value=false;clearDefaults.value=false;error.value='';Object.assign(master,blank)
 busy.value=true;open.value=true
 try{
  if(nextKind==='warehouse')employees.value=await masterAPI('employee_choices',{company:props.company})
  if(nextKind!=='uom'){catalog.value=await api('catalogue',{company:props.company})
   const root=catalog.value.groups.find(g=>g.is_group&&!g.parent_item_group)?.name||catalog.value.groups.find(g=>g.is_group)?.name||''
   Object.assign(master,{uom:catalog.value.uoms.find(u=>u.name==='Kg')?.name||catalog.value.uoms[0]?.name||'',parent:defaults.parent||(nextKind==='warehouse'?catalog.value.parents[0]?.name||'':root),group_parent:root})}
  if(name){const result=await masterAPI('read_master',{company:props.company,kind:nextKind,name});editing.value=result
   if(nextKind==='item')Object.assign(master,Object.fromEntries(Object.keys(itemBlank).map(k=>[k,typeof itemBlank[k]==='boolean'?!!result[k]:result[k]??itemBlank[k]])),{conversions:(result.conversions||[]).map(r=>({...r}))})
   Object.assign(master,{is_group:!!result.is_group,name:result.name,code:result.code,group:result.group||'',uom:result.uom||'',parent:result.parent||'',description:result.description||'',minimum_stock:result.minimum_stock||0,pack_uom:result.pack_uom||'',pack_factor:result.pack_factor||0,enabled:result.enabled!==0,must_be_whole_number:!!result.must_be_whole_number,
    ...Object.fromEntries(['lotus_address','lotus_contact_employee','lotus_contact_name','lotus_contact_phone','lotus_receiving_hours','lotus_default_lead_days','lotus_delivery_note'].map(k=>[k,result[k]??blank[k]]))})}
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function save(){
 busy.value=true;error.value=''
 try{
  const values={...master}
  if(kind.value==='item'){delete values.pack_uom;delete values.pack_factor;values.conversions=(master.conversions||[]).filter(r=>r.uom)}
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
    <LotusField v-model="master.code" label="Mã vật tư" :readonly="!!editing||readonly" maxlength="140" :placeholder="editing?'':'Để trống: tự sinh '+codePrefix+'-00001…'" :hint="editing?'':'Mã tự sinh theo loại hàng khi lưu; muốn mã riêng thì gõ vào.'"/>
    <LotusField v-model="master.name" label="Tên vật tư" :readonly="readonly" maxlength="140" placeholder="VD: Phân NPK 16-16-8" required/>
    <LotusField v-model="master.group" label="Nhóm vật tư" :options="groupOptions" :required="!master.new_group" :disabled="!!master.new_group||readonly"/>
    <LotusField v-if="!editing&&permissions['Item Group']" v-model="master.new_group" label="Hoặc tạo nhóm mới" maxlength="140" placeholder="Để trống nếu dùng nhóm đã có"/>
    <LotusField v-model="master.kind" label="Loại hàng" :options="kindOptions" :searchable="false" :empty-option="null" :readonly="readonly" required :hint="kindHint" wide/>
    <LotusField v-if="master.kind==='Asset'" v-model="master.asset_category" label="Nhóm tài sản cố định" :options="(catalog.asset_categories||[]).map(c=>({value:c,label:c}))" :readonly="readonly" required hint="Nhóm tài sản quyết định tài khoản nguyên giá, hao mòn và chi phí khấu hao."/>
    <LotusField v-model="master.uom" :label="stockItem?'Đơn vị tồn kho gốc':'Đơn vị tính'" :options="uomOptions" :searchable="false" :readonly="readonly||!!editing?.has_ledger" required :hint="editing?.has_ledger?'Đã nhập / xuất theo đơn vị này nên không đổi được. Mua bán theo đơn vị khác thì thêm ở bảng quy đổi bên dưới.':editing?'Đổi được khi chưa nhập / xuất kho. Hệ số quy đổi bên dưới tính theo đơn vị gốc mới.':''"/>
    <LotusField v-if="stockItem" v-model="master.minimum_stock" :label="'Tồn tối thiểu chung toàn bộ kho ('+unitLabel(master.uom)+')'" type="number" min="0" :readonly="readonly" required hint="Áp dụng trên tổng tồn các kho của công ty, không chọn kho riêng."/>
    <LotusField v-model="master.description" label="Ghi chú (không bắt buộc)" type="textarea" wide maxlength="2000" :readonly="readonly" placeholder="Quy cách đóng gói, thông tin nhận biết…"/>
   </template>
   <template v-else-if="kind==='group'">
    <LotusField v-model="master.name" label="Tên nhóm vật tư" maxlength="140" placeholder="VD: Phân bón" :readonly="readonly" required/>
    <LotusField v-model="master.parent" label="Thuộc nhóm cha" :options="parentGroupOptions" :empty-option="null" :readonly="readonly" required :hint="editing?'Đổi để chuyển cả nhóm (và các nhóm con) sang nhánh khác.':''"/>
    <LotusField v-if="!editing" v-model="master.is_group" type="checkbox" label="Là nhóm cha" hint="Nhóm cha chỉ chứa các nhóm con (VD: Vật tư nông nghiệp › Phân bón); vật tư được xếp vào nhóm con."/>
    <p v-else-if="editing.is_group" class="lotus-form-note">Nhóm cha: {{editing.child_count}} nhóm con.</p>
    <p v-else class="lotus-form-note">{{editing.item_count}} mã vật tư trong nhóm này.</p>
   </template>
   <template v-else-if="kind==='warehouse'">
    <LotusField v-model="master.name" label="Tên kho" maxlength="140" placeholder="VD: Kho phân bón farm" :readonly="readonly" required/>
    <LotusField :model-value="warehouseCode" label="Mã kho (tự sinh theo tên)" readonly hint="Mã theo tên kho và viết tắt công ty; khi đổi tên kho, ERPNext cập nhật liên kết liên quan."/>
    <LotusField v-model="master.parent" label="Thuộc nhóm kho" :options="parentWarehouseOptions" :searchable="false" :readonly="readonly" required/>
    <LotusField v-if="!editing" v-model="master.is_group" type="checkbox" label="Là nhóm kho" hint="Nhóm kho chỉ để gom các kho (VD: Kho farm 222 › Kho phân, Kho thuốc); hàng nhập vào kho con."/>
    <template v-if="!master.is_group&&!editing?.is_group">
    <LotusField v-model="master.lotus_contact_employee" label="Người phụ trách kho (nhân sự HRMS)" :options="employeeOptions" empty-option="Chưa phân công" :readonly="readonly" :hint="employees.length?'':'Chưa có nhân sự đang làm việc, cần tiếp nhận tại module Nhân sự.'"/>
    <LotusField :model-value="master.lotus_contact_phone" label="Số điện thoại người phụ trách" readonly placeholder="Tự lấy từ hồ sơ HRMS" hint="Đồng bộ theo hồ sơ nhân sự khi lưu; không nhập thủ công."/>
    <LotusField v-model="master.lotus_receiving_hours" label="Giờ nhận hàng" maxlength="140" :readonly="readonly" placeholder="Ví dụ: Thứ Hai–Thứ Bảy, 7:00–17:00"/>
    <LotusField v-model="master.lotus_default_lead_days" label="Thời gian chờ hàng mặc định (ngày)" type="number" min="0" max="365" step="1" :readonly="readonly" hint="Chỉ dùng để gợi ý, ngày giao do NCC xác nhận sẽ được ưu tiên."/>
    <LotusField v-model="master.lotus_address" label="Địa chỉ kho / điểm nhận hàng" type="textarea" wide maxlength="500" :readonly="readonly" placeholder="Địa chỉ giao hàng, xã, tỉnh, hướng dẫn đến cổng kho"/>
    <LotusField v-model="master.lotus_delivery_note" label="Ghi chú giao nhận" type="textarea" wide maxlength="500" :readonly="readonly" placeholder="Cổng giao hàng, giờ nghỉ, yêu cầu bốc dỡ…"/>
    </template>
   </template>
   <template v-else>
    <LotusField v-model="master.name" label="Tên đơn vị tính" maxlength="140" :readonly="!!editing||readonly" placeholder="VD: Thùng" :hint="editing?'Tên đơn vị đã dùng trên chứng từ nên không đổi được.':''" required/>
    <LotusField v-if="editing" :model-value="unitLabel(master.code)" label="Tên hiển thị" readonly/>
    <LotusField v-model="master.must_be_whole_number" type="checkbox" label="Chỉ nhập số nguyên (bao, can, cái…)" :readonly="readonly"/>
    <LotusField v-if="editing" v-model="master.enabled" type="checkbox" label="Đang sử dụng" :readonly="readonly" hint="Bỏ chọn để ngừng dùng; không ngừng được khi còn là đơn vị gốc của vật tư đang dùng."/>
   </template>
  </FormGrid>
  <template v-if="kind==='item'">
   <FormSection title="Đơn vị quy đổi" description="Mua, nhập, xuất theo bao, thùng, tấn… mà tồn kho vẫn tính theo đơn vị gốc.">
    <LineItemsEditor v-model="master.conversions" :columns="conversionColumns" add-label="Thêm đơn vị quy đổi" empty-text="Chưa có đơn vị quy đổi: chỉ dùng đơn vị gốc." :min="0" :readonly="readonly" :new-row="()=>({uom:'',conversion_factor:1})"/>
    <p v-if="editing?.has_ledger" class="lotus-form-note">Vật tư đã nhập / xuất: đơn vị đã có giữ nguyên hệ số; được thêm đơn vị mới hoặc bỏ đơn vị không dùng nữa.</p>
   </FormSection>
   <FormSection title="Trạng thái và phạm vi dùng">
    <FormGrid :columns="3">
     <LotusField :model-value="!master.disabled" type="checkbox" label="Đang sử dụng" :readonly="readonly" hint="Bỏ chọn để ngừng dùng: mã không hiện khi lập chứng từ mới, lịch sử vẫn giữ." @update:model-value="master.disabled=!$event"/>
     <LotusField v-model="master.is_purchase_item" type="checkbox" label="Hàng mua" :readonly="readonly" hint="Hiện trong đề nghị mua, đơn mua, hóa đơn mua."/>
     <LotusField v-model="master.is_sales_item" type="checkbox" label="Hàng bán" :readonly="readonly" hint="Hiện trong đơn bán, hóa đơn bán (phụ phẩm, vật tư bán lại…)."/>
    </FormGrid>
   </FormSection>
   <FormSection v-if="stockItem" title="Lô và hạn dùng">
    <FormGrid :columns="3">
     <LotusField v-model="master.has_batch_no" type="checkbox" label="Quản lý theo lô" :readonly="readonly||editing?.has_ledger" :hint="editing?.has_ledger?'Đã có nhập xuất nên không đổi được.':'Thuốc, phân có số lô của nhà sản xuất.'"/>
     <LotusField v-if="master.has_batch_no" v-model="master.has_expiry_date" type="checkbox" label="Có hạn sử dụng" :readonly="readonly" hint="Cảnh báo lô sắp hết hạn, xuất lô gần hạn trước."/>
     <LotusField v-if="master.has_batch_no&&master.has_expiry_date" v-model="master.shelf_life_in_days" label="Hạn dùng kể từ ngày sản xuất (ngày)" type="number" min="0" step="1" :readonly="readonly"/>
    </FormGrid>
   </FormSection>
   <FormSection v-if="master.is_purchase_item" title="Mua hàng">
    <FormGrid :columns="2">
     <LotusField v-model="master.default_supplier" label="Nhà cung cấp mặc định" :options="(catalog.suppliers||[]).map(s=>({value:s.name,label:s.supplier_name||s.name}))" empty-option="Chưa chọn" :readonly="readonly"/>
     <LotusField v-if="stockItem" v-model="master.default_warehouse" label="Kho nhận mặc định" :options="(catalog.warehouses||[]).map(w=>({value:w.name,label:w.warehouse_name}))" empty-option="Chưa chọn" :searchable="false" :readonly="readonly"/>
     <LotusField v-model="master.lead_time_days" label="Thời gian chờ hàng (ngày)" type="number" min="0" step="1" :readonly="readonly"/>
     <LotusField v-model="master.min_order_qty" :label="'Số lượng đặt tối thiểu ('+unitLabel(master.uom)+')'" type="number" min="0" :readonly="readonly"/>
     <template v-if="editing">
      <LotusField :model-value="editing.last_purchase_rate?money(editing.last_purchase_rate):'Chưa mua'" label="Giá mua gần nhất" readonly/>
      <LotusField v-if="stockItem" :model-value="editing.valuation_rate?money(editing.valuation_rate):'—'" label="Giá vốn hiện tại" readonly/>
     </template>
    </FormGrid>
   </FormSection>
  </template>
  <template #secondary><UiButton v-if="editing?.can_delete&&!deleting" type="button" variant="destructive" :disabled="busy" @click="deleting=true">Xóa danh mục</UiButton></template>
 </ModalForm>
</template>


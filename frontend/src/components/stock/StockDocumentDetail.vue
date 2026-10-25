<script setup>
import {computed,ref} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import LotusField from '../form/LotusField.vue'
import DataTable from '../DataTable.vue'
import SigningPanel from '../SigningPanel.vue'
import {Button as UiButton} from '../ui/button'
import {detailColumns,receiptDetailColumns,statusLabel,entryTypeLabel} from '../../stock-columns'
// Chi tiết phiếu kho: in, sửa / xóa nháp, ghi sổ (cập nhật tồn kho) và ký số sau ghi sổ.
const props=defineProps({warehouses:{type:Array,default:()=>[]},session:Object})
const emit=defineEmits(['changed','edit'])
const api=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const issueModes={Manual:'Thủ công',Plan:'Theo kế hoạch đã duyệt',Request:'Theo yêu cầu đã duyệt'}
const open=ref(false),detail=ref(null),busy=ref(false),error=ref(''),confirmPost=ref(false),deleting=ref(false)
const warehouseLabel=id=>props.warehouses.find(w=>w.name===id)?.warehouse_name||id||'—'
const money=computed(()=>props.session?.companies?.find(c=>c.name===detail.value?.company)?.default_currency||'VND')
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:money.value})
const receipt=computed(()=>detail.value?.kind==='Material Receipt')
const columns=computed(()=>receipt.value?[...detailColumns(warehouseLabel),...receiptDetailColumns(cash)]:detailColumns(warehouseLabel))
const canEdit=computed(()=>detail.value?.docstatus===0&&detail.value.can_write&&(detail.value.kind!=='Material Issue'||!detail.value.issue_mode||detail.value.issue_mode==='Manual'))
const printURL=computed(()=>detail.value?'/lotus/in-phieu?'+new URLSearchParams({doctype:detail.value.doctype,name:detail.value.name}):'')
async function show(doctype,name){
 error.value='';confirmPost.value=false;deleting.value=false
 detail.value=await api('document',{doctype,name});open.value=true
}
async function post(){
 if(busy.value||!confirmPost.value)return
 busy.value=true;error.value=''
 try{await api('submit_document',{doctype:detail.value.doctype,name:detail.value.name,modified:detail.value.modified},true);detail.value=await api('document',{doctype:detail.value.doctype,name:detail.value.name});confirmPost.value=false;emit('changed')}
 catch(e){error.value=e.message}finally{busy.value=false}
}
async function remove(){
 busy.value=true;error.value=''
 try{await api('delete_draft',{doctype:detail.value.doctype,name:detail.value.name,modified:detail.value.modified},true);open.value=false;emit('changed')}
 catch(e){error.value=e.message}finally{busy.value=false}
}
function edit(){const current=detail.value;open.value=false;emit('edit',current)}
defineExpose({open:show,hasChanges:()=>false,discardChanges:()=>{open.value=false}})
</script>

<template>
 <ModalForm v-if="detail" v-model="open" :title="detail.name" :busy="busy" :error="error" width="1080px" :readonly="!detail.can_submit" submit-label="Ghi sổ phiếu" busy-label="Đang ghi sổ…" :submit-disabled="!confirmPost" @submit="post">
  <p class="lotus-modal-form__description">{{entryTypeLabel(detail.kind)}} · {{detail.posting_date}} · {{detail.company}} · {{statusLabel(detail.docstatus)}}</p>
  <div v-if="deleting" class="lotus-delete-confirm" role="alert"><p>Xác nhận xóa phiếu nháp {{detail.name}}?</p><div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="deleting=false">Giữ lại</UiButton><UiButton type="button" variant="destructive" :disabled="busy" @click="remove">Xác nhận xóa</UiButton></div></div>
  <p v-if="detail.docstatus===1" class="stock-success" role="status">Phiếu đã ghi sổ. Tồn kho đã được cập nhật.</p>
  <SigningPanel v-if="detail.docstatus===1" :doctype="detail.doctype" :name="detail.name" :company="detail.company" @notice="error=''" @error="error=$event"/>
  <DataTable :rows="detail.items" :columns="columns"/>
  <template v-if="receipt">
   <dl class="lotus-form-totals"><div><dt>Tiền vật tư</dt><dd>{{cash(detail.basic_total)}}</dd></div><div><dt>Chi phí</dt><dd>{{cash(detail.additional_total)}}</dd></div><div><dt>Giá trị nhập</dt><dd>{{cash(detail.incoming_total)}}</dd></div></dl>
   <dl v-if="detail.additional_costs?.length" class="stock-detail-costs"><div v-for="(cost,index) in detail.additional_costs" :key="index"><dt>{{cost.description}}</dt><dd>{{cash(cost.amount)}}</dd></div></dl>
   <p class="lotus-form-note">Giá trị nhập gồm chi phí phân bổ. Công nợ nhà cung cấp ghi nhận bằng hóa đơn mua hàng.</p>
  </template>
  <p v-if="detail.receiver" class="lotus-form-note">Người nhận: {{detail.receiver}} · {{issueModes[detail.issue_mode]||issueModes.Manual}}</p>
  <p v-if="detail.notes" class="lotus-form-note">{{detail.notes}}</p>
  <LotusField v-if="detail.can_submit" v-model="confirmPost" type="checkbox" required label="Tôi đã kiểm tra phiếu. Ghi sổ sẽ cập nhật tồn kho."/>
  <p v-else-if="detail.docstatus===0" class="lotus-form-note">Tài khoản chưa có quyền ghi sổ hoặc phiếu thuộc nghiệp vụ nâng cao chưa hỗ trợ ở đây.</p>
  <template #secondary>
   <UiButton v-if="canEdit" type="button" variant="outline" :disabled="busy" @click="edit">Sửa phiếu nháp</UiButton>
   <UiButton v-if="detail.docstatus===0&&detail.can_delete&&!deleting" type="button" variant="destructive" :disabled="busy" @click="deleting=true">Xóa phiếu nháp</UiButton>
  </template>
  <template #actions><UiButton as="a" variant="outline" :href="printURL" target="_blank" rel="noopener">In phiếu</UiButton></template>
 </ModalForm>
</template>

<style>
.stock-detail-costs{display:grid;gap:4px;margin:0}
.stock-detail-costs div{display:flex;justify-content:space-between;gap:12px}
.stock-detail-costs dt{color:var(--lotus-muted)}
.stock-detail-costs dd{margin:0;font-variant-numeric:tabular-nums}
</style>

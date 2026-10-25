<script setup>
import {onMounted,ref} from 'vue'
import {call} from '../../api'
import ProcurementSigners from '../ProcurementSigners.vue'
import ProcurementField from '../ProcurementField.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button} from '../ui/button'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
const props=defineProps({doctype:String,name:String,company:String,disabled:Boolean})
const emit=defineEmits(['loaded','changed','error'])
const info=ref(null),options=ref(null),signers=ref({}),busy=ref(false),reason=ref(''),date=ref(''),operation=ref(''),dialog=ref(false),qr=ref(null),qrOpen=ref(false)
const confirmation=useWorkspaceConfirm(),confirmationOpen=confirmation.open,confirmationTitle=confirmation.title,confirmationMessage=confirmation.message
let key=crypto.randomUUID()
const api=(m,args={},write=false)=>call('lotus_farm.erp_workbench.'+m,args,write)
async function load(){try{info.value=await api('approval',{doctype:props.doctype,name:props.name});emit('loaded',info.value);if(info.value?.order?.can_request_approval||info.value?.can_start)options.value=await call('lotus_farm.signing.candidates',{chain:info.value.chain,company:props.company})}catch(e){emit('error',e.message)}}
async function act(method,values={}){if(busy.value||props.disabled)return;if(!values.reason&&!await confirmation.ask(method==='approve_order'||method==='sign'?'Xác nhận ký duyệt chứng từ và thực hiện bước nghiệp vụ tương ứng?':'Xác nhận cập nhật trạng thái chứng từ?'))return;busy.value=true;try{await api('approval_action',{doctype:props.doctype,name:props.name,modified:info.value.order?.modified||info.value.proposal?.modified||info.value.modified,operation:method,values,client_key:key},true);key=crypto.randomUUID();dialog.value=false;emit('changed')}catch(e){emit('error',e.message)}finally{busy.value=false}}
async function payment(method){try{const current=await api('document',{doctype:props.doctype,name:props.name,company:props.company});info.value.modified=current.doc.modified;await act(method,method==='start_signing'||method==='sign'&&info.value.can_start?{signers:signers.value}:method==='return'?{reason:reason.value}:{})}catch(e){emit('error',e.message)}}
function ask(method){operation.value=method;reason.value='';date.value=info.value.order?.revised_delivery_date||info.value.order?.expected_date||'';dialog.value=true}
async function showQR(){busy.value=true;try{qr.value=await call('lotus_farm.digital_signature.create_signing_challenge',{name:props.name,modified:info.value.order.modified},true);qrOpen.value=true}catch(e){emit('error',e.message)}finally{busy.value=false}}
onMounted(load)
</script>
<template>
 <section v-if="info?.gate" class="erp-approval" aria-label="Duyệt và chữ ký"><h3>Quy trình duyệt</h3><LotusSignatureTimeline v-if="info.status?.round" :steps="info.status.steps" :current="info.status.current" title=""/>
  <template v-if="info.order"><p v-if="info.order.reject_reason" role="status">{{info.order.reject_reason}}</p><ProcurementSigners v-if="info.order.can_request_approval&&options" v-model="signers" :options="options"/>
   <div class="erp-toolbar-actions"><Button v-if="info.order.can_request_approval" :disabled="disabled||busy||!signers.APPROVE" @click="act('request_approval',{approver:signers.APPROVE})">Trình duyệt</Button><Button v-if="info.order.can_approve" :disabled="disabled||busy" @click="act('approve_order')">Phê duyệt</Button><Button v-if="info.order.can_approve" variant="outline" :disabled="disabled||busy" @click="showQR">Duyệt bằng QR</Button><Button v-if="info.order.can_approve" variant="outline" :disabled="disabled||busy" @click="ask('reject_order')">Trả lại</Button><Button v-if="info.order.can_manage&&!info.order.sent_at" variant="outline" :disabled="disabled||busy" @click="act('mark_order_sent')">Đã gửi NCC</Button><Button v-if="info.order.can_manage&&!info.order.supplier_confirmed_at" variant="outline" :disabled="disabled||busy" @click="act('confirm_supplier_order')">NCC xác nhận</Button><Button v-if="info.order.can_manage" variant="outline" :disabled="disabled||busy" @click="ask('reschedule_order')">Đổi hẹn giao</Button><Button v-if="info.order.can_close" variant="outline" :disabled="disabled||busy" @click="ask('close_order')">Đóng phần không giao</Button></div>
  </template>
  <template v-else-if="info.chain==='payment_voucher'"><ProcurementSigners v-if="info.can_start&&options" v-model="signers" :options="options"/><div class="erp-toolbar-actions"><Button v-if="info.can_start" :disabled="disabled||busy" @click="payment(info.chain==='purchase_proposal'?'sign':'start_signing')">{{info.chain==='purchase_proposal'?'Trình ký đề xuất':'Trình ký thanh toán'}}</Button><Button v-if="info.status?.can_sign" :disabled="disabled||busy" @click="payment('sign')">Ký duyệt</Button><Button v-if="info.status?.can_return" variant="outline" :disabled="disabled||busy" @click="ask('return')">Trả lại</Button></div></template>
  <WorkspaceModal v-model="dialog" title="Xử lý chứng từ" width="560px" :busy="busy"><form @submit.prevent="operation==='return'?payment('return'):act(operation,{reason,expected_date:date})"><ProcurementField v-if="operation==='reschedule_order'" v-model="date" label="Ngày giao mới" type="date" required/><ProcurementField v-model="reason" label="Lý do" type="textarea" minlength="3" required/><Button type="submit" :disabled="busy||reason.trim().length<3">Xác nhận</Button></form></WorkspaceModal>
  <WorkspaceModal v-model="qrOpen" title="Duyệt bằng điện thoại" width="420px"><img v-if="qr" class="erp-signing-qr" :src="qr.qr_image" alt="QR ký duyệt đơn mua"><p v-if="qr">Hết hạn: {{qr.expires_at}}</p><Button variant="outline" @click="qrOpen=false;emit('changed')">Đã ký, tải lại</Button></WorkspaceModal>
  <WorkspaceConfirm :open="confirmationOpen" :title="confirmationTitle" :message="confirmationMessage" @answer="confirmation.finish"/>
 </section>
</template>

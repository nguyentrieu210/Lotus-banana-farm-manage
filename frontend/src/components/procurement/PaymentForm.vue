<script setup>
// Lập phiếu chi trả một nhà cung cấp (spec 003, US6): chọn nhiều hóa đơn, tạm ứng theo đơn mua, phần trả thêm ghi rõ là
// tạm ứng; hình thức chi, số tham chiếu, file, người ký. Máy chủ (finance.supplier_payment.prepare) không cho chi vượt số
// còn nợ sau các phiếu đang chờ ký, rồi bắt đầu chuỗi ký phiếu chi.
import {computed,ref,watch} from 'vue'
import ResponsiveForm from '../form/ResponsiveForm.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import ProcurementSigners from '../ProcurementSigners.vue'
import {Button} from '../ui/button'
import {FilePickerButton} from '../ui/file-input'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'
import {newKey} from '../../procurement'
import {upload} from '../../api'

const props=defineProps({modelValue:Boolean,supplier:String,company:String,preset:{type:Array,default:()=>[]},mobile:Boolean,today:String,callFn:Function,uploader:Function})
const emit=defineEmits(['update:modelValue','created'])
const call=(module,name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.'+module+'.'+name,args,write):lotusMethod(module,name,args,write)
const MODES=[{value:'bank',label:'Chuyển khoản'},{value:'cash',label:'Tiền mặt'}]
const busy=ref(false),error=ref(''),info=ref(null),amounts=ref({}),advance=ref(''),mode=ref('bank'),reference=ref(''),date=ref(''),remark=ref(''),signers=ref({}),options=ref(null),added=ref([]),key=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const id=item=>item.doctype+'|'+item.name
const total=computed(()=>(info.value?.items||[]).reduce((sum,i)=>sum+Number(amounts.value[id(i)]||0),0)+Number(advance.value||0))
const missingSigners=computed(()=>(options.value?.steps||[]).slice(1).some(s=>!signers.value[s.key]))
const problem=computed(()=>{
 for(const item of info.value?.items||[]){const value=Number(amounts.value[id(item)]||0);if(value<0)return item.label+': số tiền không hợp lệ.';if(value>item.payable+0.5)return item.label+': chỉ còn trả được '+money(item.payable)+'. Phần trả thêm ghi vào ô tạm ứng.'}
 if(Number(advance.value||0)<0)return 'Số tạm ứng không hợp lệ.'
 if(total.value<=0)return 'Nhập số tiền trả cho ít nhất một hóa đơn, hoặc số tạm ứng.'
 if(mode.value==='bank'&&!reference.value.trim())return 'Chuyển khoản cần số ủy nhiệm chi / số giao dịch.'
 if(!date.value)return 'Chọn ngày chi.'
 if(missingSigners.value)return 'Chọn đủ người ký phiếu chi.'
 return ''
})
async function start(){
 error.value='';info.value=null;amounts.value={};advance.value='';mode.value='bank';reference.value='';remark.value='';added.value=[];date.value=props.today||'';key.value=newKey()
 busy.value=true
 try{
  info.value=await call('finance.supplier_payment','open_items',{supplier:props.supplier})
  // The invoices the person came from are filled with what can still be paid.
  for(const item of info.value.items)if(props.preset.includes(item.name))amounts.value[id(item)]=item.payable
  options.value=await call('signing','candidates',{chain:'payment_voucher',company:props.company||undefined})
 }catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
watch(()=>props.modelValue,open=>{if(open)start()},{immediate:true})
function payAll(){for(const item of info.value?.items||[])if(item.doctype==='Purchase Invoice')amounts.value[id(item)]=item.payable}
const uploaded=new Map()
async function submit(){
 if(busy.value||problem.value)return
 busy.value=true;error.value=''
 try{
  const send=props.uploader||upload,files=[]
  for(const file of added.value){if(!uploaded.has(file))uploaded.set(file,(await send(file)).file_url);files.push(uploaded.get(file))}
  const allocations=info.value.items.filter(i=>Number(amounts.value[id(i)])>0).map(i=>({doctype:i.doctype,name:i.name,amount:Number(amounts.value[id(i)])}))
  const result=await call('finance.supplier_payment','prepare',{supplier:props.supplier,allocations,advance_amount:Number(advance.value||0),mode:mode.value,
   reference_no:reference.value.trim()||null,posting_date:date.value,remark:remark.value.trim()||null,files,signers:signers.value,client_key:key.value},true)
  emit('created',result);emit('update:modelValue',false)
 }catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
</script>

<template>
 <ResponsiveForm :mobile="mobile" :model-value="modelValue" :title="'Phiếu chi · '+(info?.supplier_name||'')" width="1080px" :busy="busy" :error="error" submit-label="Lập phiếu và trình ký" busy-label="Đang lập phiếu…" :submit-disabled="!!problem" @update:model-value="emit('update:modelValue',$event)" @submit="submit">
  <template v-if="info">
   <FormSection title="Khoản trả" :description="'Đang nợ theo hóa đơn '+money(info.owed)+'. Số còn trả được đã trừ các phiếu đang chờ ký.'">
    <template #actions><component :is="button" type="button" variant="outline" size="sm" @click="payAll">Trả hết các hóa đơn</component></template>
    <div v-for="item in info.items" :key="id(item)" class="payment-form__item">
     <div><strong>{{item.label}}</strong><small>{{item.name}} · {{shortDate(item.date)}}<template v-if="item.due_date"> · hạn trả {{shortDate(item.due_date)}}</template> · còn trả được {{money(item.payable)}}<template v-if="item.waiting"> · đang chờ ký {{money(item.waiting)}}</template></small></div>
     <LotusField v-model="amounts[id(item)]" :mobile="mobile" type="money" :aria-label="'Số tiền trả '+item.label" :disabled="item.payable<=0.5" placeholder="0"/>
    </div>
    <p v-if="!info.items.length" class="lotus-form-note">Nhà cung cấp này không còn hóa đơn nợ hay đơn mua chờ tạm ứng. Vẫn lập được phiếu tạm ứng.</p>
    <LotusField v-model="advance" :mobile="mobile" type="money" label="Tạm ứng thêm (chưa gắn hóa đơn)" hint="Phần trả vượt số nợ phải ghi ở đây; sẽ cấn trừ vào hóa đơn sau."/>
   </FormSection>
   <FormSection title="Cách chi">
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="mode" :mobile="mobile" label="Hình thức chi" :options="MODES" :searchable="false"/>
     <LotusField v-model="reference" :mobile="mobile" label="Số ủy nhiệm chi / số giao dịch" :required="mode==='bank'" maxlength="60"/>
     <LotusField v-model="date" :mobile="mobile" label="Ngày chi" type="date" required/>
    </FormGrid>
    <LotusField v-model="remark" :mobile="mobile" label="Lý do chi" placeholder="Trả tiền hàng tháng 11…" maxlength="300"/>
    <div class="payment-form__files"><FilePickerButton :as="mobile?LotusMobileButton:undefined" accept="image/*,application/pdf" multiple label="Đính kèm chứng từ chi" size="sm" :disabled="busy" @files="list=>added=[...added,...list].slice(0,20)">Đính kèm ủy nhiệm chi, biên nhận</FilePickerButton>
     <span v-for="(file,index) in added" :key="index" class="lotus-form-note">{{file.name}} <component :is="button" type="button" variant="ghost" size="sm" :aria-label="'Bỏ '+file.name" @click="added=added.filter((_,i)=>i!==index)">Bỏ</component></span></div>
   </FormSection>
   <ProcurementSigners v-model="signers" :mobile="mobile" :options="options"/>
   <dl class="lotus-form-totals"><div><dt>Tổng tiền chi</dt><dd>{{money(total)}}</dd></div><div v-if="Number(advance)>0"><dt>Trong đó tạm ứng</dt><dd>{{money(advance)}}</dd></div></dl>
   <p v-if="problem" class="lotus-form-note" role="status">{{problem}}</p>
   <p class="lotus-form-note">Phiếu chỉ ghi sổ sau khi kế toán trưởng và giám đốc ký.</p>
  </template>
 </ResponsiveForm>
</template>

<style>
.payment-form__item{display:grid;grid-template-columns:minmax(0,2fr) minmax(140px,1fr);gap:var(--lotus-space-3,12px);align-items:center;padding:var(--lotus-space-2,8px) 0;border-bottom:1px solid var(--lotus-border);min-width:0}
.payment-form__item div{display:grid;gap:2px;min-width:0}
.payment-form__item small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.payment-form__files{display:flex;flex-wrap:wrap;align-items:center;gap:var(--lotus-space-2,8px)}
@media(max-width:620px){.payment-form__item{grid-template-columns:minmax(0,1fr)}}
</style>

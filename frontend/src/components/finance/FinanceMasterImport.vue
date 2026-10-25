<script setup>
import {FileInput} from '../ui/file-input'
import {computed,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import DataTable from '../DataTable.vue'
import {Button} from '../ui/button'
import {call} from '../../api'

const props=defineProps({modelValue:Boolean,kind:{type:String,default:'categories'}})
const emit=defineEmits(['update:modelValue','imported'])
const API='lotus_farm.finance.master_imports.'
const content=ref(''),preview=ref(null),error=ref(''),busy=ref(false),saving=ref(false),fileVersion=ref(0)
const categories=computed(()=>props.kind==='categories')
const title=computed(()=>categories.value?'Nhập nhóm tài sản từ Excel':'Nhập hệ thống tài khoản từ Excel')
const fields=computed(()=>categories.value?
 [['asset_category_name','Nhóm tài sản'],['non_depreciable_category','Không khấu hao'],['fixed_asset_account','TK nguyên giá'],['accumulated_depreciation_account','TK hao mòn'],['depreciation_expense_account','TK khấu hao'],['capital_work_in_progress_account','TK chờ ghi tăng']]:
 [['account_number','Số tài khoản'],['account_name','Tên tài khoản'],['parent_account','Tài khoản cha'],['is_group','Là nhóm'],['account_type','Loại tài khoản']])
const columns=computed(()=>[
 {field:'line',headerName:'Dòng',width:80},
 {field:'action',headerName:'Thao tác',width:140,valueFormatter:p=>p.value==='skip'?'Bỏ qua đã có':'Thêm mới'},
 ...fields.value.map(([field,headerName])=>({field,headerName,minWidth:160,flex:1,valueGetter:p=>p.data.values[field]})),
 ...(preview.value?.rows.some(r=>Object.keys(r.errors||{}).length)?[{field:'errors',headerName:'Lỗi',pinned:'right',width:340,minWidth:280,valueGetter:p=>Object.entries(p.data.errors||{}).map(([k,v])=>(fields.value.find(f=>f[0]===k)?.[1]||k)+': '+v).join('; ')}]:[])
])
watch(()=>[props.modelValue,props.kind],()=>{content.value='';preview.value=null;error.value='';fileVersion.value++})
function download(){window.location.href='/api/method/'+API+'template?kind='+encodeURIComponent(props.kind)}
function readFile(event){
 const file=event.target.files?.[0],version=++fileVersion.value
 content.value='';preview.value=null;error.value=''
 if(!file)return
 if(file.size>5_000_000){error.value='File vượt quá 5 MB.';return}
 const reader=new FileReader()
 reader.onload=()=>{if(version===fileVersion.value)content.value=String(reader.result)}
 reader.onerror=()=>{if(version===fileVersion.value)error.value='Không đọc được file. Chọn lại file .xlsx.'}
 reader.readAsDataURL(file)
}
async function inspect(){
 busy.value=true;error.value='';preview.value=null
 const source=content.value,kind=props.kind,version=fileVersion.value
 try{const data=await call(API+'preview',{kind,content:source},true);if(version===fileVersion.value&&props.modelValue)preview.value=data}
 catch(e){error.value=e.message||String(e)}finally{busy.value=false}
}
async function confirm(){
 if(!preview.value?.valid||busy.value||saving.value)return
 saving.value=true;error.value=''
 try{
  const data=await call(API+'commit',{kind:props.kind,content:content.value,fingerprint:preview.value.fingerprint},true)
  emit('update:modelValue',false)
  emit('imported',{...data,kind:props.kind})
 }catch(e){error.value=e.message||String(e);preview.value=null}finally{saving.value=false}
}
</script>

<template>
 <WorkspaceModal :model-value="modelValue" :title="title" width="1100px" :busy="saving" @update:model-value="emit('update:modelValue',$event)">
  <p v-if="error" class="hr-ops-error" role="alert">{{error}}</p>
  <div class="fin-master-import__actions">
   <Button variant="outline" :disabled="saving" @click="download">Tải mẫu</Button>
   <FileInput :key="kind+'-'+(modelValue?'open':'closed')" accept=".xlsx" :aria-label="categories?'File nhóm tài sản':'File hệ thống tài khoản'" :disabled="busy||saving" @change="readFile"/>
   <Button :disabled="!content||busy||saving" @click="inspect">{{busy?'Đang kiểm tra…':'Xem trước'}}</Button>
  </div>
  <p v-if="categories">Nhập số tài khoản hoặc mã đầy đủ từ sheet tham chiếu. Nhập tài khoản còn thiếu trước khi nhập nhóm.</p>
  <p v-else>Tài khoản cha phải là nhóm đang dùng hoặc nhóm trong cùng file. Loại tài khoản lấy từ sheet Loai tai khoan.</p>
  <p>Chỉ thêm mới; dòng đã có và khớp được bỏ qua. Không nhập số dư hay ghi bút toán.</p>
  <template v-if="preview">
   <p role="status">Thêm {{preview.create_count}} · Bỏ qua {{preview.skip_count}}<span v-if="!preview.rows.length"> · File chưa có dữ liệu.</span></p>
   <DataTable :rows="preview.rows" :columns="columns" row-key="line" :storage-key="'fin-master-import-'+kind" empty="File chưa có dữ liệu."/>
   <div class="fin-master-import__actions"><Button :disabled="!preview.valid||busy||saving" @click="confirm">{{categories?'Xác nhận nhập nhóm':'Xác nhận nhập tài khoản'}}</Button></div>
  </template>
 </WorkspaceModal>
</template>

<style>
.fin-master-import__actions{display:flex;align-items:center;flex-wrap:wrap;gap:var(--lotus-space-2);margin-block:var(--lotus-space-3)}
.fin-master-import__actions>input[type=file]{flex:1;min-width:180px;width:auto}
.fin-master-import__actions>button{flex-shrink:0}
</style>

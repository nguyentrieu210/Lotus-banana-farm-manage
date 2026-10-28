<script setup>
import {computed,ref,watch} from 'vue'
import {useSession,useScope} from './store'
import {call} from './api'
import DataTable from './components/DataTable.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'

const session=useSession()
const scope=useScope()
const farms=computed(()=>session.farms||[])
const farm=ref(scope.farm||farms.value[0]?.name||'')
const state=ref({rows:[],colors:[],programs:[],can_create:false,notice:''})
const loading=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const search=ref(''),period=ref('all')
const color=ref(''),start=ref(''),end=ref('')
const program=ref(''),generatedFrom=ref(''),generatedTo=ref('')
const today=computed(()=>session.today||new Date().toISOString().slice(0,10))
const palette=computed(()=>Object.fromEntries(state.value.colors.map(x=>[x.code,x.label])))
const rows=computed(()=>state.value.rows.map(r=>{
 const status=!r.enabled?'Ngừng dùng':!r.valid_from||!r.valid_to?'Chưa có kỳ':r.valid_from>today.value?'Sắp áp dụng':r.valid_to<today.value?'Đã qua':'Đang áp dụng'
 return {...r,color_name:palette.value[r.color_code]||r.display_name,
  source_label:r.process_adoption?'Lịch đã duyệt':'Lịch thủ công',status_label:status}
}).filter(r=>{
 const q=search.value.trim().toLocaleLowerCase('vi')
 const matches=!q||[r.tag_code,r.display_name,r.color_name,r.valid_from,r.valid_to].some(v=>String(v||'').toLocaleLowerCase('vi').includes(q))
 return matches&&(period.value==='all'||r.status_label===period.value)
}))
const columns=[
 {field:'color_name',headerName:'Màu dây',minWidth:165},
 {field:'color_code',headerName:'Mã màu',minWidth:90},
 {field:'valid_from',headerName:'Áp dụng từ',minWidth:125},
 {field:'valid_to',headerName:'Đến hết ngày',minWidth:125},
 {field:'status_label',headerName:'Tình trạng',minWidth:130},
 {field:'source_label',headerName:'Nguồn lịch',minWidth:135},
 {field:'tag_code',headerName:'Mã đợt (lưu lịch sử)',minWidth:230},
]
let request=0
async function load(){
 const key=++request
 if(!farm.value){state.value={rows:[],colors:[],programs:[],can_create:false,notice:''};return}
 loading.value=true;error.value=''
 try{
  const result=await call('lotus_farm.bunch_tag_catalog.catalog',{farm:farm.value})
  if(key!==request)return
  state.value=result
  if(!result.programs.some(x=>x.name===program.value))program.value=result.programs[0]?.name||''
 }catch(e){if(key===request)error.value=e.message||'Không đọc được lịch màu dây.'}
 finally{if(key===request)loading.value=false}
}
watch(()=>scope.farm,value=>{if(value)farm.value=value})
watch(farm,()=>{notice.value='';load()},{immediate:true})
function validDates(a,b){return !!a&&!!b&&a<=b}
async function addPeriod(){
 if(!validDates(start.value,end.value)||!color.value){error.value='Chọn màu và nhập ngày bắt đầu, kết thúc hợp lệ.';return}
 saving.value=true;error.value='';notice.value=''
 try{
  await call('lotus_farm.bunch_tag_catalog.add_manual_period',{
   farm:farm.value,color_code:color.value,valid_from:start.value,valid_to:end.value
  },true)
  notice.value='Đã lưu đợt màu mới. Các đợt trước giữ nguyên.'
  color.value='';start.value='';end.value=''
  await load()
 }catch(e){error.value=e.message||'Chưa lưu được kỳ màu dây.'}
 finally{saving.value=false}
}
async function generate(){
 if(!program.value||!validDates(generatedFrom.value,generatedTo.value)){error.value='Chọn chương trình và khoảng ngày cần tạo.';return}
 saving.value=true;error.value='';notice.value=''
 try{
  const r=await call('lotus_farm.onedrive_workspace.generate_tags',{
   process_adoption:program.value,from_date:generatedFrom.value,to_date:generatedTo.value
  },true)
  notice.value='Đã tạo '+(r.created||0)+' kỳ; '+(r.existing||0)+' kỳ đã tồn tại.'
  await load()
 }catch(e){error.value=e.message||'Không tạo được kỳ theo lịch đã duyệt.'}
 finally{saving.value=false}
}
</script>

<template>
 <section class="color-catalog lotus-ui" aria-label="Danh mục màu dây cắt bắp">
  <div class="color-head">
   <div><h2>Danh mục màu dây cắt bắp</h2><p>Mỗi màu có ngày bắt đầu và kết thúc rõ ràng. Màu quay vòng thì tạo kỳ mới, không sửa kỳ cũ đã dùng.</p></div>
   <UiButton type="button" variant="outline" :disabled="loading" @click="load">Làm mới</UiButton>
  </div>
  <div class="color-toolbar">
   <label>Vườn <UiSelect v-model="farm" aria-label="Vườn">
    <option value="">Chọn vườn</option><option v-for="f in farms" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option>
   </UiSelect></label>
   <label>Tìm màu / ngày <UiInput v-model="search" placeholder="Mã màu, tên màu, ngày..." /></label>
   <label>Tình trạng <UiSelect v-model="period" aria-label="Tình trạng áp dụng">
    <option value="all">Tất cả</option><option value="Đang áp dụng">Đang áp dụng</option>
    <option value="Sắp áp dụng">Sắp áp dụng</option><option value="Đã qua">Đã qua</option>
    <option value="Chưa có kỳ">Chưa có kỳ</option><option value="Ngừng dùng">Ngừng dùng</option>
   </UiSelect></label>
  </div>
  <p v-if="error" role="alert" class="color-error">{{error}}</p>
  <p v-if="notice" role="status" class="color-success">{{notice}}</p>
  <p class="color-notice">{{state.notice}}</p>
  <p v-if="loading">Đang đọc danh mục…</p>
  <DataTable v-else :rows="rows" :columns="columns" row-key="name" storage-key="bunch-color-periods" empty="Chưa có kỳ màu dây trong vườn này."/>
  <p class="color-footnote">{{rows.length}} kỳ màu đang hiển thị. Ngày ở đây là ngày <strong>cắt bắp</strong>, không phải ngày dự thu hoạch.</p>

  <div v-if="state.can_create" class="color-actions">
   <section class="color-panel">
    <h3>Thêm kỳ màu thủ công</h3>
    <p>Dùng khi vườn chưa có chương trình màu được duyệt cho những ngày này. Các kỳ trong cùng vườn không được trùng nhau.</p>
    <form @submit.prevent="addPeriod">
     <label>Màu dây <UiSelect v-model="color" required aria-label="Chọn màu dây">
      <option value="">Chọn màu</option><option v-for="c in state.colors" :key="c.code" :value="c.code">{{c.code}} · {{c.label}}</option>
     </UiSelect></label>
     <label>Ngày bắt đầu <UiInput v-model="start" type="date" required /></label>
     <label>Ngày kết thúc <UiInput v-model="end" type="date" required /></label>
     <UiButton type="submit" :disabled="saving||!farm||!color||!validDates(start,end)">{{saving?'Đang lưu…':'Lưu kỳ màu mới'}}</UiButton>
    </form>
   </section>
   <section v-if="state.programs.length" class="color-panel">
    <h3>Tạo kỳ từ lịch đã duyệt</h3>
    <p>Giữ nguyên lịch màu và ngày áp dụng của phiên bản nguồn; không được tự thay kỳ đã phát hành.</p>
    <form @submit.prevent="generate">
     <label>Chương trình <UiSelect v-model="program" required aria-label="Chương trình màu dây">
      <option v-for="p in state.programs" :key="p.name" :value="p.name">Phiên bản {{p.version}} · {{p.valid_from}} → {{p.valid_to||'Chưa kết thúc'}}</option>
     </UiSelect></label>
     <label>Từ ngày <UiInput v-model="generatedFrom" type="date" required /></label>
     <label>Đến ngày <UiInput v-model="generatedTo" type="date" required /></label>
     <UiButton type="submit" variant="outline" :disabled="saving||!program||!validDates(generatedFrom,generatedTo)">Tạo kỳ từ lịch đã duyệt</UiButton>
    </form>
   </section>
  </div>
 </section>
</template>

<style scoped>
.color-catalog{display:grid;gap:15px;padding:12px 18px 28px;max-width:100%;min-width:0}
.color-head{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
.color-head h2{font-size:19px;margin:0 0 5px}
.color-head p,.color-panel p,.color-footnote{font-size:12px;color:var(--lotus-muted);margin:0;line-height:1.6}
.color-toolbar{display:grid;grid-template-columns:repeat(3,minmax(155px,1fr));gap:12px}
.color-toolbar label,.color-panel label{font-size:12px;display:grid;gap:5px;font-weight:600}
.color-notice{margin:0;font-size:12px;color:var(--lotus-muted)}
.color-error{color:var(--lotus-danger);margin:0}
.color-success{color:var(--lotus-success-700);margin:0}
.color-actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;align-items:start}
.color-panel{border:1px solid var(--lotus-border);border-radius:12px;padding:15px;display:grid;gap:10px}
.color-panel h3{margin:0;font-size:15px}
.color-panel form{display:grid;gap:10px}
.color-panel form button{justify-self:start}
@media(max-width:680px){.color-toolbar{grid-template-columns:1fr}.color-catalog{padding:8px 10px}}
</style>

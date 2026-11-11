<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
import {blockList,crewTeam,isOverdue} from '../../issue-request-model.js'
// Kho › Xuất kho › "Cấp theo yêu cầu (N)" (spec 005): yêu cầu cấp vật tư đã duyệt, chưa đóng, còn số
// (lotus_farm.warehouse.issue_queue), xếp theo ngày cần, quá hạn tô đỏ. "Lập phiếu xuất" mở form xuất kho đang có
// ở chế độ "Theo yêu cầu đã duyệt" (StockDocumentForm.openFromRequest).
const props=defineProps({company:String,warehouse:String,active:Boolean,refreshKey:Number,today:String})
const emit=defineEmits(['issue','count'])
const rows=ref([]),open=ref(false),busy=ref(false),error=ref('')
let asked=0
async function load(){
 if(!props.company||!props.active)return
 const mine=++asked
 busy.value=true;error.value=''
 try{
  const r=await call('lotus_farm.warehouse.issue_queue',{company:props.company,warehouse:props.warehouse||null})
  if(mine!==asked)return
  rows.value=Array.isArray(r)?r:r?.rows||[]
 }catch(e){if(mine===asked){error.value=e.message;rows.value=[]}}
 finally{if(mine===asked){busy.value=false;emit('count',rows.value.length)}}
}
watch(()=>[props.company,props.warehouse,props.active,props.refreshKey],load,{immediate:true})
const needed=r=>r.needed||r.schedule_date||''
const sorted=computed(()=>[...rows.value].sort((a,b)=>(needed(a)||'9999').localeCompare(needed(b)||'9999')||String(a.name).localeCompare(String(b.name))))
const late=r=>isOverdue({...r,state:r.state||'waiting'},props.today)
function show(){open.value=true;load()}
function issue(row){open.value=false;emit('issue',row.name)}
defineExpose({show,reload:load,count:()=>rows.value.length})
</script>

<template>
 <ModalForm v-model="open" title="Cấp theo yêu cầu" width="820px" readonly>
  <p v-if="error" class="lotus-modal-form__error" role="alert">{{error}}</p>
  <p v-if="busy&&!rows.length" class="lotus-form-note" role="status">Đang tải…</p>
  <p v-else-if="!rows.length" class="lotus-form-note">Không có yêu cầu đã duyệt nào còn chờ cấp.</p>
  <div class="issue-queue">
   <article v-for="r in sorted" :key="r.name" class="issue-queue__card" :class="{'is-late':late(r)}">
    <div>
     <strong>{{r.name}} · {{crewTeam(r)}}</strong>
     <span><template v-if="r.work_name">{{r.work_name}} · </template>cần {{formatDate(needed(r))}}<b v-if="late(r)" class="issue-queue__late"> · Quá hạn chưa cấp</b></span>
     <span v-if="blockList(r)">Lô {{blockList(r)}}</span>
     <span>{{r.warehouse_name||r.warehouse}}<template v-if="(r.open_lines??r.lines_left)!=null"> · còn {{r.open_lines??r.lines_left}} dòng</template><template v-if="r.approved_by_name||r.approver_name"> · duyệt: {{r.approved_by_name||r.approver_name}}</template><template v-if="r.held"> · Kho đang lập phiếu</template></span>
    </div>
    <UiButton type="button" @click="issue(r)">Lập phiếu xuất</UiButton>
   </article>
  </div>
 </ModalForm>
</template>

<style>
.issue-queue{display:grid;gap:8px}
.issue-queue__card{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:10px 12px;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-info);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.issue-queue__card>div{display:grid;gap:2px;min-width:0;flex:1 1 260px}
.issue-queue__card strong{color:var(--lotus-text-strong)}
.issue-queue__card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.issue-queue__card.is-late{border-left-color:var(--lotus-danger)}
.issue-queue__late{color:var(--lotus-danger)}
</style>

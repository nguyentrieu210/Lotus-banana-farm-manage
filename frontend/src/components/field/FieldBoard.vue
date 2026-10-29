<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import DataTable from '../DataTable.vue'
import LotusField from '../form/LotusField.vue'
import {formatDate} from '../../format'
import {assignmentStates,boardRows,amountText} from '../../field-report-model.js'
// Lô × việc for one đội and month: every lô of the đội down the side, every việc given in the month across, and in each
// cell the phiếu giao with tổ and state, so the đội trưởng sees which lô still lacks which việc.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},month:{type:String,required:true},mobile:Boolean})
const emit=defineEmits(['update:month'])
const board=ref(null),loading=ref(false),error=ref('')
const rows=computed(()=>boardRows(board.value))
const works=computed(()=>board.value?.works||[])
async function load(){
 if(!props.farm||!props.crew||!props.month)return
 loading.value=true;error.value=''
 try{board.value=await call('lotus_farm.field_report.board',{farm:props.farm,crew:props.crew,month:props.month})}
 catch(e){error.value=e.message;board.value=null}
 finally{loading.value=false}
}
watch(()=>[props.farm,props.crew,props.month],load,{immediate:true})
const cellText=c=>c.team_name+' · '+(c.display==='Done'?'xong '+formatDate(c.done_date):assignmentStates[c.display]||c.display)
const columns=computed(()=>[
 {field:'block_code',headerName:'Lô',pinned:'left',minWidth:80,valueGetter:p=>p.data.block_code+' · '+amountText(p.data.area_ha)+' ha'},
 ...works.value.map((w,i)=>({field:'work_'+i,headerName:w.work_name,minWidth:170,sortable:false,
  valueGetter:p=>(p.data.cells[w.name]||[]).map(cellText).join(' / '),
  cellClass:p=>{const c=(p.data.cells[w.name]||[])[0];return c?'field-board__cell field-board__cell--'+String(c.display).toLowerCase():''}})),
])
</script>

<template>
 <section class="field-board" :aria-busy="loading">
  <div class="field-board__bar">
   <LotusField :model-value="month" type="month" label="Tháng" :mobile="mobile" @update:model-value="emit('update:month',$event)"/>
   <p class="lotus-form-note">Mỗi ô là phiếu giao của việc đó trên lô trong tháng (mới nhất trước). Ô trống: lô chưa giao việc đó.</p>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="board&&!works.length" class="lotus-form-note">Tháng này chưa giao việc nào.</p>
  <DataTable v-else-if="board" :rows="rows" :columns="columns" :loading="loading" row-key="key" storage-key="field-board" :totals="false" :selection-enabled="false" :paginate="false" export-title="Bảng lô × việc"/>
 </section>
</template>

<style>
.field-board{display:grid;gap:12px;min-width:0}
.field-board__bar{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.field-board__bar .lotus-form-note{margin:0;flex:1 1 240px}
.field-board__cell--done{background:var(--lotus-success-soft,var(--lotus-surface-muted))}
.field-board__cell--late{background:var(--lotus-danger-soft,var(--lotus-surface-muted));color:var(--lotus-danger)}
.field-board__cell--reported{background:var(--lotus-warning-soft,var(--lotus-surface-muted))}
</style>

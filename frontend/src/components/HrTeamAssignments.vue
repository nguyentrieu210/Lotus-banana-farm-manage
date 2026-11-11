<script setup>
import {computed,ref,watch} from 'vue'
import {workFarm} from '../work-farm'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import LotusField from './form/LotusField.vue'
import DataTable from './DataTable.vue'
import {hrCatalogLabel} from '../hr-catalog-labels'

const props=defineProps({
 company:{type:String,required:true},
 farms:{type:Array,default:()=>[]},
 teams:{type:Array,default:()=>[]},
 employees:{type:Array,default:()=>[]},
 manager:Boolean,busy:Boolean,
 confirm:{type:Function,required:true}  // in-app dialog (HrApp askConfirm), never window.confirm
})
const emit=defineEmits(['saved'])
const farm=ref('')
const targetTeam=ref('')
const filterTeam=ref('')
const query=ref('')
const checked=ref([])
const saving=ref(false)
const error=ref('')
const notice=ref('')
const activeEmployees=computed(()=>(props.employees||[]).filter(e=>e.status==='Active'))
const internalTeams=computed(()=>(props.teams||[]).filter(t=>t.active!==0 && t.lotus_team_type==='Internal'))
const farmOptions=computed(()=>props.farms.map(f=>({value:f.name,label:f.farm_name||f.name})))
const teamsInFarm=computed(()=>internalTeams.value.filter(t=>t.farm===farm.value).sort((a,b)=>String(a.team_name).localeCompare(String(b.team_name),'vi')))
const farmTeamOptions=computed(()=>[{value:'__remove__',label:'Bỏ phân tổ'},...teamsInFarm.value.map(t=>({value:t.name,label:t.team_name||t.name}))])
const lookup=computed(()=>Object.fromEntries(internalTeams.value.map(t=>[t.name,t.team_name||t.name])))
const allFarmEmployees=computed(()=>activeEmployees.value.filter(e=>e.lotus_farm===farm.value))
const missingFarm=computed(()=>activeEmployees.value.filter(e=>!e.lotus_farm).length)
const rows=computed(()=>{
 const q=query.value.trim().toLocaleLowerCase('vi-VN')
 return allFarmEmployees.value.filter(e=>(!filterTeam.value || (filterTeam.value==='__unassigned__'? !e.lotus_work_team:e.lotus_work_team===filterTeam.value))
  &&(!q||[e.name,e.employee_name,e.department,e.designation].some(v=>String(v||'').toLocaleLowerCase('vi-VN').includes(q))))
})
const selected=computed(()=>rows.value.filter(r=>checked.value.includes(r.name)))
const allChecked=computed(()=>rows.value.length>0&&rows.value.every(r=>checked.value.includes(r.name)))
const unassigned=computed(()=>allFarmEmployees.value.filter(e=>!e.lotus_work_team).length)
const assigned=computed(()=>allFarmEmployees.value.length-unassigned.value)
const counts=computed(()=>teamsInFarm.value.map(t=>({...t,count:allFarmEmployees.value.filter(e=>e.lotus_work_team===t.name).length})))
const teamFilterOptions=computed(()=>[{value:'__unassigned__',label:'Chưa phân tổ'},...farmTeamOptions.value])
watch(()=>props.farms,(farms)=>{
 if(!farms.some(f=>f.name===farm.value))farm.value=farms.find(f=>f.name===workFarm())?.name||farms[0]?.name||''
},{immediate:true})
watch(farm,()=>{targetTeam.value='';filterTeam.value='';checked.value=[];notice.value='';error.value=''})
watch([filterTeam,query],()=>{checked.value=[]})
watch(()=>props.employees,()=>{checked.value=[]})
function pickRows(list,yes){const names=list.map(r=>r.name);checked.value=yes?[...new Set([...checked.value,...names])]:checked.value.filter(n=>!names.includes(n))}
const peopleColumns=[
 {field:'employee_name',headerName:'Nhân viên',minWidth:190,flex:1.4},
 {field:'name',headerName:'Mã',minWidth:140},
 {field:'designation',headerName:'Chức danh',minWidth:150,valueFormatter:p=>hrCatalogLabel(p.value)||'Chưa có chức vụ'},
 {field:'department',headerName:'Phòng ban',minWidth:140,valueFormatter:p=>hrCatalogLabel(p.value)||'—'},
 {field:'lotus_work_team',headerName:'Tổ/đội hiện tại',minWidth:150,valueGetter:p=>lookup.value[p.data.lotus_work_team]||'Chưa phân tổ'}
]
function pickAll(){checked.value=allChecked.value?[]:rows.value.map(r=>r.name)}
function pick(name,yes){checked.value=yes?[...new Set([...checked.value,name])]:checked.value.filter(n=>n!==name)}
function chooseTeam(name){filterTeam.value=name;targetTeam.value=name;checked.value=[]}
async function save(){
 error.value='';notice.value=''
 if(!props.manager||saving.value||props.busy)return
 if(!selected.value.length){error.value='Chọn nhân viên cần phân tổ trước.';return}
 if(!targetTeam.value){error.value='Chọn tổ/đội nhận hoặc chọn Bỏ phân tổ.';return}
 if(!farmTeamOptions.value.some(t=>t.value===targetTeam.value)){error.value='Tổ/đội không thuộc vườn đang chọn.';return}
 const remove=targetTeam.value==='__remove__'
 const label=remove?'Chưa phân tổ':(lookup.value[targetTeam.value]||targetTeam.value)
 if(!await props.confirm('Xác nhận '+(remove?'bỏ phân':'phân')+' tổ '+label+' cho '+selected.value.length+' nhân viên?','Phân tổ/đội'))return
 saving.value=true
 try{
  const names=selected.value.map(e=>({name:e.name,modified:e.modified}))
  const result=await call('lotus_farm.hr_workspace.assign_teams',{
    company:props.company,farm:farm.value,team:remove?'':targetTeam.value,employees:names
  },true)
  notice.value='Đã cập nhật '+result.updated+' nhân viên; '+result.unchanged+' người không thay đổi.'
  checked.value=[]
  emit('saved')
 }catch(e){error.value=e.message||String(e)}finally{saving.value=false}
}
</script>

<template>
<section class="team-assign">
 <div class="team-assign__heading">
  <div><h2>Phân tổ/đội nhân viên</h2><p>Chọn vườn, chọn nhân viên và đưa vào tổ/đội nội bộ. Lưu tại hồ sơ nhân viên, không thay đổi lương hay ngày công.</p></div>
 </div>
 <p v-if="error" class="team-assign__error" role="alert">{{error}}</p>
 <p v-if="notice" class="team-assign__ok" role="status">{{notice}}</p>
 <div class="team-assign__filters">
  <LotusField v-model="farm" label="Vườn" :options="farmOptions" :searchable="false" :empty-option="null"/>
  <LotusField v-model="filterTeam" label="Xem nhân viên thuộc tổ" :options="teamFilterOptions" empty-option="Tất cả tổ/đội" :searchable="false"/>
  <LotusField v-model="query" label="Tìm nhân viên" placeholder="Tên, mã, chức vụ, phòng ban" type="search"/>
 </div>
 <div class="team-assign__stats">
  <span><b>{{allFarmEmployees.length}}</b> nhân viên trong vườn</span>
  <span><b>{{assigned}}</b> đã phân tổ</span>
  <span><b>{{unassigned}}</b> chưa phân tổ</span>
  <span><b>{{teamsInFarm.length}}</b> tổ/đội nội bộ</span>
 </div>
 <div v-if="missingFarm" class="team-assign__hint">{{missingFarm}} nhân viên chưa gán vườn trong hồ sơ. Cần xác định vườn trước khi phân tổ.</div>
 <div class="team-assign__workspace">
  <div class="team-assign__people">
   <div class="team-assign__list-head">
    <UiButton variant="outline" size="sm" :disabled="!manager||!rows.length||saving" @click="pickAll">{{allChecked?'Bỏ chọn tất cả':'Chọn tất cả '+rows.length+' người đang hiển thị'}}</UiButton>
    <b>Đã chọn {{selected.length}}</b>
   </div>
   <!-- Shared table: sort, column filters, export and the pager like every list; ticks persist across pages. -->
   <DataTable selection-enabled :rows="rows" :columns="peopleColumns" row-key="name" storage-key="hr-team-assign" :row-detail="false" :totals="false"
     empty="Không có nhân viên phù hợp bộ lọc." :selected-row-keys="checked"
     @row-selection-change="({id,selected:on})=>pick(id,on)" @page-selection-change="({rows:page,selected:on})=>pickRows(page,on)" @selection-clear="checked=[]"/>
  </div>
  <aside class="team-assign__side">
   <h3>Chuyển vào tổ/đội</h3>
   <LotusField v-model="targetTeam" label="Tổ/đội nhận" :options="farmTeamOptions" empty-option="Chọn tổ/đội" :searchable="false"/>
   <p>Chỉ thay đổi tổ/đội của <b>{{selected.length}}</b> nhân viên đã chọn, không chuyển vườn và không chấm công tự động.</p>
   <UiButton block :disabled="!manager||saving||busy||!selected.length||!targetTeam" :loading="saving" @click="save">Lưu phân tổ ({{selected.length}})</UiButton>
   <h3>Danh mục tổ/đội của vườn</h3>
   <div v-if="!counts.length" class="team-assign__empty">Chưa có tổ/đội nội bộ ở vườn này.</div>
   <button v-for="team in counts" :key="team.name" type="button" class="team-assign__team-item" :class="{'is-active':filterTeam===team.name}" @click="chooseTeam(team.name)">
    <span>{{team.team_name}}</span><b>{{team.count}} người</b>
   </button>
  </aside>
 </div>
</section>
</template>

<style scoped>
.team-assign{display:grid;gap:14px;padding:4px 0 24px}
.team-assign__heading h2{margin:0 0 4px;font-size:1.2rem}
.team-assign__heading p,.team-assign__side p,.team-assign__hint{margin:0;color:var(--lotus-muted);font-size:.85rem}
.team-assign__filters{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:10px}
.team-assign__stats{display:flex;flex-wrap:wrap;gap:10px}
.team-assign__stats span{padding:8px 12px;border:1px solid var(--lotus-border);border-radius:8px;background:var(--lotus-surface);font-size:.85rem}
.team-assign__stats b{font-variant-numeric:tabular-nums}
.team-assign__workspace{display:grid;grid-template-columns:minmax(0,2fr) minmax(250px,1fr);gap:14px}
.team-assign__people,.team-assign__side{border:1px solid var(--lotus-border);border-radius:10px;background:var(--lotus-surface);overflow:hidden}
.team-assign__people{display:grid;gap:8px;padding:10px;min-width:0}
.team-assign__list-head{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:.85rem}
.team-assign label{display:flex;align-items:center;gap:10px;cursor:pointer}
.team-assign input[type=checkbox]{width:17px;height:17px;accent-color:var(--lotus-primary);flex-shrink:0}
.team-assign__person{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:9px 12px;border-bottom:1px solid var(--lotus-border)}
.team-assign__person label{min-width:0}.team-assign__person strong,.team-assign__person small{display:block}
.team-assign__person small{color:var(--lotus-muted);font-size:.76rem}
.team-assign__team{color:var(--lotus-muted);font-size:.8rem;text-align:right;max-width:40%}
.team-assign__side{padding:14px;display:flex;flex-direction:column;gap:10px;align-self:start;max-height:65vh;overflow:auto}
.team-assign__side h3{margin:8px 0 0;font-size:.95rem}
.team-assign__team-item{display:flex;justify-content:space-between;gap:10px;padding:8px 10px;border:1px solid var(--lotus-border);border-radius:7px;background:var(--lotus-surface);font:inherit;font-size:.83rem;text-align:left;cursor:pointer}
.team-assign__team-item:hover,.team-assign__team-item.is-active{border-color:var(--lotus-primary);background:var(--lotus-soft)}
.team-assign__team-item b{white-space:nowrap}
.team-assign__empty{padding:20px;color:var(--lotus-muted);font-size:.88rem}
.team-assign__error{color:var(--lotus-danger)}.team-assign__ok{color:var(--lotus-success)}
@media(max-width:850px){.team-assign__filters{grid-template-columns:1fr 1fr}.team-assign__workspace{grid-template-columns:1fr}}
@media(max-width:530px){.team-assign__filters{grid-template-columns:1fr}.team-assign__person{align-items:flex-start;flex-direction:column;gap:5px}}
</style>

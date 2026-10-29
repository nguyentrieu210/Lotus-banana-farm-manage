<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
import ModalForm from '../form/ModalForm.vue'
import ReasonDialog from '../form/ReasonDialog.vue'
import WorkspaceSummaryStrip from '../WorkspaceSummaryStrip.vue'
import {Button as UiButton} from '../ui/button'
import {useReasonDialog} from '../../use-reason-dialog'
import {unitLabel} from '../../units'
import {formatDate} from '../../format'
import {newLine,lineFromAssignment,payload,preview,totals,ribbonCount,colourStages,payKinds,payShort,locations,reportStates,sections,assignmentStates,money,amountText} from '../../field-report-model.js'
// One đội's report for one day (báo cáo ngày). Việc vườn is reported on the phiếu giao (giao việc theo lô) the report
// lists ready to fill; công nhật outside a phiếu is added freely; chăm buồng is counted by lô and ribbon colour on the
// lots each tổ holds. Tổ trưởng edit their own tổ's lines; the đội trưởng edits all lines, the weather, and confirms or
// returns the day. Shared by the desktop workspace and the /work phone app (`mobile`).
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},date:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['changed','busy-change'])
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const report=ref(null),lines=ref([]),weather=ref(''),busy=ref(false),error=ref(''),notice=ref(''),saved=ref('')
const reason=useReasonDialog()
const detail=ref(null),detailOpen=ref(false)

const rights=computed(()=>report.value?.rights||{})
const locked=computed(()=>report.value?.state==='Confirmed')
const crewTeams=computed(()=>props.setup.teams.filter(t=>t.lotus_parent_team===props.crew&&t.active))
const myTeams=computed(()=>rights.value.supervisor?crewTeams.value:crewTeams.value.filter(t=>(rights.value.teams||[]).includes(t.name)))
const crewDoc=computed(()=>props.setup.crews.find(c=>c.name===props.crew))
const zones=computed(()=>crewDoc.value?.zones||[])
const blocks=computed(()=>Object.fromEntries(props.setup.blocks.filter(b=>zones.value.includes(b.zone)).map(b=>[b.name,b])))
const ctx=computed(()=>({rates:props.setup.rates,blocks:blocks.value,day:props.date}))
const works=computed(()=>Object.fromEntries(props.setup.works.map(w=>[w.name,w])))
const stage=work=>works.value[work]?.lotus_bunch_stage||''
const tasks=computed(()=>Object.fromEntries((report.value?.assignments||[]).map(a=>[a.name,a])))
const own=computed(()=>lines.value.filter(l=>l.editable!==false))
const others=computed(()=>lines.value.filter(l=>l.editable===false))
function part(pick){return computed({get:()=>own.value.filter(pick),set:rows=>{lines.value=[...own.value.filter(l=>!pick(l)),...rows,...others.value]}})}
const taskLines=part(l=>l.section!=='Bunch'&&!!l.assignment)
const freeLines=part(l=>l.section!=='Bunch'&&!l.assignment)
const bunchLines=part(l=>l.section==='Bunch')
const dirty=computed(()=>!!report.value&&snapshot()!==saved.value)
const sum=computed(()=>totals(lines.value,ctx.value))
const ribbonOpts=computed(()=>({stage,ribbon:report.value?.ribbon?.name||null,cut:report.value?.bunch_cut||{},done:report.value?.bunch_done||{}}))
const overCut=computed(()=>own.value.filter(l=>ribbonCount(l,lines.value,ribbonOpts.value)?.over).length)
const summary=computed(()=>[
 {label:'Trạng thái',value:reportStates[report.value?.state]||'Nháp'},
 {label:'Số dòng',value:sum.value.lines},
 {label:'Tổng công',value:amountText(sum.value.workdays)},
 {label:'Việc xong',value:sum.value.done},
 {label:'Tiền khoán',value:money(sum.value.amount)},
 ...(sum.value.low?[{label:'Chưa đạt ngày công',value:sum.value.low+' dòng'}]:[]),
 ...(overCut.value?[{label:'Vượt số cắt bắp',value:overCut.value+' dòng'}]:[]),
])

const teamOptions=computed(()=>myTeams.value.map(t=>({value:t.name,label:t.team_name+(t.leader_name?' · '+t.leader_name:'')})))
const blockOptions=computed(()=>Object.values(blocks.value).map(b=>({value:b.name,label:b.block_code+' · '+amountText(b.area_ha)+' ha · '+amountText(b.trees)+' cây'})))
const zoneOptions=computed(()=>zones.value.map(z=>({value:z,label:'Khu '+z})))
const workOptions=section=>props.setup.works.filter(w=>w.section===section).map(w=>({value:w.name,label:w.work_name}))
const teamName=name=>props.setup.teams.find(t=>t.name===name)?.team_name||'—'
const blockCode=name=>props.setup.blocks.find(b=>b.name===name)?.block_code||name||''
const placeText=l=>l.location==='Zone'?'Khu '+l.zone:l.location==='Blocks'?String(l.blocks||'').split(',').map(blockCode).join(', '):blockCode(l.farm_block)
// Lots a tổ chăm buồng holds today; công khoán buồng only on those, công nhật anywhere in the đội's khu.
const heldBy=computed(()=>report.value?.bunch_lots||{})
const bunchBlockOptions=row=>row.pay_kind==='Piece'?blockOptions.value.filter(o=>heldBy.value[o.value]===row.work_team):blockOptions.value
const heldText=computed(()=>myTeams.value.map(t=>({team:t.team_name,lots:Object.entries(heldBy.value).filter(([,team])=>team===t.name).map(([b])=>blockCode(b))})).filter(x=>x.lots.length))
const ribbonChoices=computed(()=>(report.value?.ribbon_options||[]).map(t=>({value:t.name,label:t.label+' · tuần '+t.week})))

function taskTitle(row){const t=tasks.value[row.assignment];return blockCode(row.farm_block)+' · '+(works.value[row.work_type]?.work_name||t?.work_type||'')}
function taskMeta(row){
 const t=tasks.value[row.assignment]||{}
 const bits=[teamName(row.work_team)]
 if(t.due_date)bits.push('hạn '+formatDate(t.due_date))
 if(t.progress?.days)bits.push('đã báo '+t.progress.days+' ngày, '+amountText(t.progress.workdays)+' công')
 return bits.join(' · ')
}
function taskState(row){const t=tasks.value[row.assignment];return t?.display==='Late'||t?.display==='Reported'?assignmentStates[t.display]:''}
function qtyHint(row){
 const p=preview(row,ctx.value),w=works.value[row.work_type]
 if(p.missingPrice)return 'Chưa có giá khoán cho việc này'
 const unit=unitLabel(p.price?.uom||w?.uom)||''
 if(p.byLot)return 'Hôm nay làm được · cả lô '+amountText(p.whole)+' '+unit
 return unit
}
function moneyText(row){
 const p=preview(row,ctx.value)
 if(row.pay_kind!=='Piece')return 'Theo chấm công'
 if(p.byLot&&!row.done)return 'Tính khi Xong'
 return money(p.amount)
}
function ribbonHint(row){
 const c=ribbonCount(row,lines.value,ribbonOpts.value)
 return c?'Đã cắt bắp '+amountText(c.cut)+' · cộng dồn '+amountText(c.total):''
}
const taskColumns=computed(()=>[
 {field:'task',label:'Lô · việc',width:'minmax(190px,1.6fr)'},
 {field:'pay_kind',label:'Loại công',type:'select',options:payKinds,searchable:false,width:'minmax(112px,0.7fr)'},
 {field:'workdays_am',label:'Công sáng',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'workdays_pm',label:'Công chiều',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'qty',label:'Khối lượng',type:'number',width:'minmax(104px,0.7fr)',hint:qtyHint,props:{min:0}},
 {field:'done',label:'Xong lô',type:'checkbox',width:'80px'},
 {field:'money',label:'Thành tiền',width:'110px'},
 {field:'more',label:'Thêm',width:'112px'},
])
const freeColumns=computed(()=>[
 {field:'work_team',label:'Tổ',type:'select',options:teamOptions.value,searchable:false,width:'minmax(120px,0.9fr)',visible:()=>teamOptions.value.length>0},
 {field:'work_type',label:'Công việc',options:workOptions('Field'),required:true,width:'minmax(150px,1.3fr)'},
 {field:'location',label:'Vị trí',type:'select',options:locations,searchable:false,width:'minmax(105px,0.7fr)'},
 {field:'place',label:'Lô / khu',width:'minmax(130px,0.9fr)'},
 {field:'workdays_am',label:'Công sáng',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'workdays_pm',label:'Công chiều',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'qty',label:'Khối lượng',type:'number',width:'minmax(104px,0.7fr)',hint:qtyHint,props:{min:0}},
 {field:'more',label:'Thêm',width:'112px'},
])
const bunchColumns=computed(()=>[
 {field:'work_team',label:'Tổ',type:'select',options:teamOptions.value,searchable:false,width:'minmax(120px,0.9fr)',required:row=>row.pay_kind==='Piece',visible:()=>teamOptions.value.length>0},
 {field:'work_type',label:'Công đoạn',options:workOptions('Bunch'),required:true,width:'minmax(150px,1.3fr)'},
 {field:'pay_kind',label:'Loại công',type:'select',options:payKinds,searchable:false,width:'minmax(112px,0.7fr)'},
 {field:'place',label:'Lô',width:'minmax(120px,0.8fr)'},
 {field:'ribbon',label:'Màu dây',width:'minmax(130px,0.9fr)'},
 {field:'workdays_am',label:'Công sáng',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'workdays_pm',label:'Công chiều',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'qty',label:'Số buồng / cây',type:'number',width:'minmax(104px,0.7fr)',props:{min:0}},
 {field:'money',label:'Thành tiền',width:'110px'},
 {field:'more',label:'Thêm',width:'112px'},
])

function shape(row){return {...row,blocks:row.blocks||'',zone:row.zone||'',done:row.done?1:0,materials:(row.materials||[]).map(m=>({...m}))}}
function snapshot(){return JSON.stringify([weather.value,payload(lines.value)])}
function apply(data){
 report.value=data;weather.value=data.weather||''
 const stored=(data.lines||[]).map(shape)
 const reported=new Set(stored.map(l=>l.assignment).filter(Boolean))
 // Every open phiếu the tổ has not reported today comes ready to fill; rows left empty are not saved.
 const ready=data.state==='Confirmed'?[]:(data.assignments||[]).filter(a=>a.state==='Open'&&!reported.has(a.name)).map(a=>lineFromAssignment(a,ctx.value))
 lines.value=[...stored,...ready]
 saved.value=snapshot()
}
async function load(){
 if(!props.farm||!props.crew||!props.date)return
 busy.value=true;error.value='';notice.value=''
 try{apply(await api('get',{farm:props.farm,crew:props.crew,date:props.date}))}
 catch(e){error.value=e.message;report.value=null}
 finally{busy.value=false}
}
watch(()=>[props.farm,props.crew,props.date],load,{immediate:true})
watch(busy,v=>emit('busy-change',v))

function add(section){return newLine(section,myTeams.value.length===1?myTeams.value[0].name:'')}
function pickedWork(row){
 const s=stage(row.work_type)
 if(s==='Cut Bud')row.bunch_tag=report.value?.ribbon?.name||null
 else if(!colourStages.includes(s))row.bunch_tag=null
 else if(!row.bunch_tag)row.bunch_tag=ribbonChoices.value[1]?.value||ribbonChoices.value[0]?.value||null
}
async function save(){
 if(busy.value||locked.value)return
 busy.value=true;error.value='';notice.value=''
 try{
  apply(await api('save',{farm:props.farm,crew:props.crew,date:props.date,lines:payload(lines.value),weather:rights.value.supervisor?weather.value:null,expected_modified:report.value?.modified},true))
  notice.value='Đã lưu báo cáo.';emit('changed')
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function act(name,extra={}){
 busy.value=true;error.value='';notice.value=''
 try{apply(await api(name,{name:report.value.name,expected_modified:report.value.modified,...extra},true));emit('changed');return true}
 catch(e){error.value=e.message;return false}
 finally{busy.value=false}
}
async function confirmDay(){if(await act('confirm'))notice.value='Đã xác nhận báo cáo. Việc báo Xong đã đóng phiếu giao; tiền khoán của ngày được tính vào tháng.'}
async function returnDay(){const text=await reason.ask('Trả lại báo cáo cho tổ trưởng sửa','Cần sửa gì');if(text&&await act('return_report',{reason:text}))notice.value='Đã trả lại báo cáo.'}
async function reopenDay(){const text=await reason.ask('Mở lại báo cáo đã xác nhận','Lý do mở lại');if(text&&await act('reopen',{reason:text}))notice.value='Đã mở lại. Phiếu giao báo Xong trong ngày này mở lại theo. Sửa xong thì xác nhận lại.'}

function openDetail(row){detail.value={row,comment:row.comment||'',proposal:row.proposal||'',note:row.note||'',under_norm_reason:row.under_norm_reason||'',materials:(row.materials||[]).map(m=>({...m}))};detailOpen.value=true}
function saveDetail(){
 const d=detail.value
 Object.assign(d.row,{comment:d.comment,proposal:d.proposal,note:d.note,under_norm_reason:d.under_norm_reason,materials:d.materials.filter(m=>m.item_code)})
 detailOpen.value=false
}
const itemOptions=search=>api('item_options',{search}).then(rows=>rows.map(r=>({value:r.name,label:r.item_name+' ('+(unitLabel(r.stock_uom)||r.stock_uom)+')'})))
const materialColumns=[{field:'item_code',label:'Vật tư',fetchOptions:itemOptions,required:true,width:'minmax(200px,1.6fr)'},{field:'qty',label:'Số lượng',type:'number',width:'110px',props:{min:0}}]
function moreLabel(row){const n=(row.materials||[]).filter(m=>m.item_code).length;return (n?'Vật tư '+n+' · ':'')+(row.comment||row.note||row.proposal?'Ghi chú ✓':'Ghi chú')}
const lowFirst=row=>preview(row,ctx.value).low&&!row.under_norm_reason
defineExpose({hasChanges:()=>dirty.value,reload:load})
</script>

<template>
 <section class="field-report" :class="{'field-report--mobile':mobile}" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <template v-if="report">
   <p v-if="report.state==='Returned'" class="field-report__warning" role="alert">Đội trưởng trả lại: {{report.return_reason}}</p>
   <p v-if="report.overdue&&report.name" class="lotus-list-page__error" role="alert">Quá hạn xác nhận (10 giờ sáng hôm sau).</p>
   <p v-if="!crewTeams.length" class="field-report__warning" role="status">Đội chưa có tổ nào. Vào Báo cáo ngày → Đội, tổ &amp; lô để xếp tổ, rồi giao việc theo lô; công nhật vẫn ghi được.</p>
   <WorkspaceSummaryStrip :items="summary"/>
   <FormGrid :columns="mobile?1:3">
    <LotusField v-model="weather" label="Thời tiết" placeholder="Sáng nắng, chiều mưa…" :readonly="!rights.supervisor||locked" :mobile="mobile" maxlength="200"/>
    <div class="field-report__ribbon"><span>Màu dây cắt bắp hôm nay</span><strong>{{report.ribbon?.label||'Chưa có lịch màu'}}</strong></div>
    <div v-if="locked" class="field-report__ribbon"><span>Đã xác nhận</span><strong>{{report.confirmed_by_name}} · {{String(report.confirmed_at).slice(0,16)}}</strong></div>
   </FormGrid>

   <FormSection title="Việc được giao" description="Các lô đội trưởng đã giao cho tổ. Ghi công và khối lượng làm được hôm nay; làm hết lô thì tích Xong lô. Khoán theo ha / số cây trả cả lô khi đội trưởng xác nhận ngày báo Xong. Dòng để trống không lưu.">
    <LineItemsEditor v-model="taskLines" :columns="taskColumns" fixed :min="0" :readonly="locked" :mobile="mobile" title="Phiếu giao" empty-text="Chưa có việc nào đang giao cho tổ. Đội trưởng giao ở mục Giao việc theo lô.">
     <template #cell-task="{row}"><div class="field-report__task"><strong>{{taskTitle(row)}}</strong><span>{{taskMeta(row)}}</span><em v-if="taskState(row)">{{taskState(row)}}</em></div></template>
     <template #cell-money="{row}"><span class="field-report__money" :class="{'field-report__money--warn':preview(row,ctx).missingPrice}">{{moneyText(row)}}</span></template>
     <template #cell-more="{row}"><UiButton type="button" size="sm" :variant="lowFirst(row)?'default':'outline'" @click="openDetail(row)">{{lowFirst(row)?'Ghi lý do chưa đạt':moreLabel(row)}}</UiButton></template>
    </LineItemsEditor>
   </FormSection>

   <FormSection title="Công nhật khác" description="Việc công nhật ngoài phiếu giao (sửa ống nước, cào lá cả khu…). Công khoán việc vườn phải có phiếu giao.">
    <LineItemsEditor v-model="freeLines" :columns="freeColumns" :new-row="()=>add('Field')" :min="0" :max="200" :readonly="locked" :mobile="mobile" title="Dòng công nhật" add-label="Việc CN" empty-text="Không có việc công nhật ngoài phiếu.">
     <template #cell-place="{row,index}">
      <LotusField v-if="row.location==='Block'" v-model="row.farm_block" :aria-label="'Lô dòng '+(index+1)" :label="mobile?'Lô':undefined" :options="blockOptions" :readonly="locked" :mobile="mobile" required/>
      <LotusField v-else-if="row.location==='Zone'" v-model="row.zone" type="select" :searchable="false" :aria-label="'Khu dòng '+(index+1)" :label="mobile?'Khu':undefined" :options="zoneOptions" :readonly="locked" :mobile="mobile" required/>
      <LotusField v-else v-model="row.blocks" :aria-label="'Các lô dòng '+(index+1)" :label="mobile?'Các lô':undefined" placeholder="A1,A2,A8" hint="Mã lô, cách nhau dấu phẩy" :readonly="locked" :mobile="mobile"/>
     </template>
     <template #cell-more="{row}"><UiButton type="button" size="sm" :variant="lowFirst(row)?'default':'outline'" @click="openDetail(row)">{{lowFirst(row)?'Ghi lý do chưa đạt':moreLabel(row)}}</UiButton></template>
    </LineItemsEditor>
   </FormSection>

   <FormSection :title="sections.Bunch" :description="'Ghi số buồng theo lô. Cắt bắp hôm nay buộc màu '+(report.ribbon?.label||'(chưa có lịch)')+'; bao buồng, tỉa trái, chống đổ chọn màu của lứa đang làm. Công khoán buồng chỉ trên lô đã giao chăm buồng cho tổ.'">
    <p v-if="heldText.length" class="field-report__held"><span v-for="h in heldText" :key="h.team"><strong>{{h.team}}</strong> chăm buồng {{h.lots.join(', ')}}</span></p>
    <LineItemsEditor v-model="bunchLines" :columns="bunchColumns" :new-row="()=>add('Bunch')" :min="0" :max="200" :readonly="locked" :mobile="mobile" title="Dòng chăm sóc buồng" add-label="Thêm công đoạn" empty-text="Chưa có công đoạn buồng nào." @select="({row,field})=>field==='work_type'&&pickedWork(row)">
     <template #cell-place="{row,index}"><LotusField v-model="row.farm_block" :aria-label="'Lô dòng buồng '+(index+1)" :label="mobile?'Lô':undefined" :options="bunchBlockOptions(row)" :readonly="locked" :mobile="mobile" required/></template>
     <template #cell-ribbon="{row,index}">
      <span v-if="stage(row.work_type)==='Cut Bud'" class="field-report__money">{{report.ribbon?.label||'Chưa có lịch màu'}}</span>
      <LotusField v-else-if="colourStages.includes(stage(row.work_type))" v-model="row.bunch_tag" type="select" :searchable="false" :aria-label="'Màu dây dòng buồng '+(index+1)" :label="mobile?'Màu dây':undefined" :options="ribbonChoices" :hint="ribbonHint(row)" :error="ribbonCount(row,lines,ribbonOpts)?.over?(report.cap_blocks?'Vượt số đã cắt bắp':'Vượt số đã cắt bắp — đội trưởng xem lại'):''" :readonly="locked" :mobile="mobile" required/>
      <span v-else class="field-report__money">—</span>
     </template>
     <template #cell-money="{row}"><span class="field-report__money">{{moneyText(row)}}</span></template>
     <template #cell-more="{row}"><UiButton type="button" size="sm" variant="outline" @click="openDetail(row)">{{moreLabel(row)}}</UiButton></template>
    </LineItemsEditor>
   </FormSection>

   <FormSection v-if="others.length" title="Dòng của tổ khác" description="Chỉ xem; tổ trưởng của tổ đó hoặc đội trưởng mới sửa được.">
    <ul class="field-report__others"><li v-for="l in others" :key="l.line_id"><strong>{{teamName(l.work_team)}}</strong> · {{works[l.work_type]?.work_name||l.work_type}} · {{payShort[l.pay_kind]}} · {{placeText(l)}} · {{amountText(l.workdays)}} công · {{amountText(l.qty)}}{{l.done?' · Xong lô':''}}{{l.ribbon?' · '+l.ribbon:''}}</li></ul>
   </FormSection>

   <footer class="field-report__actions">
    <UiButton v-if="!locked" type="button" :disabled="busy||!dirty" @click="save">{{busy?'Đang lưu…':'Lưu báo cáo'}}</UiButton>
    <UiButton v-if="rights.can_confirm&&!locked&&report.name" type="button" variant="outline" :disabled="busy||dirty" :title="dirty?'Lưu trước khi xác nhận':''" @click="confirmDay">Xác nhận báo cáo</UiButton>
    <UiButton v-if="rights.can_confirm&&!locked&&report.name" type="button" variant="ghost" :disabled="busy" @click="returnDay">Trả lại</UiButton>
    <UiButton v-if="rights.can_reopen&&locked" type="button" variant="outline" :disabled="busy" @click="reopenDay">Mở lại để sửa</UiButton>
    <span v-if="dirty" class="field-report__dirty">Có thay đổi chưa lưu</span>
   </footer>
  </template>
  <p v-else-if="busy" class="lotus-form-note" role="status">Đang tải báo cáo…</p>

  <ModalForm v-model="detailOpen" title="Vật tư và ghi chú của dòng" width="720px" submit-label="Xong" :readonly="locked" @submit="saveDetail">
   <template v-if="detail">
    <LotusField v-if="preview(detail.row,ctx).low||detail.under_norm_reason" v-model="detail.under_norm_reason" type="textarea" label="Lý do chưa đạt ngày công" required maxlength="500" :mobile="mobile" hint="Ví dụ: mưa nghỉ 15h30, công nhân mới, cây khô nhiều"/>
    <LineItemsEditor v-model="detail.materials" :columns="materialColumns" :new-row="()=>({item_code:'',qty:null})" :min="0" :max="4" :readonly="locked" :mobile="mobile" title="Vật tư tiêu hao (tối đa 4)" add-label="Thêm vật tư" empty-text="Không dùng vật tư."/>
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="detail.comment" type="textarea" label="Nhận xét" maxlength="500" :readonly="locked" :mobile="mobile"/>
     <LotusField v-model="detail.proposal" type="textarea" label="Đề xuất giải pháp" maxlength="500" :readonly="locked" :mobile="mobile"/>
     <LotusField v-model="detail.note" type="textarea" label="Ghi chú (lý do, nguyên nhân)" maxlength="500" :readonly="locked" :mobile="mobile"/>
    </FormGrid>
   </template>
  </ModalForm>
  <ReasonDialog :dialog="reason"/>
 </section>
</template>

<style>
.field-report{display:grid;gap:14px;min-width:0}
.field-report__notice{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-success-soft,var(--lotus-surface-muted));color:var(--lotus-text-strong);font-size:var(--lotus-text-sm)}
.field-report__warning{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-warning-soft,var(--lotus-surface-muted));color:var(--lotus-text-strong);font-size:var(--lotus-text-sm)}
.field-report__ribbon{display:grid;gap:4px;font-size:var(--lotus-text-sm)}
.field-report__ribbon span{color:var(--lotus-muted)}
.field-report__task{display:grid;gap:2px;padding-top:4px;min-width:0;font-size:var(--lotus-text-sm)}
.field-report__task strong{color:var(--lotus-text-strong);font-weight:600}
.field-report__task span{color:var(--lotus-muted)}
.field-report__task em{font-style:normal;color:var(--lotus-danger)}
.field-report__held{margin:0;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.field-report__held strong{color:var(--lotus-text-strong);font-weight:550}
.field-report__money{display:inline-block;padding-top:8px;font-variant-numeric:tabular-nums;white-space:nowrap}
.field-report__money--warn{color:var(--lotus-danger)}
.field-report__others{margin:0;padding-left:18px;display:grid;gap:4px;font-size:var(--lotus-text-sm)}
.field-report__actions{position:sticky;bottom:0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 0;background:var(--lotus-surface);border-top:1px solid var(--lotus-border)}
.field-report__dirty{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-report--mobile .field-report__money,.field-report--mobile .field-report__task{padding-top:0}
</style>

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
import {newLine,payload,preview,totals,payKinds,payShort,locations,reportStates,sections,basisLabels,money,amountText} from '../../field-report-model.js'
// One đội's report for one day (báo cáo ngày). Tổ trưởng edit their own tổ's lines; the đội trưởng edits all lines,
// the weather, and confirms or returns the day. Shared by the desktop workspace and the /work phone app (`mobile`).
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
const own=computed(()=>lines.value.filter(l=>l.editable!==false))
const others=computed(()=>lines.value.filter(l=>l.editable===false))
const fieldLines=computed({get:()=>own.value.filter(l=>l.section!=='Bunch'),set:rows=>{lines.value=[...rows,...own.value.filter(l=>l.section==='Bunch'),...others.value]}})
const bunchLines=computed({get:()=>own.value.filter(l=>l.section==='Bunch'),set:rows=>{lines.value=[...own.value.filter(l=>l.section!=='Bunch'),...rows,...others.value]}})
const dirty=computed(()=>!!report.value&&snapshot()!==saved.value)
const sum=computed(()=>totals(lines.value,ctx.value))
const summary=computed(()=>[
 {label:'Trạng thái',value:reportStates[report.value?.state]||'Nháp'},
 {label:'Số dòng',value:sum.value.lines},
 {label:'Tổng công',value:amountText(sum.value.workdays)},
 {label:'Tiền khoán',value:money(sum.value.amount)},
 ...(sum.value.low?[{label:'Chưa đạt ngày công',value:sum.value.low+' dòng'}]:[]),
])

const teamOptions=computed(()=>myTeams.value.map(t=>({value:t.name,label:t.team_name+(t.leader_name?' · '+t.leader_name:'')})))
const blockOptions=computed(()=>Object.values(blocks.value).map(b=>({value:b.name,label:b.block_code+' · '+amountText(b.area_ha)+' ha · '+amountText(b.trees)+' cây'})))
const zoneOptions=computed(()=>zones.value.map(z=>({value:z,label:'Khu '+z})))
const workOptions=section=>props.setup.works.filter(w=>w.section===section).map(w=>({value:w.name,label:w.work_name}))
const teamName=name=>props.setup.teams.find(t=>t.name===name)?.team_name||'—'
const blockCode=name=>props.setup.blocks.find(b=>b.name===name)?.block_code||name||''
const placeText=l=>l.location==='Zone'?'Khu '+l.zone:l.location==='Blocks'?String(l.blocks||'').split(',').map(blockCode).join(', '):blockCode(l.farm_block)

function qtyHint(row){
 const p=preview(row,ctx.value),w=works.value[row.work_type]
 if(p.missingPrice)return 'Chưa có giá khoán cho việc này'
 const unit=unitLabel(p.price?.uom||w?.uom)||''
 if(p.whole!=null)return (row.whole_lot||row.qty==null||row.qty==='')?'Cả lô: '+amountText(p.whole)+' '+unit:'Cả lô '+amountText(p.whole)+' · '+(basisLabels[p.price.basis]||'')
 return unit
}
const columns=section=>[
 {field:'work_team',label:'Tổ',type:'select',options:teamOptions.value,searchable:false,width:'minmax(120px,0.9fr)',required:row=>row.pay_kind==='Piece',visible:()=>teamOptions.value.length>0},
 {field:'work_type',label:section==='Bunch'?'Công đoạn':'Công việc',options:workOptions(section),required:true,width:'minmax(150px,1.3fr)'},
 {field:'pay_kind',label:'Loại công',type:'select',options:payKinds,searchable:false,width:'minmax(112px,0.7fr)'},
 ...(section==='Bunch'?[]:[{field:'location',label:'Vị trí',type:'select',options:locations,searchable:false,width:'minmax(105px,0.7fr)',visible:row=>row.pay_kind!=='Piece'}]),
 {field:'place',label:'Lô / khu',width:'minmax(130px,0.9fr)'},
 {field:'workdays_am',label:'Công sáng',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'workdays_pm',label:'Công chiều',type:'number',width:'86px',props:{min:0,step:0.5}},
 {field:'qty',label:section==='Bunch'?'Số buồng':'Khối lượng',type:'number',width:'minmax(104px,0.7fr)',hint:qtyHint,props:{min:0}},
 {field:'money',label:'Thành tiền',width:'104px'},
 {field:'more',label:'Thêm',width:'112px'},
]

function shape(row){return {...row,blocks:row.blocks||'',zone:row.zone||'',materials:(row.materials||[]).map(m=>({...m})),qty:row.whole_lot?null:row.qty}}
function snapshot(){return JSON.stringify([weather.value,payload(lines.value)])}
function apply(data){
 report.value=data;weather.value=data.weather||''
 lines.value=(data.lines||[]).map(shape)
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
function pickedWork(row){const w=works.value[row.work_type];if(w&&row.section!==w.section)row.section=w.section}
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
async function confirmDay(){if(await act('confirm'))notice.value='Đã xác nhận báo cáo. Tiền khoán của ngày được tính vào tháng.'}
async function returnDay(){const text=await reason.ask('Trả lại báo cáo cho tổ trưởng sửa','Cần sửa gì');if(text&&await act('return_report',{reason:text}))notice.value='Đã trả lại báo cáo.'}
async function reopenDay(){const text=await reason.ask('Mở lại báo cáo đã xác nhận','Lý do mở lại');if(text&&await act('reopen',{reason:text}))notice.value='Đã mở lại. Sửa xong thì xác nhận lại.'}

function openDetail(row){detail.value={row,comment:row.comment||'',proposal:row.proposal||'',note:row.note||'',under_norm_reason:row.under_norm_reason||'',materials:(row.materials||[]).map(m=>({...m}))};detailOpen.value=true}
function saveDetail(){
 const d=detail.value
 Object.assign(d.row,{comment:d.comment,proposal:d.proposal,note:d.note,under_norm_reason:d.under_norm_reason,materials:d.materials.filter(m=>m.item_code)})
 detailOpen.value=false
}
const itemOptions=search=>api('item_options',{search}).then(rows=>rows.map(r=>({value:r.name,label:r.item_name+' ('+(unitLabel(r.stock_uom)||r.stock_uom)+')'})))
const materialColumns=[{field:'item_code',label:'Vật tư',fetchOptions:itemOptions,required:true,width:'minmax(200px,1.6fr)'},{field:'qty',label:'Số lượng',type:'number',width:'110px',props:{min:0}}]
function moreLabel(row){const n=(row.materials||[]).filter(m=>m.item_code).length;return (n?'Vật tư '+n+' · ':'')+(row.comment||row.note||row.proposal?'Ghi chú ✓':'Ghi chú')}
defineExpose({hasChanges:()=>dirty.value,reload:load})
</script>

<template>
 <section class="field-report" :class="{'field-report--mobile':mobile}" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <template v-if="report">
   <p v-if="report.state==='Returned'" class="field-report__warning" role="alert">Đội trưởng trả lại: {{report.return_reason}}</p>
   <p v-if="report.overdue" class="lotus-list-page__error" role="alert">Quá hạn xác nhận (10 giờ sáng hôm sau).</p>
   <p v-if="!crewTeams.length" class="field-report__warning" role="status">Đội chưa có tổ nào. Vào Báo cáo ngày → Đội, tổ &amp; lô để xếp tổ trước khi ghi công khoán; công nhật vẫn ghi được.</p>
   <WorkspaceSummaryStrip :items="summary"/>
   <FormGrid :columns="mobile?1:3">
    <LotusField v-model="weather" label="Thời tiết" placeholder="Sáng nắng, chiều mưa…" :readonly="!rights.supervisor||locked" :mobile="mobile" maxlength="200"/>
    <div class="field-report__ribbon"><span>Màu dây cắt bắp hôm nay</span><strong>{{report.ribbon?.label||'Chưa có lịch màu'}}</strong></div>
    <div v-if="locked" class="field-report__ribbon"><span>Đã xác nhận</span><strong>{{report.confirmed_by_name}} · {{String(report.confirmed_at).slice(0,16)}}</strong></div>
   </FormGrid>

   <FormSection :title="sections.Field" description="Công khoán ghi từng lô; để trống khối lượng là làm cả lô. Công nhật ghi được cả khu hoặc nhiều lô.">
    <LineItemsEditor v-model="fieldLines" :columns="columns('Field')" :new-row="()=>add('Field')" :min="0" :max="200" :readonly="locked" :mobile="mobile" title="Dòng công việc" add-label="Thêm việc" empty-text="Chưa có việc vườn nào." @select="({row,field})=>field==='work_type'&&pickedWork(row)">
     <template #cell-place="{row,index}">
      <LotusField v-if="row.pay_kind==='Piece'||row.location==='Block'" v-model="row.farm_block" :aria-label="'Lô dòng '+(index+1)" :label="mobile?'Lô':undefined" :options="blockOptions" :readonly="locked" :mobile="mobile" required/>
      <LotusField v-else-if="row.location==='Zone'" v-model="row.zone" type="select" :searchable="false" :aria-label="'Khu dòng '+(index+1)" :label="mobile?'Khu':undefined" :options="zoneOptions" :readonly="locked" :mobile="mobile" required/>
      <LotusField v-else v-model="row.blocks" :aria-label="'Các lô dòng '+(index+1)" :label="mobile?'Các lô':undefined" placeholder="A1,A2,A8" hint="Mã lô, cách nhau dấu phẩy" :readonly="locked" :mobile="mobile"/>
     </template>
     <template #cell-money="{row}"><span class="field-report__money" :class="{'field-report__money--warn':preview(row,ctx).missingPrice}">{{row.pay_kind==='Piece'?money(preview(row,ctx).amount):'Theo chấm công'}}</span></template>
     <template #cell-more="{row}"><UiButton type="button" size="sm" :variant="preview(row,ctx).low&&!row.under_norm_reason?'default':'outline'" @click="openDetail(row)">{{preview(row,ctx).low&&!row.under_norm_reason?'Ghi lý do chưa đạt':moreLabel(row)}}</UiButton></template>
    </LineItemsEditor>
   </FormSection>

   <FormSection :title="sections.Bunch" :description="'Chích bắp, cắt bắp, lặt hoa, bao buồng, chống đổ — ghi số buồng theo lô. Cắt bắp hôm nay buộc màu '+(report.ribbon?.label||'(chưa có lịch)')+'.'">
    <LineItemsEditor v-model="bunchLines" :columns="columns('Bunch')" :new-row="()=>add('Bunch')" :min="0" :max="200" :readonly="locked" :mobile="mobile" title="Dòng chăm sóc buồng" add-label="Thêm công đoạn" empty-text="Chưa có công đoạn buồng nào." @select="({row,field})=>field==='work_type'&&pickedWork(row)">
     <template #cell-place="{row,index}"><LotusField v-model="row.farm_block" :aria-label="'Lô dòng buồng '+(index+1)" :label="mobile?'Lô':undefined" :options="blockOptions" :readonly="locked" :mobile="mobile" required/></template>
     <template #cell-money="{row}"><span class="field-report__money">{{row.pay_kind==='Piece'?money(preview(row,ctx).amount):'Theo chấm công'}}<small v-if="works[row.work_type]?.lotus_bunch_stage==='Cut Bud'"> · {{report.ribbon?.label||'chưa có màu'}}</small></span></template>
     <template #cell-more="{row}"><UiButton type="button" size="sm" variant="outline" @click="openDetail(row)">{{moreLabel(row)}}</UiButton></template>
    </LineItemsEditor>
   </FormSection>

   <FormSection v-if="others.length" title="Dòng của tổ khác" description="Chỉ xem; tổ trưởng của tổ đó hoặc đội trưởng mới sửa được.">
    <ul class="field-report__others"><li v-for="l in others" :key="l.line_id"><strong>{{teamName(l.work_team)}}</strong> · {{works[l.work_type]?.work_name||l.work_type}} · {{payShort[l.pay_kind]}} · {{placeText(l)}} · {{amountText(l.workdays)}} công · {{amountText(l.qty)}} {{unitLabel(l.uom)}}<span v-if="l.ribbon"> · {{l.ribbon}}</span></li></ul>
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
    <LotusField v-if="preview(detail.row,ctx).low||detail.under_norm_reason" v-model="detail.under_norm_reason" type="textarea" label="Lý do chưa đạt ngày công" required maxlength="500" :mobile="mobile" hint="Ví dụ: mưa nghỉ 15h30, công nhân mới học việc"/>
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
.field-report__money{display:inline-block;padding-top:8px;font-variant-numeric:tabular-nums;white-space:nowrap}
.field-report__money small{color:var(--lotus-muted)}
.field-report__money--warn{color:var(--lotus-danger)}
.field-report__others{margin:0;padding-left:18px;display:grid;gap:4px;font-size:var(--lotus-text-sm)}
.field-report__actions{position:sticky;bottom:0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 0;background:var(--lotus-surface);border-top:1px solid var(--lotus-border)}
.field-report__dirty{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-report--mobile .field-report__money{padding-top:0}
</style>

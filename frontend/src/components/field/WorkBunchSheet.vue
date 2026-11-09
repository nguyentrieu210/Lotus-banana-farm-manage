<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import {amountText} from '../../field-work-model.js'
import {formatDate} from '../../format'
import {AFTER_CUT,blankForm,blankHarvest,blankReject,colourOptions,formFromRows,groupByZone,kindLabels,lineSum,sheetFingerprint,sheetRows,stageOptions,sum} from '../../bunch-sheet-model.js'
// The entry dialog of one việc for one tổ and day: chích and cắt take a number per lô, loại and thu are lines. Saving sends the
// whole open sheet of the tổ, so the other việc of the day are kept. Closing with unsaved numbers asks first.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},date:{type:String,required:true},sheet:{type:Object,required:true},
 kind:{type:String,required:true},initialTeam:String,mobile:Boolean})
const emit=defineEmits(['close','saved'])
const team=ref(props.initialTeam||props.sheet.teams[0]?.name||''),form=ref(blankForm()),baseline=ref('')
const saving=ref(false),error=ref(''),rowErrors=ref([]),askDrop=ref(false)

function fill(){
 form.value=formFromRows(props.sheet.rows,team.value);baseline.value=sheetFingerprint(form.value);rowErrors.value=[];error.value=''
 if(props.kind==='reject'&&!form.value.rejects.length)form.value.rejects.push(blankReject())
 if(props.kind==='harvest'&&!form.value.harvests.length)form.value.harvests.push(blankHarvest())
}
onMounted(fill)
watch(team,fill)

const dirty=computed(()=>sheetFingerprint(form.value)!==baseline.value)
const isGrid=computed(()=>props.kind==='inject'||props.kind==='cut')
const zones=computed(()=>groupByZone(props.sheet.blocks))
const teamOptions=computed(()=>props.sheet.teams.map(t=>({value:t.name,label:t.label})))
const blockOptions=computed(()=>props.sheet.blocks.map(b=>({value:b.name,label:b.code})))
const reasonOptions=computed(()=>props.sheet.reasons.map(r=>({value:r.name,label:r.reason_name})))
const noRibbon=computed(()=>props.kind==='cut'&&!props.sheet.ribbon)
const title=computed(()=>kindLabels[props.kind]+' · '+formatDate(props.date))
const lockedLines=computed(()=>form.value.locked.lines.filter(r=>r.event_type===(props.kind==='reject'?'Reject':'Harvest')))
const total=computed(()=>isGrid.value?sum(form.value[props.kind]):lineSum(props.kind==='reject'?form.value.rejects:form.value.harvests))
const harvestKg=computed(()=>form.value.harvests.reduce((n,l)=>n+(Number(l.weight_kg)||0),0))

function requestClose(open){if(open||saving.value)return;if(dirty.value){askDrop.value=true;return};emit('close')}
async function save(){
 if(!dirty.value||saving.value)return
 saving.value=true;error.value='';rowErrors.value=[];askDrop.value=false
 try{
  const result=await call('lotus_farm.bunch_posting.save_day',{farm:props.farm,crew:props.crew,date:props.date,team:team.value,rows:sheetRows(form.value)},true)
  if(result.errors.length){rowErrors.value=result.errors;return}
  emit('saved')
 }catch(e){error.value=e.message}
 finally{saving.value=false}
}
</script>

<template>
 <ModalForm class="work-bunch-modal" :model-value="true" :title="title" width="720px" :busy="saving" :error="error" submit-label="Lưu" :submit-disabled="!dirty||!team" @update:model-value="requestClose" @submit="save">
  <ul v-if="rowErrors.length" class="work-bunch__errors" role="alert"><li v-for="(e,i) in rowErrors" :key="i"><strong v-if="e.block">{{e.block}}:</strong> {{e.message}}</li></ul>
  <LotusField v-if="teamOptions.length>1" v-model="team" label="Tổ" type="select" :searchable="false" :options="teamOptions" :mobile="mobile" :disabled="dirty" :hint="dirty?'Lưu hoặc bỏ thay đổi trước khi đổi tổ.':''"/>

  <template v-if="isGrid">
   <p v-if="kind==='cut'&&sheet.ribbon" class="work-bunch__ribbon"><span class="work-bunch__chip" :style="{background:sheet.ribbon.code||'transparent'}" aria-hidden="true"></span>Màu dây hôm nay: <strong>{{sheet.ribbon.label}}</strong> · tuần {{sheet.ribbon.week}}</p>
   <p v-if="noRibbon" class="lotus-modal-form__error" role="alert">Ngày này chưa có màu dây trong lịch màu dây, chưa nhập được cắt bắp.</p>
   <div v-for="z in zones" :key="z.zone" class="work-bunch__zone">
    <h3>Khu {{z.zone}}</h3>
    <div class="work-bunch__grid">
     <template v-for="b in z.items" :key="b.name">
      <LotusField v-if="form.locked[kind][b.name]" :model-value="form.locked[kind][b.name]" :label="b.code" type="number" :mobile="mobile" disabled hint="Đã xác nhận"/>
      <LotusField v-else v-model="form[kind][b.name]" :label="b.code" type="number" inputmode="numeric" :mobile="mobile" :disabled="noRibbon"/>
     </template>
    </div>
   </div>
  </template>

  <template v-else-if="kind==='reject'">
   <article v-for="l in form.rejects" :key="l.id" class="work-bunch__line">
    <FormGrid :columns="2">
     <LotusField v-model="l.block" label="Lô" type="select" :options="blockOptions" :mobile="mobile"/>
     <LotusField v-model="l.qty" label="Số buồng" type="number" inputmode="numeric" :mobile="mobile"/>
     <LotusField v-model="l.reject_stage" label="Giai đoạn" type="select" :searchable="false" :options="stageOptions" :mobile="mobile"/>
     <LotusField v-model="l.reason" label="Lý do" type="select" :searchable="false" :options="reasonOptions" :mobile="mobile"/>
     <LotusField v-if="l.reject_stage===AFTER_CUT" v-model="l.bunch_tag" label="Màu dây" type="select" :searchable="false" :options="colourOptions(sheet,l.block,l.bunch_tag)" :mobile="mobile" :hint="l.block&&!colourOptions(sheet,l.block,l.bunch_tag).length?'Lô này chưa có buồng đã cắt bắp.':''"/>
    </FormGrid>
    <UiButton type="button" variant="ghost" size="sm" @click="form.rejects.splice(form.rejects.indexOf(l),1)">Bỏ dòng</UiButton>
   </article>
   <div><UiButton type="button" variant="outline" @click="form.rejects.push(blankReject())">Thêm dòng</UiButton></div>
  </template>

  <template v-else>
   <article v-for="l in form.harvests" :key="l.id" class="work-bunch__line">
    <FormGrid :columns="2">
     <LotusField v-model="l.block" label="Lô" type="select" :options="blockOptions" :mobile="mobile"/>
     <LotusField v-model="l.bunch_tag" label="Màu dây" type="select" :searchable="false" :options="colourOptions(sheet,l.block,l.bunch_tag)" :mobile="mobile" :hint="l.block&&!colourOptions(sheet,l.block,l.bunch_tag).length?'Lô này chưa có buồng đã cắt bắp.':''"/>
     <LotusField v-model="l.qty" label="Số buồng" type="number" inputmode="numeric" :mobile="mobile"/>
     <LotusField v-model="l.weight_kg" label="Khối lượng (kg)" type="number" inputmode="decimal" :mobile="mobile"/>
    </FormGrid>
    <UiButton type="button" variant="ghost" size="sm" @click="form.harvests.splice(form.harvests.indexOf(l),1)">Bỏ dòng</UiButton>
   </article>
   <div><UiButton type="button" variant="outline" @click="form.harvests.push(blankHarvest())">Thêm dòng</UiButton></div>
  </template>

  <ul v-if="!isGrid&&lockedLines.length" class="work-bunch__locked">
   <li v-for="r in lockedLines" :key="r.name">{{r.block_code}}<template v-if="r.ribbon"> · {{r.ribbon}}</template><template v-if="r.reason_name"> · {{r.reason_name}}</template> · {{amountText(r.qty)}} buồng<template v-if="r.weight_kg"> · {{amountText(r.weight_kg)}} kg</template> · đã xác nhận</li>
  </ul>
  <p v-if="total" class="lotus-form-note">Tổng {{amountText(total)}} buồng<template v-if="kind==='harvest'&&harvestKg"> · {{amountText(harvestKg)}} kg</template></p>
  <div v-if="askDrop" class="lotus-delete-confirm" role="alert">
   <p>Số vừa nhập chưa được lưu. Bỏ các thay đổi này?</p>
   <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="askDrop=false">Tiếp tục nhập</UiButton><UiButton type="button" variant="destructive" @click="emit('close')">Bỏ thay đổi</UiButton></div>
  </div>
 </ModalForm>
</template>

<style>
.work-bunch__zone{display:grid;gap:6px}
.work-bunch__zone h3{margin:0;font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-muted)}
.work-bunch__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px}
.work-bunch__ribbon{display:flex;align-items:center;gap:6px;margin:0;font-size:var(--lotus-text-sm)}
.work-bunch__chip{display:inline-block;width:14px;height:14px;border-radius:50%;border:1px solid var(--lotus-border)}
.work-bunch__line{display:grid;gap:4px;justify-items:start;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.work-bunch__line>.lotus-form-grid{width:100%}
.work-bunch__errors,.work-bunch__locked{margin:0;padding-left:18px;font-size:var(--lotus-text-sm)}
.work-bunch__errors{color:var(--lotus-danger)}
.work-bunch__locked{color:var(--lotus-muted)}
.work-bunch-modal .lotus-pwa-field.van-cell{padding:6px 10px}
.work-bunch-modal .work-bunch__line .lotus-form-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
@media(max-width:620px){.work-bunch-modal .work-bunch__grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>

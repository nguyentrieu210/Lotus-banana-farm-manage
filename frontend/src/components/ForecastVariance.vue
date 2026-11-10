<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import ModalForm from './form/ModalForm.vue'
// So dự thu với thực tế: one card per week, comparing what was frozen before the week began with what was harvested. A card opens the
// week by lô and colour. Suggested parameters are shown next to those in force and are never applied from here.
const props=defineProps({farm:{type:String,default:''},canSnapshot:Boolean})
const api=(name,args={},write=false)=>call('lotus_farm.forecast_snapshot.'+name,args,write)
const fmt=(n,d=0)=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:d})
const pad=n=>String(n).padStart(2,'0')
function isoWeek(day){const d=new Date(Date.UTC(day.getFullYear(),day.getMonth(),day.getDate()));const n=d.getUTCDay()||7;d.setUTCDate(d.getUTCDate()+4-n);const start=new Date(Date.UTC(d.getUTCFullYear(),0,1));return d.getUTCFullYear()+'-W'+pad(Math.ceil(((d-start)/864e5+1)/7))}
function weeksAgo(n){const d=new Date();d.setDate(d.getDate()-7*n);return isoWeek(d)}
const data=ref(null),busy=ref(false),error=ref(''),notice=ref(''),saving=ref(false)
const week=ref(null),detail=ref(null),detailBusy=ref(false),advice=ref(null),adviceOpen=ref(false)
async function load(){
 if(!props.farm)return
 busy.value=true;error.value=''
 try{data.value=await api('variance',{farm:props.farm,from_week:weeksAgo(12),to_week:weeksAgo(0),group_by:'week'})}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
onMounted(load)
watch(()=>props.farm,load)
const byWeek=computed(()=>new Map((data.value?.rows||[]).map(r=>[r.key,r])))
const cards=computed(()=>[...(data.value?.weeks||[])].reverse().filter(w=>data.value.snapshots[w]).map(w=>({week:w,number:Number(w.split('-W')[1]),row:byWeek.value.get(w)||{forecast_bunches:0,actual_bunches:0,diff_bunches:0,diff_pct:null,forecast_kg:0,actual_kg:0},from:data.value.snapshots[w].date})))
const pct=v=>v==null?'—':(v>0?'+':'')+fmt(v,1)+'%'
const dm=s=>String(s).slice(8,10)+'/'+String(s).slice(5,7)
const tone=v=>v==null?'':Math.abs(v)<=10?'is-good':Math.abs(v)<=15?'is-fair':'is-bad'
async function snapshot(){
 saving.value=true;error.value='';notice.value=''
 try{const r=await api('create',{farm:props.farm},true);notice.value='Đã chốt bản dự thu: '+fmt(r.total_bunches)+' buồng, '+fmt(r.total_kg)+' kg.';await load()}
 catch(e){error.value=e.message}
 finally{saving.value=false}
}
async function openWeek(c){
 week.value=c;detail.value=null;detailBusy.value=true
 try{detail.value=(await api('variance',{farm:props.farm,from_week:c.week,to_week:c.week,group_by:'detail'})).rows}
 catch(e){error.value=e.message;week.value=null}
 finally{detailBusy.value=false}
}
async function openAdvice(){
 adviceOpen.value=true;advice.value=null
 try{advice.value=await api('suggest_parameters',{farm:props.farm})}
 catch(e){error.value=e.message;adviceOpen.value=false}
}
const adviceValue=v=>v==null?'—':v<=1&&v>0?fmt(v*100,1)+'%':fmt(v,2)
</script>

<template>
 <section class="forecast-variance" :aria-busy="busy">
  <div class="forecast-variance__actions">
   <UiButton type="button" variant="outline" @click="openAdvice">Tham số đề xuất</UiButton>
   <UiButton v-if="canSnapshot" type="button" :disabled="saving" @click="snapshot">{{saving?'Đang chốt…':'Chốt bản dự thu hôm nay'}}</UiButton>
  </div>
  <p v-if="error" role="alert" class="land-bad">{{error}}</p>
  <p v-if="notice" role="status" class="notice">{{notice}}</p>
  <p class="land-note">Mỗi tuần có một bản chốt dự thu tính theo sổ lô lúc 0 giờ thứ Hai (người đầu tiên mở ứng dụng trong tuần sẽ kích hoạt việc dựng, kể cả bù tuần bị lỡ). Mỗi tuần được so với bản chốt của chính tuần đó.</p>
  <p v-if="data&&!cards.length" class="land-note">Chưa có tuần nào để so. Cần có bản dự thu đã chốt và số thu hoạch đã xác nhận.</p>
  <div class="bunch-weekly__grid">
   <button v-for="c in cards" :key="c.week" type="button" class="bunch-week" @click="openWeek(c)">
    <span class="bunch-week__name">Tuần {{c.number}}</span>
    <span class="bunch-week__days">Bản chốt {{dm(c.from)}}</span>
    <strong :class="tone(c.row.diff_pct)">{{pct(c.row.diff_pct)}}</strong>
    <span class="bunch-week__kg">Dự thu {{fmt(c.row.forecast_bunches)}} · thực tế {{fmt(c.row.actual_bunches)}} buồng</span>
    <span class="bunch-week__kg">{{fmt(c.row.forecast_kg)}} · {{fmt(c.row.actual_kg)}} kg</span>
    <span v-if="data.packout?.[c.week]?.bunches" class="bunch-week__kg">Xưởng: {{fmt(data.packout[c.week].kg_per_bunch,1)}} kg/buồng · {{fmt(data.packout[c.week].cartons_per_bunch,2)}} thùng/buồng</span>
   </button>
  </div>

  <ModalForm :model-value="!!week" :title="week?'Tuần '+week.number+' · dự thu và thực tế':'Tuần'" width="720px" readonly @update:model-value="v=>!v&&(week=null)">
   <p v-if="detailBusy" class="lotus-form-note" role="status">Đang tải…</p>
   <ul v-else class="bunch-lines">
    <li v-for="r in detail||[]" :key="r.key"><div class="forecast-variance__line">
     <strong>{{r.block_code}}<template v-if="r.ribbon"> · {{r.ribbon}}</template></strong><span>Dự thu {{fmt(r.forecast_bunches)}} · thực tế {{fmt(r.actual_bunches)}} buồng · {{fmt(r.actual_kg)}} kg</span><em :class="tone(r.diff_pct)">{{pct(r.diff_pct)}}</em>
    </div></li>
   </ul>
  </ModalForm>

  <ModalForm :model-value="adviceOpen" title="Tham số đề xuất" width="560px" readonly @update:model-value="v=>!v&&(adviceOpen=false)">
   <p v-if="!advice" class="lotus-form-note" role="status">Đang tải…</p>
   <template v-else>
    <p class="lotus-form-note">Đo từ {{advice.samples}} màu dây đã thu xong; cần ít nhất {{advice.needed}} màu mới đề xuất. Chưa áp dụng: muốn dùng thì tạo bộ thông số mới ở tab Bộ thông số và duyệt.</p>
    <ul v-if="advice.lines.length" class="bunch-lines">
     <li v-for="l in advice.lines" :key="l.field"><div class="forecast-variance__line"><strong>{{l.label}}</strong><span>Đang dùng {{adviceValue(l.current)}} {{l.unit}}</span><em>{{adviceValue(l.suggested)}} {{l.unit}}</em></div></li>
    </ul>
   </template>
  </ModalForm>
 </section>
</template>

<style>
.forecast-variance{display:grid;gap:12px;min-width:0}
.forecast-variance__actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.forecast-variance__line{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.forecast-variance .is-good{color:var(--lotus-success)}
.forecast-variance .is-fair{color:var(--lotus-warning)}
.forecast-variance .is-bad{color:var(--lotus-danger)}
</style>

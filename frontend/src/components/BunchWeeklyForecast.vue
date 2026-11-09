<script setup>
import {computed,ref} from 'vue'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import ModalForm from './form/ModalForm.vue'
import BunchChart from './BunchChart.vue'
import BunchOpeningImport from './BunchOpeningImport.vue'
// Dự thu: real numbers and estimates kept apart, every bunch counted once at the stage nearest to harvest. One column per week (or month); a week
// opens by lô, a lô opens where its number comes from. The pace line compares the bunches really cut with those the estimate needs.
const props=defineProps({data:Object,farm:{type:String,default:''},canImport:Boolean,view:{type:String,default:'weeks'},zones:{type:Array,default:()=>[]},zone:{type:String,default:''}})
const emit=defineEmits(['changed','zone'])
const num=(n,d=0)=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:d})
const dm=s=>s?String(s).slice(8,10)+'/'+String(s).slice(5,7):''
const dmy=s=>s?dm(s)+'/'+String(s).slice(0,4):''
const units=[{id:'bunches',label:'Buồng',unit:'buồng',layers:'layers',total:'bunches',digits:0},{id:'kg',label:'Kg',unit:'kg',layers:'layer_kg',total:'kg',digits:0},
 {id:'cartons',label:'Thùng',unit:'thùng',layers:'layer_cartons',total:'cartons',digits:0},{id:'containers',label:'Cont',unit:'cont',layers:'layer_containers',total:'containers',digits:1}]
const unitId=ref('bunches')
const unit=computed(()=>units.find(u=>u.id===unitId.value))
const value=n=>num(n,unit.value.digits)
function parts(slot){const l=slot?.[unit.value.layers]||{};return {cut:Number(l.cut||0),inject:Number(l.inject||0),est:Number(l.sucker||0)+Number(l.tree||0)}}
const eventText={'Sucker Select':'Chọn chồi','Bud Injection':'Chích bắp','Cut Bud':'Cắt bắp','Reject':'Hủy buồng','Harvest':'Thu hoạch'}
const layerText={cut:'Đã cắt bắp',inject:'Đã chích bắp',sucker:'Theo chọn chồi',tree:'Theo số cây'}
const confidenceText={high:'Tin cậy cao',medium:'Tin cậy khá',low:'Tin cậy thấp'}
const sourceText=l=>l.source_type==='Opening Import'?'Sổ cắt bắp'+(l.source_name?' ('+l.source_name+')':''):l.source_type==='Work Entry'?'Phiếu chọn chồi':'Nhập hằng ngày'
const week=ref(null),line=ref(null),trace=ref(null),busy=ref(false),error=ref(''),importing=ref(false),notice=ref(''),openZone=ref(''),paceOpen=ref(false)

const weeks=computed(()=>props.data?.weeks||[])
const months=computed(()=>props.data?.months||[])
const isWeeks=computed(()=>props.view==='weeks')
const scope=computed(()=>isWeeks.value?[props.data?.totals].filter(Boolean):months.value)
const sums=computed(()=>scope.value.reduce((n,s)=>{const p=parts(s);return {cut:n.cut+p.cut,inject:n.inject+p.inject,est:n.est+p.est}},{cut:0,inject:0,est:0}))
const coverage=computed(()=>props.data?.coverage||{with_data:0,total:0})
const period=computed(()=>isWeeks.value?(props.data?.horizon||13)+' tuần tới':'12 tháng tới')
const monthName=m=>'Tháng '+Number(String(m).slice(5,7))+'/'+String(m).slice(2,4)
const items=computed(()=>isWeeks.value
 ?weeks.value.map(w=>({key:w.week,name:String(w.number),title:'Tuần '+w.number+' ('+dm(w.start)+' – '+dm(w.end)+')',values:parts(w),source:w}))
 :months.value.map(m=>({key:m.month,name:'T'+Number(String(m.month).slice(5,7)),title:monthName(m.month),values:parts(m),source:m})))

const pending=computed(()=>Object.entries(props.data?.unconfirmed||{}).filter(([k])=>eventText[k]).map(([k,v])=>eventText[k].toLowerCase()+' '+num(v)).join(', '))
const pace=computed(()=>props.data?.pace||null)
const zoneRows=computed(()=>{
 const found=new Map((props.data?.zones||[]).map(z=>[z.zone,z])),starts=props.data?.zone_starts||{}
 const rows=props.zones.map(zone=>{const z=found.get(zone);return {zone,values:parts(z),total:z?Number(z[unit.value.total]||0):0,first:starts[zone]}})
 const top=Math.max(1,...rows.map(r=>r.total))
 return rows.map(r=>({...r,share:v=>v/top*100}))
})
const zoneLots=computed(()=>{
 if(!openZone.value)return []
 const found=new Map((props.data?.blocks||[]).map(b=>[b.block,b]))
 return Object.entries(props.data?.block_starts||{}).filter(([,b])=>b.zone===openZone.value).map(([name,b])=>{const row=found.get(name);return {name,code:b.code,first:b.first,total:row?Number(row[unit.value.total]||0):0}})
  .sort((a,b)=>a.code.length-b.code.length||a.code.localeCompare(b.code))
})
const title=computed(()=>week.value?'Tuần '+week.value.number+' · '+dm(week.value.start)+' – '+dm(week.value.end):'Tuần')
const rows=computed(()=>week.value?(props.data?.rows||[]).filter(r=>r.week===week.value.week):[])
function close(open){if(!open){week.value=null;line.value=null;trace.value=null;error.value=''}}
async function openLine(r){
 line.value=r;trace.value=null;busy.value=true;error.value=''
 try{trace.value=await call('lotus_farm.block_forecast.trace',{farm:props.farm,block:r.block,week:r.week,layer:r.layer,tag:r.tag||undefined,cycle:r.cycle})}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
function back(){line.value=null;trace.value=null;error.value=''}
function imported(result){importing.value=false;notice.value='Đã ghi '+num(result.bunches)+' buồng vào sổ buồng.';emit('changed')}
</script>

<template>
 <section class="bunch-weekly">
  <div class="bunch-weekly__bar">
   <div class="bunch-chips" role="group" aria-label="Lọc theo khu">
    <button type="button" :aria-pressed="!zone" :class="{'is-on':!zone}" @click="emit('zone','')">Tất cả</button>
    <button v-for="z in zones" :key="z" type="button" :aria-pressed="zone===z" :class="{'is-on':zone===z}" @click="emit('zone',z)">{{z}}</button>
   </div>
   <div class="bunch-chips" role="group" aria-label="Đơn vị">
    <button v-for="u in units" :key="u.id" type="button" :aria-pressed="unitId===u.id" :class="{'is-on':unitId===u.id}" @click="unitId=u.id">{{u.label}}</button>
   </div>
  </div>

  <div class="land-stats bunch-weekly__stats">
   <div><span>Chắc chắn</span><strong>{{value(sums.cut+sums.inject)}} {{unit.unit}}</strong><small>Đã cắt {{value(sums.cut)}} · đã chích {{value(sums.inject)}} · {{period}}</small></div>
   <div><span>Ước tính</span><strong>{{value(sums.est)}} {{unit.unit}}</strong><small>Theo chọn chồi và số cây</small></div>
   <div><span>Lô có số thật</span><strong>{{coverage.with_data}}/{{coverage.total}} lô</strong><small v-if="coverage.total>coverage.with_data">Còn {{coverage.total-coverage.with_data}} lô chỉ có ước tính</small></div>
  </div>
  <p v-if="notice" role="status" class="notice">{{notice}}</p>
  <p v-if="pending" class="land-note">Chưa xác nhận, chưa tính vào dự thu: {{pending}}.</p>
  <p v-for="(w,i) in data?.warnings||[]" :key="i" class="land-note">{{w}}</p>

  <section class="land-card">
   <div class="bunch-weekly__head"><h3>{{isWeeks?(data?.horizon||13)+' tuần tới':'12 tháng tới'}}</h3><UiButton v-if="canImport&&isWeeks" type="button" variant="outline" size="sm" @click="notice='';importing=true">Nạp sổ cắt bắp</UiButton></div>
   <BunchChart :items="items" :format="value" :unit="unit.unit" :clickable="isWeeks" :label="'Dự thu '+period+' theo '+unit.unit" @select="i=>week=i.source"/>
  </section>

  <button v-if="isWeeks&&pace" type="button" class="bunch-pace" @click="paceOpen=true">
   <strong>Nhịp cắt bắp</strong>
   <span v-if="pace.last_actual">Tuần {{pace.last_actual.number}}: cắt thật {{num(pace.last_actual.actual)}}</span><span v-else>Chưa có số cắt thật</span>
   <span v-if="pace.next_need">Tuần {{pace.next_need.number}} cần: khoảng {{num(pace.next_need.needed)}}</span>
   <em v-if="pace.alert" class="bunch-pace__alert"><span aria-hidden="true">⚠</span> Gấp {{num(pace.times)}} lần nhịp hiện tại</em>
  </button>

  <section v-if="isWeeks&&!zone&&zoneRows.length" class="land-card">
   <h3>Theo khu</h3>
   <ul class="bunch-zones">
    <li v-for="z in zoneRows" :key="z.zone"><button type="button" @click="openZone=z.zone">
     <strong>Khu {{z.zone}}</strong>
     <span class="bunch-zones__bar bunch-chart" aria-hidden="true"><i v-if="z.values.cut" class="is-cut" :style="{width:z.share(z.values.cut)+'%'}"></i><i v-if="z.values.inject" class="is-inject" :style="{width:z.share(z.values.inject)+'%'}"></i><i v-if="z.values.est" class="is-est" :style="{width:z.share(z.values.est)+'%'}"></i></span>
     <em>{{z.total?value(z.total)+' '+unit.unit:z.first?'Thu từ '+dm(z.first):'Chưa có số'}}</em>
    </button></li>
   </ul>
  </section>

  <ModalForm class="bunch-weekly-modal" :model-value="!!week" :title="title" width="720px" readonly :error="error" @update:model-value="close">
   <template v-if="week&&!line">
    <p class="lotus-form-note">{{num(week.bunches)}} buồng · {{num(week.kg)}} kg · {{num(week.cartons)}} thùng · {{num(week.containers,1)}} cont. Bấm một dòng để xem số lấy từ đâu.</p>
    <ul class="bunch-lines">
     <li v-for="r in rows" :key="r.block+r.layer+(r.tag||'')+r.cycle"><button type="button" @click="openLine(r)">
      <strong>{{r.block_code}}<template v-if="r.ribbon"> · {{r.ribbon}}</template></strong><span>{{layerText[r.layer]}} · {{confidenceText[r.confidence]}} · vụ {{r.cycle}}{{r.overdue?' · quá hạn':''}}</span><em>{{num(r.bunches)}} buồng · {{num(r.kg)}} kg</em>
     </button></li>
    </ul>
   </template>
   <template v-else-if="line">
    <div><UiButton type="button" variant="ghost" size="sm" @click="back">‹ Quay lại tuần {{week?.number}}</UiButton></div>
    <h3 class="bunch-trace__title">{{line.block_code}}<template v-if="line.ribbon"> · màu {{line.ribbon}}</template> · {{num(line.bunches)}} buồng trong tuần</h3>
    <p v-if="busy" class="lotus-form-note" role="status">Đang tải…</p>
    <template v-if="trace">
     <p class="lotus-form-note">{{trace.note}}</p>
     <dl v-for="g in trace.groups" :key="g.key" class="bunch-trace__facts">
      <div v-for="[label,fact] in g.facts" :key="label"><dt>{{label}}</dt><dd>{{typeof fact==='number'?num(fact):fact}}</dd></div>
     </dl>
     <ul class="bunch-trace__lines">
      <li v-for="l in trace.lines" :key="l.name">{{dmy(l.event_date)}} · {{eventText[l.event_type]||l.event_type}} · {{num(l.qty)}} buồng · {{sourceText(l)}}</li>
     </ul>
     <p v-if="trace.params" class="lotus-form-note">Thông số: {{trace.params.profile?trace.params.profile+' bản '+trace.params.version:'mặc định, chưa duyệt'}} · cắt đến thu {{trace.params.min_days}}–{{trace.params.max_days}} ngày · tỷ lệ thu {{num(trace.params.harvest_rate*100)}}% · đóng gói {{num(trace.params.pack_rate*100)}}% · {{num(trace.params.kg_per_carton)}} kg/thùng</p>
    </template>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!openZone" :title="'Khu '+openZone+' · '+period" width="560px" readonly @update:model-value="v=>!v&&(openZone='')">
   <ul class="bunch-lines">
    <li v-for="l in zoneLots" :key="l.name"><div class="bunch-lines__row"><strong>{{l.code}}</strong><span>{{l.first?'Thu từ '+dm(l.first):'Chưa có số'}}</span><em>{{value(l.total)}} {{unit.unit}}</em></div></li>
   </ul>
  </ModalForm>

  <ModalForm :model-value="paceOpen" title="Nhịp cắt bắp" width="560px" readonly @update:model-value="v=>paceOpen=v">
   <p class="lotus-form-note">Số buồng cần cắt mỗi tuần để đạt phần ước tính. Sau 2–3 tuần nhập liệu sẽ thấy ước tính đang cao hay thấp.</p>
   <ul class="bunch-lines">
    <li v-for="w in pace?.weeks||[]" :key="w.week"><div class="bunch-lines__row"><strong>Tuần {{w.number}}</strong><span>{{dm(w.start)}}</span><em>{{w.future?'Cần '+num(w.needed):'Cắt thật '+num(w.actual)}}</em></div></li>
   </ul>
  </ModalForm>

  <BunchOpeningImport v-if="importing" :farm="farm" @close="importing=false" @done="imported"/>
 </section>
</template>

<style>
.bunch-weekly{display:grid;gap:12px;min-width:0}
.bunch-weekly__bar{display:flex;justify-content:space-between;gap:8px 16px;flex-wrap:wrap}
.bunch-weekly__head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.bunch-weekly__head h3{margin:0}
.bunch-weekly .bunch-weekly__stats{grid-template-columns:repeat(3,minmax(0,1fr))}
@media(max-width:620px){.bunch-weekly .bunch-weekly__stats{grid-template-columns:minmax(0,1fr)}}
.bunch-weekly__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.bunch-chips{display:inline-flex;gap:2px;padding:2px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.bunch-chips button{min-height:32px;padding:4px 12px;border:0;border-radius:6px;background:transparent;color:var(--lotus-muted);font:inherit;font-size:var(--lotus-text-sm);cursor:pointer}
.bunch-chips button.is-on{background:var(--lotus-primary-subtle);color:var(--lotus-primary-text);font-weight:600}
.bunch-pace{display:flex;align-items:center;gap:6px 18px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.bunch-pace:hover{border-color:var(--lotus-primary)}
.bunch-pace span{font-size:var(--lotus-text-sm);color:var(--lotus-text-secondary);font-variant-numeric:tabular-nums}
.bunch-pace__alert{margin-left:auto;font-style:normal;font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-warning)}
.bunch-pace__alert span{color:inherit}
.bunch-zones{display:grid;gap:4px;margin:0;padding:0;list-style:none}
.bunch-zones button{display:grid;grid-template-columns:60px minmax(0,1fr) 130px;align-items:center;gap:10px;width:100%;padding:6px 8px;border:0;border-radius:var(--lotus-radius-md);background:transparent;color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.bunch-zones button:hover{background:var(--lotus-hover)}
.bunch-zones em{font-style:normal;text-align:right;font-size:var(--lotus-text-sm);font-variant-numeric:tabular-nums;color:var(--lotus-text-secondary)}
.bunch-zones__bar{display:flex;gap:2px;height:12px}
.bunch-zones__bar i{display:block;height:100%}
.bunch-zones__bar i:last-child{border-radius:0 4px 4px 0}
.bunch-lines,.bunch-trace__lines{margin:0;padding:0;list-style:none}
.bunch-lines{display:grid;gap:6px}
.bunch-lines button,.bunch-lines__row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;width:100%;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left}
.bunch-lines button{cursor:pointer}
.bunch-lines button:hover{border-color:var(--lotus-primary)}
.bunch-lines span{grid-column:1;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.bunch-lines em{grid-column:2;grid-row:1/3;align-self:center;font-style:normal;font-variant-numeric:tabular-nums}
.bunch-week,.bunch-month{display:grid;gap:2px;justify-items:start;padding:12px 14px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left}
.bunch-week{cursor:pointer}
.bunch-week:hover:not(:disabled){border-color:var(--lotus-primary)}
.bunch-week__name{font-weight:600}
.bunch-week__days,.bunch-week__kg{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.bunch-week strong{font-size:1.45rem;line-height:1.3;font-variant-numeric:tabular-nums}
.bunch-trace__title{margin:0;font-size:var(--lotus-text-base)}
.bunch-trace__facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin:0}
.bunch-trace__facts div{padding:8px 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
.bunch-trace__facts dt{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.bunch-trace__facts dd{margin:0;font-weight:600;font-variant-numeric:tabular-nums}
.bunch-trace__lines{display:grid;gap:4px;font-size:var(--lotus-text-sm)}
</style>

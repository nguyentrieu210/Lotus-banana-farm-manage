<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import ModalForm from '../form/ModalForm.vue'
import DataTable from '../DataTable.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
import {amountText} from '../../lot-entry-model.js'
import {StatTile} from '../ui/stat-tile'
import RibbonDot from '../agri/RibbonDot.vue'
import RibbonBatchCard from '../agri/RibbonBatchCard.vue'
// Bảng màu dây (lotus_farm.ribbon_board): bunches on the plants per ribbon colour of a week, from confirmed numbers.
// The lô and colours to harvest now come first; a colour card opens its lô in a dialog.
const props=defineProps({farm:{type:String,required:true},zones:{type:Array,default:()=>[]},mobile:Boolean,compact:Boolean})
// compact (the đội trưởng's phone): the totals and the due list first, the colour cards behind one button.
const zone=ref(''),week=ref(''),data=ref(null),busy=ref(false),error=ref(''),opened=ref(null),showDone=ref(false),expanded=ref(!props.compact)
let asked=0
async function load(){
 const mine=++asked
 busy.value=true;error.value=''
 try{const result=await call('lotus_farm.ribbon_board.board',{farm:props.farm,zone:zone.value||undefined,week:week.value||undefined});if(mine===asked)data.value=result}
 catch(e){if(mine===asked){error.value=e.message;data.value=null}}
 finally{if(mine===asked)busy.value=false}
}
watch(()=>[props.farm,zone.value,week.value],load,{immediate:true})
// The due list of this week, or of a coming week to plan the cutters and the xưởng: any day of the week will do.
const inDays=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
const weekOptions=[{value:'',label:'Tuần này'},{value:inDays(7),label:'Tuần sau'},{value:inDays(14),label:'Hai tuần nữa'}]
const statusLabels={waiting:'Đang nuôi',due:'Đến tuổi thu',overdue:'Quá tuổi thu',done:'Đã thu hết'}
const zoneOptions=computed(()=>[{value:'',label:'Tất cả khu'},...(data.value?.zones||[]).filter(z=>!props.zones.length||props.zones.includes(z)).map(z=>({value:z,label:'Khu '+z}))])
const cards=computed(()=>(data.value?.cards||[]).filter(c=>showDone.value||c.status!=='done').slice().reverse())
const due=computed(()=>data.value?.due_rows||[])
// A ribbon-board card as a kit batch card (spec 004): colour, week, age, lots, counts and harvest progress.
const batchOf=c=>({code:c.code,label:c.colour+' tuần '+c.week+(c.lan?' lần '+c.lan:''),week:c.week,year:c.year,age:c.age_weeks,lots:c.lots.length,cut:c.cut,bagged:c.bag,harvested:c.harvested,left:c.left,status:c.status,statusLabel:statusLabels[c.status]})
// Sổ cắt bắp in the layout of the farm's Excel book, ten weeks to a sheet.
const bookUrl=computed(()=>'/api/method/lotus_farm.ribbon_board.export_cut_book?'+new URLSearchParams({farm:props.farm,...(zone.value?{zone:zone.value}:{})}))
const lotColumns=[
 {field:'code',headerName:'Lô',minWidth:70},
 {field:'cut',headerName:'Cắt bắp',minWidth:90,sum:true},
 {field:'bag',headerName:'Đã bao',minWidth:90,sum:true},
 {field:'bag_left',headerName:'Chưa bao',minWidth:90,sum:true},
 {field:'rejected',headerName:'Hủy sau cắt',minWidth:100,sum:true},
 {field:'harvested',headerName:'Đã thu',minWidth:90,sum:true},
 {field:'kg',headerName:'Kg đã thu',minWidth:100,sum:true},
 {field:'left',headerName:'Còn trên cây',minWidth:110,sum:true},
 {field:'quarantine_until',headerName:'Cách ly đến',valueFormatter:p=>p.value?formatDate(p.value):'',minWidth:110},
]
</script>

<template>
 <section class="ribbon-board" :class="{'ribbon-board--mobile':mobile}" :aria-busy="busy">
  <div class="ribbon-board__tools">
   <LotusField v-if="zoneOptions.length>2" v-model="zone" label="Khu" type="select" :searchable="false" :options="zoneOptions" :empty-option="null" :mobile="mobile"/>
   <LotusField v-model="week" label="Cần thu trong" type="select" :searchable="false" :options="weekOptions" :empty-option="null" :mobile="mobile"/>
   <LotusField v-if="expanded" v-model="showDone" type="checkbox" label="Hiện cả màu đã thu hết" :mobile="mobile"/>
   <a v-if="!mobile" class="ribbon-board__book" :href="bookUrl">Xuất sổ cắt bắp (Excel)</a>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <template v-if="data">
   <div class="ribbon-board__totals">
    <StatTile label="Còn trên cây" :value="data.left" unit="buồng" icon="leaf" tone="primary"/>
    <StatTile class="is-due" label="Đến tuổi thu" :value="data.due" unit="buồng" icon="bunch" tone="warning"/>
    <StatTile class="is-late" label="Quá tuổi thu" :value="data.overdue" unit="buồng" icon="alert" tone="danger"/>
   </div>
   <h3 class="ribbon-board__title">Cần thu {{week?'tuần từ '+formatDate(data.day):'tuần này'}}</h3>
   <p v-if="!due.length" class="lotus-form-note">Chưa có màu nào đến tuổi thu.</p>
   <div class="ribbon-board__due">
    <article v-for="r in due" :key="r.tag+r.block" class="ribbon-due" :class="{'is-held':r.quarantine_until,'is-late':r.status==='overdue'}">
     <RibbonDot :code="r.code_colour" size="lg" decorative/>
     <div><strong>Lô {{r.code}} · {{r.colour}} tuần {{r.week}}<template v-if="r.lan"> lần {{r.lan}}</template></strong>
      <span>Còn {{amountText(r.left)}} buồng · thu {{formatDate(r.start)}} – {{formatDate(r.end)}}</span>
      <em v-if="r.quarantine_until">Đang cách ly đến {{formatDate(r.quarantine_until)}}: chưa được thu</em></div>
    </article>
   </div>
   <UiButton v-if="!expanded" type="button" variant="outline" class="ribbon-board__more" @click="expanded=true">Xem từng màu dây ({{cards.length}})</UiButton>
   <h3 v-if="expanded" class="ribbon-board__title">Theo màu dây</h3>
   <p v-if="expanded&&!cards.length" class="lotus-form-note">Chưa có buồng đã cắt bắp trong sổ lô.</p>
   <div v-if="expanded" class="ribbon-board__cards">
    <RibbonBatchCard v-for="c in cards" :key="c.tag" class="ribbon-card" :class="'is-'+c.status" interactive :batch="batchOf(c)" @open="opened=c"/>
   </div>
  </template>
  <ModalForm :model-value="!!opened" :title="opened?opened.colour+' tuần '+opened.week+(opened.lan?' lần '+opened.lan:''):''" width="860px" readonly
   @update:model-value="v=>!v&&(opened=null)">
   <template v-if="opened">
    <p class="lotus-form-note">Cắt bắp từ {{formatDate(opened.first_cut)}} · thu dự kiến {{formatDate(opened.start)}} – {{formatDate(opened.end)}} · {{statusLabels[opened.status]}}</p>
    <DataTable :rows="opened.lots" :columns="lotColumns" row-key="block" storage-key="ribbon-board-lots" :selection-enabled="false" :paginate="false"
     :export-title="'Màu '+opened.colour+' tuần '+opened.week"/>
   </template>
  </ModalForm>
 </section>
</template>

<style>
.ribbon-board{display:grid;gap:12px;min-width:0}
.ribbon-board__tools{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.ribbon-board__tools>*{min-width:180px}
.ribbon-board__tools .ribbon-board__book{min-width:0;align-self:center;font-size:var(--lotus-text-sm)}
.ribbon-board__totals{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.ribbon-board__title{margin:4px 0 0;font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-semibold);color:var(--lotus-muted)}
.ribbon-board__due{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
.ribbon-board__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.ribbon-board--mobile .ribbon-board__due,.ribbon-board--mobile .ribbon-board__cards,.ribbon-board--mobile .ribbon-board__totals{grid-template-columns:1fr}
.ribbon-due{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-warning-400);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs)}
.ribbon-due.is-late{border-left-color:var(--lotus-tone-danger-solid)}
.ribbon-due.is-held{background-image:repeating-linear-gradient(135deg,var(--lotus-lot-quarantine) 0 6px,transparent 6px 14px)}
.ribbon-due div{display:grid;gap:2px;min-width:0}
.ribbon-due strong{color:var(--lotus-text-strong)}
.ribbon-due span{font-size:var(--lotus-text-sm);color:var(--lotus-muted);font-variant-numeric:tabular-nums}
.ribbon-due em{font-size:var(--lotus-text-sm);font-style:normal;font-weight:var(--lotus-weight-semibold);color:var(--lotus-tone-danger-text)}
</style>

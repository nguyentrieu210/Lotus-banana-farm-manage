<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import './report.css'
// Tồn theo màu dây: what is on the trees, one card per colour of a half-week. A card opens its lô. Used on the report page and from the phone.
const props=defineProps({farm:{type:String,default:''},filters:{type:Object,default:()=>({})}})
const emit=defineEmits(['loaded'])
const data=ref(null),busy=ref(false),error=ref(''),show=ref('open'),card=ref(null)
const num=n=>Number(n||0).toLocaleString('vi-VN')
const dm=s=>s?String(s).slice(8,10)+'/'+String(s).slice(5,7):''
const states={waiting:'Chưa đến kỳ thu',due:'Đến kỳ thu',overdue:'Quá hạn thu',done:'Đã thu xong'}
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.bunch_report.stock',{farm:props.farm||undefined,filters:Object.keys(props.filters).length?JSON.stringify(props.filters):undefined});emit('loaded',data.value)}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
watch(()=>[props.farm,JSON.stringify(props.filters)],load,{immediate:true})
const all=computed(()=>data.value?.cards||[])
const cards=computed(()=>all.value.filter(c=>show.value==='open'?c.status!=='done':c.status==='done'))
const finished=computed(()=>all.value.filter(c=>c.status==='done').length)
const lanText=c=>c.lan?' · lần '+c.lan:''
const title=computed(()=>card.value?card.value.colour+' · tuần '+card.value.week+lanText(card.value):'Lô')
</script>

<template>
 <div class="bunch-stock" :aria-busy="busy">
  <p v-if="error" role="alert" class="lotus-list-page__error">{{error}}</p>
  <template v-if="data">
   <div class="bunch-report__tiles">
    <div><span>Tồn buồng</span><strong>{{num(data.left)}} buồng</strong></div>
    <div><span>Đến kỳ thu tuần này</span><strong>{{num(data.due)}} buồng</strong></div>
    <div><span>Quá hạn thu</span><strong>{{num(data.overdue)}} buồng</strong></div>
   </div>
   <div v-if="finished" class="bunch-report__chips" role="group" aria-label="Hiện màu dây">
    <button type="button" :aria-pressed="show==='open'" :class="{'is-on':show==='open'}" @click="show='open'">Còn tồn</button>
    <button type="button" :aria-pressed="show==='done'" :class="{'is-on':show==='done'}" @click="show='done'">Đã thu xong ({{finished}})</button>
   </div>
   <p v-if="!cards.length" class="lotus-form-note">Chưa có buồng đã cắt bắp trong phần đang lọc.</p>
   <div class="bunch-stock__grid">
    <button v-for="c in cards" :key="c.tag" type="button" class="bunch-stock__card" :class="'is-'+c.status" @click="card=c">
     <span class="bunch-stock__head"><strong>{{c.colour}}</strong><small>Tuần {{c.week}}{{lanText(c)}}</small></span>
     <b>{{num(c.left)}} <small>buồng tồn</small></b>
     <span>Cắt {{num(c.cut)}} · Hủy {{num(c.rejected)}} · Thu {{num(c.harvested)}}</span>
     <span>Thu {{dm(c.start)}} – {{dm(c.end)}}</span>
     <em><span v-if="c.status==='overdue'" aria-hidden="true">⚠ </span>{{states[c.status]}}</em>
    </button>
   </div>
  </template>
  <ModalForm :model-value="!!card" :title="title" width="560px" readonly @update:model-value="v=>!v&&(card=null)">
   <ul v-if="card" class="bunch-report__rows">
    <li v-for="l in card.lots" :key="l.block"><strong>{{l.code}}</strong><span>Cắt {{num(l.cut)}} · Hủy {{num(l.rejected)}} · Thu {{num(l.harvested)}}</span><em>Tồn {{num(l.left)}}</em></li>
   </ul>
  </ModalForm>
 </div>
</template>

<style>
.bunch-stock{display:grid;gap:12px;min-width:0}
.bunch-stock__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.bunch-stock__card{display:grid;gap:3px;justify-items:start;padding:12px 14px;border:1px solid var(--lotus-border);border-left-width:4px;border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.bunch-stock__card:hover{border-color:var(--lotus-primary)}
.bunch-stock__card.is-due{border-left-color:var(--lotus-success)}
.bunch-stock__card.is-overdue{border-left-color:var(--lotus-warning)}
.bunch-stock__head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;width:100%}
.bunch-stock__head small{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.bunch-stock__card b{font-size:1.3rem;font-variant-numeric:tabular-nums}
.bunch-stock__card b small{font-size:var(--lotus-text-sm);font-weight:400;color:var(--lotus-muted)}
.bunch-stock__card>span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.bunch-stock__card em{font-style:normal;font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-text-secondary)}
</style>

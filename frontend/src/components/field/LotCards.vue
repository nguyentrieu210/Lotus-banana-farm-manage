<script setup>
import {computed,ref} from 'vue'
import LotusField from '../form/LotusField.vue'
import {LotCard} from '../agri'
import {formatDate} from '../../format'
import {lotSummary,stateLabels} from '../../lot-entry-model.js'
// The lô of a tổ for a day, one card each: what was entered, what is given to the tổ, the colours still on the plants and
// a quarantine. Tap a card to open its dialog. Lô outside the giao việc can be added from the list.
// Spec 004: the card is the shared kit LotCard (same card on Hôm nay, Màu dây and Vòng chăm sóc, desktop and phone).
const props=defineProps({lots:{type:Array,required:true},works:{type:Array,default:()=>[]},editable:Boolean,mobile:Boolean})
const emit=defineEmits(['open'])
const added=ref([])
const shown=computed(()=>props.lots.filter(l=>l.active||added.value.includes(l.block)))
const others=computed(()=>props.lots.filter(l=>!l.active&&!added.value.includes(l.block)).map(l=>({value:l.block,label:'Lô '+l.code+' · khu '+l.zone})))
const workLabel=name=>props.works.find(w=>w.name===name)?.label||name
const today=new Date().toLocaleDateString('sv-SE')
const LOT_STATE={Draft:'entered',Reopened:'entered',Sent:'sent',Confirmed:'confirmed'}
function given(lot){return lot.assignments.map(a=>a.kind==='Round'?workLabel(a.work_type)+(a.due_date?' (hạn '+formatDate(a.due_date)+')':''):'chăm buồng').join(', ')}
function card(lot){
 const sum=lotSummary(lot)
 return {
  code:lot.code,zone:lot.zone,state:sum.count?LOT_STATE[sum.state]||'entered':'empty',
  stateLabel:sum.count?stateLabels[sum.state]:props.editable?'Chưa nhập':'Chưa có số',
  line:sum.count?sum.count+' việc'+(sum.works.length?': '+sum.works.join(', '):''):'',
  todo:!sum.count&&props.editable?'Chưa nhập hôm nay: bấm để nhập':'',
  ribbons:(lot.colours||[]).map(c=>({code:c.code,label:c.label,week:c.week,count:c.left})),
  quarantineUntil:lot.quarantine_until||'',
  facts:lot.assignments.length?['Được giao: '+given(lot)]:[],
 }
}
function addLot(block){if(!block)return;added.value.push(block);const lot=props.lots.find(l=>l.block===block);if(lot)emit('open',lot)}
</script>

<template>
 <section class="lot-cards" :class="{'lot-cards--mobile':mobile}">
  <LotCard v-for="lot in shown" :key="lot.block" class="lot-card lot-card__main" :lot="card(lot)" :today="today" @open="emit('open',lot)"/>
  <p v-if="!shown.length" class="lotus-form-note">Tổ chưa được giao lô nào. Chọn lô ở dưới để nhập việc đã làm.</p>
  <div v-if="editable&&others.length" class="lot-cards__add"><LotusField :model-value="''" label="Nhập cho lô khác" :options="others" placeholder="Chọn lô…" :mobile="mobile" @update:model-value="addLot"/></div>
 </section>
</template>

<style>
.lot-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;align-items:start}
.lot-cards--mobile{grid-template-columns:1fr}
.lot-cards__add{grid-column:1/-1;max-width:360px}
</style>

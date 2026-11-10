<script setup>
import {computed,ref} from 'vue'
import LotusField from '../form/LotusField.vue'
import {formatDate} from '../../format'
import {lotSummary,stateLabels,stateTone,amountText,swatch} from '../../lot-entry-model.js'
// The lô of a tổ for a day, one card each: what was entered, what is given to the tổ, the colours still on the plants and
// a quarantine. Tap a card to open its dialog. Lô outside the giao việc can be added from the list.
const props=defineProps({lots:{type:Array,required:true},works:{type:Array,default:()=>[]},editable:Boolean,mobile:Boolean})
const emit=defineEmits(['open'])
const added=ref([])
const shown=computed(()=>props.lots.filter(l=>l.active||added.value.includes(l.block)))
const others=computed(()=>props.lots.filter(l=>!l.active&&!added.value.includes(l.block)).map(l=>({value:l.block,label:'Lô '+l.code+' · khu '+l.zone})))
const workLabel=name=>props.works.find(w=>w.name===name)?.label||name
function addLot(block){if(!block)return;added.value.push(block);const lot=props.lots.find(l=>l.block===block);if(lot)emit('open',lot)}
</script>

<template>
 <section class="lot-cards" :class="{'lot-cards--mobile':mobile}">
  <article v-for="lot in shown" :key="lot.block" class="lot-card" :class="'is-'+(stateTone[lotSummary(lot).state]||'idle')">
   <button type="button" class="lot-card__main" @click="emit('open',lot)">
    <strong>Lô {{lot.code}} <small>khu {{lot.zone}}</small></strong>
    <span v-if="lotSummary(lot).count">{{lotSummary(lot).count}} việc · {{stateLabels[lotSummary(lot).state]}}</span>
    <span v-else class="lot-card__todo">{{editable?'Chưa nhập hôm nay: bấm để nhập':'Chưa có số hôm nay'}}</span>
    <span v-if="lot.assignments.length" class="lot-card__given">Được giao: {{lot.assignments.map(a=>a.kind==='Round'?workLabel(a.work_type)+(a.due_date?' (hạn '+formatDate(a.due_date)+')':''):'chăm buồng').join(', ')}}</span>
    <span v-if="lot.colours.length" class="lot-card__colours">
     <i v-for="c in lot.colours.slice(0,4)" :key="c.tag" :title="c.label+' tuần '+c.week+': còn '+c.left+' buồng'"><b :style="{background:swatch(c.code)}" aria-hidden="true"></b>{{c.label}} {{amountText(c.left)}}</i>
    </span>
    <em v-if="lot.quarantine_until" class="lot-card__held">Cách ly thuốc đến {{formatDate(lot.quarantine_until)}}</em>
   </button>
  </article>
  <p v-if="!shown.length" class="lotus-form-note">Tổ chưa được giao lô nào. Chọn lô ở dưới để nhập việc đã làm.</p>
  <div v-if="editable&&others.length" class="lot-cards__add"><LotusField :model-value="''" label="Nhập cho lô khác" :options="others" placeholder="Chọn lô…" :mobile="mobile" @update:model-value="addLot"/></div>
 </section>
</template>

<style>
.lot-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;align-items:start}
.lot-cards--mobile{grid-template-columns:1fr}
.lot-cards__add{grid-column:1/-1;max-width:360px}
.lot-card{border:1px solid var(--lotus-border);border-left-width:4px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.lot-card.is-success{border-left-color:var(--lotus-success)}
.lot-card.is-info{border-left-color:var(--lotus-primary)}
.lot-card.is-warning,.lot-card.is-neutral{border-left-color:var(--lotus-warning)}
.lot-card__main{display:grid;gap:3px;width:100%;padding:10px 12px;text-align:left;font:inherit;color:inherit;background:none;border:0;cursor:pointer}
.lot-card__main strong{font-weight:600;color:var(--lotus-text-strong)}
.lot-card__main small{font-weight:400;color:var(--lotus-muted)}
.lot-card__main span,.lot-card__main em{font-size:var(--lotus-text-sm);color:var(--lotus-muted);font-style:normal}
.lot-card__todo{color:var(--lotus-primary-text)!important}
.lot-card__colours{display:flex;flex-wrap:wrap;gap:4px 10px}
.lot-card__colours i{display:inline-flex;align-items:center;gap:4px;font-style:normal}
.lot-card__colours b{display:inline-block;width:10px;height:10px;border-radius:50%;border:1px solid var(--lotus-border)}
.lot-card__held{color:var(--lotus-danger)!important}
</style>

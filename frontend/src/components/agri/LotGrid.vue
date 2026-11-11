<script setup>
import {computed} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {LOT_STATES,groupLots,zoneColour} from '../../lot-states.js'
// The whole farm at a glance (FR-030): every lot as a tile, grouped by khu, coloured by one state per lot with an icon
// and a legend with counts, so the state never depends on colour alone. Tiles are buttons; v-model is the chosen lot code.
// lots: [{code, zone?, state, title?}]; states: the legend order (a LOT_METRICS[...].states list).
const props=defineProps({lots:{type:Array,required:true},states:{type:Array,default:()=>Object.keys(LOT_STATES)},label:{type:String,default:'Lô của vườn'},zoneLabel:{type:String,default:'Khu'}})
const emit=defineEmits(['select'])
const model=defineModel({type:String,default:''})
const grouped=computed(()=>groupLots(props.lots))
const legend=computed(()=>props.states.map(state=>({state,...(LOT_STATES[state]||{label:state,icon:''}),count:grouped.value.counts[state]||0})))
function choose(lot){model.value=lot.code;emit('select',lot)}
const describe=lot=>'Lô '+lot.code+': '+(lot.title||LOT_STATES[lot.state]?.label||lot.state)
</script>
<template>
 <section class="lotus-lotgrid" :aria-label="label">
  <div class="lotus-lotgrid__zones">
   <div v-for="group in grouped.groups" :key="group.zone" class="lotus-lotgrid__zone" role="group" :aria-label="zoneLabel+' '+group.zone">
    <div class="lotus-lotgrid__zone-head"><span class="lotus-lotgrid__zone-swatch" :style="{'--zone':zoneColour(group.zone)}" aria-hidden="true"/>{{zoneLabel}} {{group.zone}}<small>{{group.lots.length}} lô</small></div>
    <ul class="lotus-lotgrid__tiles">
     <li v-for="lot in group.lots" :key="lot.code"><button type="button" class="lotus-lot-tile" :data-state="lot.state||'empty'" :aria-pressed="model===lot.code" :aria-label="describe(lot)" :title="describe(lot)" @click="choose(lot)"><LotusIcon v-if="LOT_STATES[lot.state]?.icon" :name="LOT_STATES[lot.state].icon"/>{{lot.code}}</button></li>
    </ul>
   </div>
  </div>
  <ul class="lotus-lotgrid__legend" aria-label="Chú giải">
   <li v-for="item in legend" :key="item.state"><span class="lotus-lot-tile" :data-state="item.state" aria-hidden="true"><LotusIcon v-if="item.icon" :name="item.icon"/></span>{{item.label}} <b>{{item.count}}</b></li>
  </ul>
 </section>
</template>

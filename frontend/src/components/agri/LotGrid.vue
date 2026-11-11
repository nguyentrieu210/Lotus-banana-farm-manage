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

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-lotgrid{display:grid;gap:14px;min-width:0}
.lotus-lotgrid__zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px 16px}
.lotus-lotgrid__zone{display:grid;align-content:start;gap:6px;min-width:0}
.lotus-lotgrid__zone-head{display:flex;align-items:center;gap:8px;color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-semibold)}
.lotus-lotgrid__zone-head small{margin-left:auto;color:var(--lotus-muted);font-weight:var(--lotus-weight-regular);font-variant-numeric:tabular-nums}
.lotus-lotgrid__zone-swatch{width:10px;height:10px;border-radius:3px;background:var(--zone,var(--lotus-border-strong));box-shadow:inset 0 0 0 1px rgb(0 0 0/.15)}
.lotus-lotgrid__tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--tile,46px),1fr));gap:4px;margin:0;padding:0;list-style:none}
.lotus-lot-tile{--tile-bg:var(--lotus-lot-empty);--tile-fg:var(--lotus-lot-empty-on);position:relative;display:grid;place-items:center;width:100%;min-height:38px;aspect-ratio:1.2/1;padding:0;border:1px solid transparent;border-radius:var(--lotus-radius-sm);background:var(--tile-bg);color:var(--tile-fg);font:inherit;font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-bold);font-variant-numeric:tabular-nums;cursor:pointer;transition:transform var(--lotus-motion-fast) var(--lotus-ease),box-shadow var(--lotus-motion-fast) var(--lotus-ease)}
.lotus-lot-tile>.lotus-icon{position:absolute;top:3px;right:3px;width:11px;height:11px;stroke-width:2.6}
.lotus-lot-tile:hover{z-index:1;transform:translateY(-1px);box-shadow:var(--lotus-shadow-md)}
.lotus-lot-tile:focus-visible{z-index:1;outline:none;box-shadow:var(--lotus-focus)}
.lotus-lot-tile[aria-pressed="true"]{z-index:1;box-shadow:0 0 0 2px var(--lotus-surface),0 0 0 4px var(--lotus-text-strong)}
[data-state="empty"]>.lotus-lot-tile,.lotus-lot-tile[data-state="empty"]{border:1px dashed var(--lotus-border-strong)}
.lotus-lot-tile[data-state="entered"]{--tile-bg:var(--lotus-lot-entered);--tile-fg:var(--lotus-lot-entered-on)}
.lotus-lot-tile[data-state="sent"]{--tile-bg:var(--lotus-lot-sent);--tile-fg:var(--lotus-lot-sent-on)}
.lotus-lot-tile[data-state="confirmed"]{--tile-bg:var(--lotus-lot-confirmed);--tile-fg:var(--lotus-lot-confirmed-on)}
.lotus-lot-tile[data-state="ok"]{--tile-bg:var(--lotus-lot-ok);--tile-fg:var(--lotus-lot-ok-on)}
.lotus-lot-tile[data-state="due"]{--tile-bg:var(--lotus-lot-due);--tile-fg:var(--lotus-lot-due-on)}
.lotus-lot-tile[data-state="overdue"]{--tile-bg:var(--lotus-lot-overdue);--tile-fg:var(--lotus-lot-overdue-on)}
.lotus-lot-tile[data-state="quarantine"]{--tile-bg:var(--lotus-lot-quarantine);--tile-fg:var(--lotus-lot-quarantine-on);border-color:var(--lotus-tone-danger-border);background-image:repeating-linear-gradient(135deg,var(--lotus-lot-quarantine-stripe) 0 3px,transparent 3px 8px)}
.lotus-lotgrid__legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:0;padding:0;list-style:none;color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm)}
.lotus-lotgrid__legend li{display:inline-flex;align-items:center;gap:6px}
.lotus-lotgrid__legend .lotus-lot-tile{width:22px;min-height:18px;aspect-ratio:auto;height:18px;cursor:default;pointer-events:none}
.lotus-lotgrid__legend .lotus-lot-tile>.lotus-icon{top:2px;right:2px;width:9px;height:9px}
.lotus-lotgrid__legend b{color:var(--lotus-text-strong);font-variant-numeric:tabular-nums}
</style>

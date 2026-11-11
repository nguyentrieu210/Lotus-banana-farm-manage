<script setup>
import {computed} from 'vue'
import {zoneColour} from '../../lot-states.js'
// A khu with its fixed map colour (FR-036): the same colour on the map, the lot grid and in tables.
const props=defineProps({zone:{type:String,required:true},label:String})
const letter=computed(()=>String(props.zone).slice(0,1).toUpperCase())
</script>
<template>
 <span class="lotus-zone-chip"><span class="lotus-zone-chip__swatch" :style="{'--zone':zoneColour(letter)}" aria-hidden="true">{{letter}}</span>{{label||'Khu '+zone}}</span>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-zone-chip{display:inline-flex;align-items:center;gap:6px;height:var(--lotus-chip-height);padding:0 10px 0 3px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-full);background:var(--lotus-surface);color:var(--lotus-text);font-size:var(--lotus-chip-font);font-weight:var(--lotus-weight-semibold);white-space:nowrap}
.lotus-zone-chip__swatch{display:grid;place-items:center;width:16px;height:16px;border-radius:50%;background:var(--zone);color:var(--lotus-neutral-900);font-size:9.5px;font-weight:800;box-shadow:inset 0 0 0 1px rgb(0 0 0/.18)}
</style>

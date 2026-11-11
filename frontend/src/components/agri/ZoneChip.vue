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

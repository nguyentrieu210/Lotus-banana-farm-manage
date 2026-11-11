<script setup>
import {computed} from 'vue'
import {isoWeek,sameWeek,weekRange} from '../../agri-format.js'
// An ISO week (FR-032): "T46", marked when it is this week or a harvest week. Give year+week or a date.
const props=defineProps({year:Number,week:Number,date:String,today:String,harvest:Boolean,long:Boolean})
const value=computed(()=>props.date?isoWeek(props.date):props.year&&props.week?{year:props.year,week:props.week}:null)
const current=computed(()=>!!props.today&&sameWeek(isoWeek(props.today),value.value))
</script>
<template>
 <span v-if="value" class="lotus-week" :class="{'lotus-week--current':current,'lotus-week--harvest':harvest&&!current}" :title="'Tuần '+value.week+'/'+value.year+': '+weekRange(value)" :aria-label="'Tuần '+value.week+' năm '+value.year+(current?', tuần này':'')+(harvest?', tuần thu':'')">{{long?'Tuần '+value.week:'T'+value.week}}</span>
</template>

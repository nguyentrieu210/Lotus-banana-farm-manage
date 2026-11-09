<script setup>
import {computed} from 'vue'
import './report.css'
// A lô by week grid: darker is more. A column heading or cell opens that week.
const props=defineProps({title:{type:String,required:true},grid:{type:Object,required:true}})
const emit=defineEmits(['open'])
const num=n=>Number(n||0).toLocaleString('vi-VN')
const top=computed(()=>Math.max(1,...props.grid.rows.flatMap(r=>r.values)))
const step=v=>!v?0:Math.min(5,Math.ceil(v/top.value*5))
const template=computed(()=>({gridTemplateColumns:'64px repeat('+props.grid.columns.length+',minmax(42px,1fr))'}))
</script>

<template>
 <section class="lotus-chart-card heat-grid" :aria-label="title">
  <header class="lotus-chart-head"><div><h3>{{title}}</h3></div></header>
  <p v-if="!grid.rows.length" class="lotus-chart-empty">Chưa có số trong phần đang lọc.</p>
  <div v-else class="heat-grid__scroll">
   <div class="heat-grid__row heat-grid__row--head" :style="template"><span></span><span v-for="c in grid.columns" :key="c.key">{{c.name}}</span></div>
   <div v-for="r in grid.rows" :key="r.key" class="heat-grid__row" :style="template">
    <strong>{{r.key}}</strong>
    <button v-for="(v,i) in r.values" :key="i" type="button" class="heat-grid__cell" :class="'is-'+step(v)" :aria-label="r.key+', '+grid.columns[i].name+': '+num(v)" @click="emit('open',grid.columns[i].key)">{{v?num(v):''}}</button>
   </div>
  </div>
 </section>
</template>

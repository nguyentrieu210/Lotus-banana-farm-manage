<script setup>
import {computed,ref} from 'vue'
import DataTable from './DataTable.vue'
// Stacked columns of bunches by how certain they are. The order is ordinal (đã cắt → đã chích → ước tính), so one blue ramp, dark for the most certain.
// Each column is the hit target: hover or focus shows every part, a click opens the detail when `clickable`. The numbers are also in the table below.
const props=defineProps({items:{type:Array,default:()=>[]},format:{type:Function,required:true},unit:{type:String,default:''},clickable:Boolean,label:{type:String,required:true},series:{type:Array,default:()=>[{id:'cut',name:'Đã cắt'},{id:'inject',name:'Đã chích'},{id:'est',name:'Ước tính'}]}})
const emit=defineEmits(['select'])
const HEIGHT=220
const totalOf=i=>props.series.reduce((n,s)=>n+Number(i.values[s.id]||0),0)
function niceMax(value){
 if(value<=0)return 1
 const power=10**Math.floor(Math.log10(value)),scaled=value/power
 return [1,1.5,2,3,4,5,6,8,10].find(s=>s>=scaled)*power
}
const top=computed(()=>niceMax(Math.max(0,...props.items.map(totalOf))))
const ticks=computed(()=>[0,.5,1].map(f=>({value:top.value*f,y:f*HEIGHT})))
const compact=v=>v>=10000?props.format(v/1000)+'K':props.format(v)
// A short number on the tallest column, and on the tallest one that is real numbers only: never one on every column.
const labelled=computed(()=>{
 const keys=new Set(),byTotal=[...props.items].sort((a,b)=>totalOf(b)-totalOf(a))
 if(byTotal[0]&&totalOf(byTotal[0]))keys.add(byTotal[0].key)
 const real=byTotal.filter(i=>totalOf(i)&&!i.values.est)[0]
 if(real)keys.add(real.key)
 return keys
})
function bars(item){
 const parts=props.series.map(s=>({...s,value:Number(item.values[s.id]||0)})).filter(p=>p.value>0)
 return parts.map((p,i)=>({...p,height:Math.max(2,p.value/top.value*HEIGHT),last:i===parts.length-1}))
}
const describe=i=>i.title+': '+(totalOf(i)?props.format(totalOf(i))+' '+props.unit+', '+props.series.filter(s=>i.values[s.id]).map(s=>s.name.toLowerCase()+' '+props.format(i.values[s.id])).join(', '):'chưa có số')
const hover=ref(null),plot=ref(null),tableOpen=ref(false)
const tableRows=computed(()=>props.items.map(i=>({key:i.key,title:i.title,...i.values,total:totalOf(i)})))
const tableColumns=computed(()=>[{field:'title',headerName:'Kỳ',minWidth:190},...props.series.map(s=>({field:s.id,headerName:s.name,minWidth:100,valueFormatter:p=>props.format(p.value||0)})),{field:'total',headerName:'Tổng ('+props.unit+')',minWidth:110,valueFormatter:p=>props.format(p.value||0)}])
function show(item,event){
 const box=plot.value?.getBoundingClientRect(),target=event.currentTarget.getBoundingClientRect()
 hover.value={item,left:box?target.left-box.left+target.width/2:0}
}
function hide(){hover.value=null}
function open(item){if(props.clickable&&totalOf(item))emit('select',item)}
</script>

<template>
 <figure class="bunch-chart" role="group" :aria-label="label">
  <ul v-if="series.length>1" class="bunch-chart__legend">
   <li v-for="s in series" :key="s.id"><span class="bunch-chart__key" :class="'is-'+s.id" aria-hidden="true"></span>{{s.name}}</li>
  </ul>
  <div class="bunch-chart__body">
   <div class="bunch-chart__axis" :style="{height:HEIGHT+'px'}" aria-hidden="true"><span v-for="t in ticks" :key="t.y" :style="{bottom:t.y+'px'}">{{compact(t.value)}}</span></div>
   <div ref="plot" class="bunch-chart__plot">
    <div class="bunch-chart__grid" :style="{height:HEIGHT+'px'}" aria-hidden="true"><i v-for="t in ticks" :key="t.y" :style="{bottom:t.y+'px'}"></i></div>
    <div class="bunch-chart__columns">
     <component :is="clickable&&totalOf(i)?'button':'div'" v-for="i in items" :key="i.key" :type="clickable&&totalOf(i)?'button':undefined" :tabindex="clickable&&totalOf(i)?undefined:0" class="bunch-col" :class="{'is-empty':!totalOf(i)}" :aria-label="describe(i)" @mouseenter="show(i,$event)" @mouseleave="hide" @focus="show(i,$event)" @blur="hide" @click="open(i)">
      <span class="bunch-col__stack" :style="{height:HEIGHT+'px'}">
       <span v-if="labelled.has(i.key)" class="bunch-col__cap">{{format(totalOf(i))}}</span>
       <span v-for="p in bars(i)" :key="p.id" class="bunch-col__part" :class="['is-'+p.id,{'is-top':p.last}]" :style="{height:p.height+'px'}"></span>
      </span>
      <span class="bunch-col__name">{{i.name}}</span>
     </component>
    </div>
    <div v-if="hover" class="bunch-chart__tip" role="presentation" :style="{left:hover.left+'px'}">
     <strong>{{hover.item.title}}</strong>
     <span v-if="!totalOf(hover.item)">Chưa có số</span>
     <template v-else>
      <span v-for="s in series.filter(x=>hover.item.values[x.id])" :key="s.id"><i class="bunch-chart__line" :class="'is-'+s.id"></i><b>{{format(hover.item.values[s.id])}}</b> {{s.name.toLowerCase()}}</span>
      <span><b>{{format(totalOf(hover.item))}}</b> {{unit}}</span>
     </template>
    </div>
   </div>
  </div>
  <details class="bunch-chart__table" @toggle="tableOpen=$event.target.open">
   <summary>Xem số dạng bảng</summary>
   <DataTable v-if="tableOpen" :rows="tableRows" :columns="tableColumns" row-key="key" storage-key="bunch-chart-table"/>
  </details>
 </figure>
</template>

<style>
.bunch-chart{--bunch-cut:var(--lotus-info-800);--bunch-inject:var(--lotus-info-500);--bunch-est:var(--lotus-info-300);display:grid;gap:8px;margin:0;min-width:0}
:root.dark .bunch-chart{--bunch-cut:var(--lotus-info-200);--bunch-inject:var(--lotus-info-400);--bunch-est:var(--lotus-info-500)}
.bunch-chart .is-cut{background:var(--bunch-cut)}
.bunch-chart .is-inject{background:var(--bunch-inject)}
.bunch-chart .is-est{background:var(--bunch-est)}
.bunch-chart__legend{display:flex;flex-wrap:wrap;gap:14px;margin:0;padding:0;list-style:none;font-size:var(--lotus-text-sm);color:var(--lotus-text-secondary)}
.bunch-chart__legend li{display:flex;align-items:center;gap:6px}
.bunch-chart__key{display:inline-block;width:10px;height:10px;border-radius:2px}
.bunch-chart__body{display:grid;grid-template-columns:44px minmax(0,1fr);gap:6px}
.bunch-chart__axis{position:relative;margin-top:18px}
.bunch-chart__axis span{position:absolute;right:0;transform:translateY(50%);font-size:var(--lotus-text-xs);color:var(--lotus-muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.bunch-chart__plot{position:relative;min-width:0;padding-top:18px}
.bunch-chart__grid{position:absolute;top:18px;left:0;right:0;pointer-events:none}
.bunch-chart__grid i{position:absolute;left:0;right:0;border-top:1px solid var(--lotus-border)}
.bunch-chart__columns{position:relative;display:flex;gap:2px}
.bunch-col{flex:1 1 0;min-width:0;display:grid;justify-items:center;gap:6px;padding:0;border:0;background:none;color:inherit;font:inherit;border-radius:4px}
button.bunch-col{cursor:pointer}
button.bunch-col:hover .bunch-col__part{filter:brightness(1.08)}
.bunch-col:focus-visible{outline:2px solid var(--lotus-primary);outline-offset:1px}
.bunch-col__stack{position:relative;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:2px;width:min(24px,100%)}
.bunch-col__part{display:block;flex:none;width:100%}
.bunch-col__part.is-top{border-radius:4px 4px 0 0}
.bunch-col__cap{flex:none;margin-bottom:2px;font-size:var(--lotus-text-xs);font-weight:600;color:var(--lotus-text-strong);font-variant-numeric:tabular-nums;white-space:nowrap}
.bunch-col__name{font-size:var(--lotus-text-xs);color:var(--lotus-muted);white-space:nowrap}
.bunch-col.is-empty .bunch-col__name{color:var(--lotus-subtle,var(--lotus-muted))}
.bunch-chart__tip{position:absolute;top:0;z-index:3;display:grid;gap:2px;transform:translateX(-50%);padding:8px 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-md);font-size:var(--lotus-text-sm);white-space:nowrap;pointer-events:none}
.bunch-chart__tip span{display:flex;align-items:center;gap:6px;color:var(--lotus-text-secondary)}
.bunch-chart__tip b{color:var(--lotus-text-strong);font-variant-numeric:tabular-nums}
.bunch-chart__line{display:inline-block;width:10px;height:2px;border-radius:1px}
.bunch-chart__table summary{cursor:pointer;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>

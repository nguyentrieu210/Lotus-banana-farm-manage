<script setup>
import {computed} from 'vue'
const props=defineProps({collection:Object})
const emit=defineEmits(['open'])
const features=computed(()=>props.collection?.features||[])
const points=computed(()=>features.value.flatMap(f=>{
  const g=f.geometry||{}
  const polys=g.type==='Polygon'?[g.coordinates]:(g.type==='MultiPolygon'?g.coordinates:[])
  return polys.flatMap(p=>p.flatMap(r=>r))
}).filter(p=>Array.isArray(p)&&Number.isFinite(Number(p[0]))&&Number.isFinite(Number(p[1]))))
const bounds=computed(()=>{
  if(!points.value.length)return null
  const xs=points.value.map(p=>Number(p[0])),ys=points.value.map(p=>Number(p[1]))
  return {xmin:Math.min(...xs),xmax:Math.max(...xs),ymin:Math.min(...ys),ymax:Math.max(...ys)}
})
function project(p){
  const b=bounds.value;if(!b)return [0,0]
  const w=b.xmax-b.xmin||1,h=b.ymax-b.ymin||1,scale=Math.min(900/w,440/h)
  return [50+(Number(p[0])-b.xmin)*scale,490-(Number(p[1])-b.ymin)*scale]
}
function path(feature){
  const g=feature.geometry||{},polys=g.type==='Polygon'?[g.coordinates]:(g.type==='MultiPolygon'?g.coordinates:[])
  return polys.map(poly=>poly.map(ring=>'M '+ring.map(p=>project(p).join(',')).join(' L ')+' Z').join(' ')).join(' ')
}
</script>
<template>
  <div v-if="!features.length" class="empty">Chưa có ranh giới thửa được duyệt trong nông trường này.</div>
  <div v-else class="plot-map-wrap">
    <svg class="plot-map" viewBox="0 0 1000 540" role="img" aria-label="Bản đồ ranh giới thửa đã duyệt">
      <g v-for="feature in features" :key="feature.properties?.document||feature.properties?.plot">
        <path :d="path(feature)" fill-rule="evenodd" tabindex="0"
          :aria-label="'Mở thửa '+feature.properties?.plot"
          @click="emit('open',feature.properties?.plot)"
          @keydown.enter="emit('open',feature.properties?.plot)">
          <title>{{feature.properties?.plot}} · v{{feature.properties?.version}}</title>
        </path>
      </g>
    </svg>
    <p class="muted">Chỉ hiển thị phiên bản ranh giới đã duyệt. Bấm vào thửa để mở lịch sử.</p>
  </div>
</template>

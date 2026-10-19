<script setup>
import {ref,onMounted,onBeforeUnmount,onActivated,onDeactivated,watch} from 'vue'
import L from 'leaflet'
import union from 'polygon-clipping'
import 'leaflet/dist/leaflet.css'
import {alignedTiles} from '../map-imagery'
import {imagery} from '../map-imagery-config'
import {Button as UiButton} from './ui/button'
const props=defineProps({collection:Object,farm:String})
const emit=defineEmits(['open'])
const canvas=ref(null),error=ref(''),count=ref(0),drafts=ref(false)
let map,blocks,zones,flycam,observer
const features=()=>props.collection?.features||[]
function content(f){const el=document.createElement('span');el.textContent=`${f.properties.code} · ${Number(f.properties.area_ha||0).toLocaleString('vi-VN')} ha`;return el}
function draw(){
 if(!map)return
 if(blocks)blocks.remove();if(zones)zones.remove()
 const rows=features();count.value=rows.length;drafts.value=rows.some(f=>f.properties.approval_state==='Draft');error.value=''
 blocks=L.geoJSON({type:'FeatureCollection',features:rows},{style:{color:'var(--lotus-primary-300)',weight:1.5,fillOpacity:0},onEachFeature(f,layer){layer.bindTooltip(content(f),{permanent:map.getZoom()>=16.5,direction:'center',className:'care-map-label'});layer.on('click',()=>emit('open',f.properties.block))}}).addTo(map)
 try{
  const byZone=new Map()
  for(const f of rows){const z=f.properties.zone;if(!z)continue;const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;byZone.set(z,[...(byZone.get(z)||[]),...polygons])}
  const shapes=[...byZone].map(([zone,polygons])=>({type:'Feature',properties:{zone},geometry:{type:'MultiPolygon',coordinates:union.union(...polygons.map(p=>[p]))}}))
  zones=L.geoJSON({type:'FeatureCollection',features:shapes},{interactive:false,style:{color:'var(--lotus-warning-300)',weight:3,fillOpacity:0,dashArray:'8 4'},onEachFeature(f,layer){const label=document.createElement('strong');label.textContent='Khu '+f.properties.zone;layer.bindTooltip(label,{permanent:true,direction:'center',className:'care-map-zone'})}}).addTo(map)
 }catch{error.value='Không dựng được ranh khu. Ranh từng lô vẫn được hiển thị.'}
 fit()
}
function fit(){if(blocks?.getBounds().isValid())map.fitBounds(blocks.getBounds(),{padding:[24,24],maxZoom:18})}
function background(){
 if(flycam){flycam.remove();flycam=null}
 if(props.farm==='LOTUS-222')flycam=alignedTiles(L,'https://map.gpcds.site/v2/tiles/farm222/{z}/{x}/{y}.webp?v=20261016-116292',{minZoom:12,maxZoom:22,maxNativeZoom:22,bounds:imagery.bounds,noWrap:true,keepBuffer:2,updateWhenIdle:true,errorTileUrl:'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=',attribution:'Ảnh flycam Lotus Farm 222'},imagery.displayAlignment).addTo(map)
}
onMounted(()=>{
 map=L.map(canvas.value,{minZoom:12,maxZoom:22}).setView([11.602,106.79],15)
 L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:22,maxNativeZoom:19,attribution:'Ảnh vệ tinh © Esri'}).addTo(map)
 background();observer=new ResizeObserver(()=>map?.invalidateSize());observer.observe(canvas.value)
 map.on('zoomend',()=>blocks?.eachLayer(layer=>{const tooltip=layer.getTooltip();if(tooltip){tooltip.options.permanent=map.getZoom()>=16.5;if(tooltip.options.permanent)layer.openTooltip();else layer.closeTooltip()}}));draw()
})
watch(()=>props.collection,draw)
watch(()=>props.farm,()=>{if(map)background()})
onActivated(()=>map?.invalidateSize())
onDeactivated(()=>map?.stop())
onBeforeUnmount(()=>{observer?.disconnect();map?.remove();map=null})
</script>
<template><section class="care-map"><div class="care-map-toolbar"><span>{{count}} lô chăm sóc<span v-if="drafts"> · Ranh nhập từ Lotus Map, chưa duyệt</span></span><UiButton size="sm" variant="outline" @click="fit">Xem toàn bộ</UiButton></div><p v-if="error" role="alert" class="error">{{error}}</p><p v-if="!count" class="notice" role="status">Chưa có ranh lô chăm sóc trong phạm vi đã chọn.</p><div ref="canvas" class="care-map-canvas" role="region" aria-label="Bản đồ flycam, ranh khu và lô chăm sóc"/></section></template>

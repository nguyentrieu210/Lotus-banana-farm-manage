<script setup>
import {ref,computed,onMounted,onBeforeUnmount,onActivated,onDeactivated,watch} from 'vue'
import L from 'leaflet'
import union from 'polygon-clipping'
import 'leaflet/dist/leaflet.css'
import {alignedTiles} from '../map-imagery'
import {imagery} from '../map-imagery-config'
import {zoneColor,zoneCenter} from '../map-zones'
import {Button as UiButton} from './ui/button'
import LotusIcon from './LotusIcon.vue'
import {distance,area,crosses,measureLabel,feature} from '../map-measure'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
const props=defineProps({collection:Object,farm:String,user:String})
const emit=defineEmits(['open','reset'])
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask:confirm,finish:finishConfirm}=useWorkspaceConfirm()
const canvas=ref(null),error=ref(''),count=ref(0),drafts=ref(false)
const mode=ref(''),points=ref([]),saved=ref([]),drawingError=ref('')
const measurement=computed(()=>points.value.length?measureLabel(mode.value,points.value):'Chọn các điểm trên bản đồ')
const canFinish=computed(()=>points.value.length>=(mode.value==='area'?3:2))
let map,blocks,zones,zoneLabels,zoneHalo,perimeter,openEdges,flycam,observer,sketches,preview
const shownZones=computed(()=>[...new Set([...features(),...(props.collection?.open_features||[])].map(f=>f.properties.zone).filter(Boolean))].sort())
const storageKey=()=>`lotus-map-sketch|${props.user}|${props.farm}`
function persist(){if(!props.user||!props.farm)return;try{localStorage.setItem(storageKey(),JSON.stringify(saved.value))}catch{drawingError.value='Không lưu được nét vẽ trên máy. Hãy xuất GeoJSON để giữ lại.'}}
function restore(){cancel();saved.value=[];if(props.user&&props.farm)try{const rows=JSON.parse(localStorage.getItem(storageKey())||'[]');saved.value=rows.filter(f=>['LineString','Polygon'].includes(f.geometry?.type)).slice(0,500)}catch{};renderSketches()}
function label(text){const el=document.createElement('span');el.textContent=text;return el}
function renderSketches(){
 if(!sketches)return
 sketches.clearLayers()
 for(const [index,f] of saved.value.entries())L.geoJSON(f,{style:{color:'var(--lotus-primary)',weight:3,fillOpacity:.16},onEachFeature(_,layer){const ps=f.geometry.type==='Polygon'?f.geometry.coordinates[0].slice(0,-1):f.geometry.coordinates;layer.bindTooltip(label(measureLabel(f.geometry.type==='Polygon'?'area':'line',ps.map(([lng,lat])=>({lat,lng})))));layer.on('click',()=>{if(!mode.value){selected.value=index}})}}).addTo(sketches)
}
const selected=ref(-1)
function start(kind){cancel();mode.value=kind;map?.doubleClickZoom.disable()}
function cancel(){mode.value='';points.value=[];drawingError.value='';preview?.clearLayers();map?.doubleClickZoom.enable()}
function renderPreview(){
 preview.clearLayers()
 if(points.value.length>1)(mode.value==='area'?L.polygon(points.value,{color:'var(--lotus-primary)',weight:3,fillOpacity:.15,interactive:false}):L.polyline(points.value,{color:'var(--lotus-primary)',weight:3,interactive:false})).addTo(preview)
 for(const p of points.value)L.circleMarker(p,{radius:4,color:'var(--lotus-primary)',fillOpacity:1,interactive:false}).addTo(preview)
}
function addPoint(event){if(!mode.value||!props.farm)return;const p=event.latlng,last=points.value.at(-1);if(last&&distance([last,p])<.1)return;points.value=[...points.value,{lat:p.lat,lng:p.lng}];drawingError.value='';renderPreview()}
function undo(){points.value=points.value.slice(0,-1);drawingError.value='';renderPreview()}
function finish(){
 if(!canFinish.value)return
 if(mode.value==='area'&&(crosses(points.value)||area(points.value)<.01)){drawingError.value='Vùng phải có diện tích và không được tự cắt. Hãy lùi điểm để sửa.';return}
 saved.value=[...saved.value,feature(mode.value,points.value)];selected.value=saved.value.length-1;persist();renderSketches();cancel()
}
function removeSelected(){saved.value=saved.value.filter((_,i)=>i!==selected.value);selected.value=-1;persist();renderSketches()}
async function clearSketches(){if(!await confirm('Xoá toàn bộ nét đo vẽ đã lưu trên máy cho vườn này?'))return;saved.value=[];selected.value=-1;persist();renderSketches()}
function exportSketches(){const url=URL.createObjectURL(new Blob([JSON.stringify({type:'FeatureCollection',features:saved.value},null,2)],{type:'application/geo+json'}));const a=document.createElement('a');a.href=url;a.download=`${props.farm}-do-ve.geojson`;a.click();URL.revokeObjectURL(url)}
const features=()=>props.collection?.features||[]
function content(f){const el=document.createElement('span');el.textContent=`${f.properties.code} · ${Number(f.properties.area_ha||0).toLocaleString('vi-VN')} ha`;return el}
function draw(){
 if(!map)return
 if(blocks)blocks.remove();if(zones)zones.remove();zoneLabels?.remove();zoneHalo?.remove();perimeter?.remove();openEdges?.remove()
 const rows=features();count.value=rows.length+(props.collection?.open_features?.length||0);drafts.value=[...rows,...(props.collection?.open_features||[])].some(f=>f.properties.approval_state==='Draft');error.value=''
 if(props.collection?.perimeter)perimeter=L.geoJSON(props.collection.perimeter,{interactive:false,style:{color:'var(--lotus-neutral-0)',weight:5,fillOpacity:0}}).addTo(map)
 blocks=L.geoJSON({type:'FeatureCollection',features:rows},{style:f=>({color:zoneColor(f.properties.zone),weight:1.5,fillColor:zoneColor(f.properties.zone),fillOpacity:.12}),onEachFeature(f,layer){layer.bindTooltip(content(f),{permanent:map.getZoom()>=16.5,direction:'center',className:'care-map-label'});layer.on('click',event=>{if(mode.value)addPoint(event);else emit('open',f.properties.block)})}}).addTo(map)
 if(props.collection?.open_features?.length)openEdges=L.geoJSON({type:'FeatureCollection',features:props.collection.open_features},{style:f=>({color:zoneColor(f.properties.zone),weight:3,dashArray:'6 5'}),onEachFeature(f,layer){layer.bindTooltip(label(`${f.properties.code} · Ranh chưa khép kín`))}}).addTo(map)
 try{
  const byZone=new Map()
  for(const f of rows){const z=f.properties.zone;if(!z)continue;const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;byZone.set(z,[...(byZone.get(z)||[]),...polygons])}
  const shapes=[...byZone].map(([zone,polygons])=>({type:'Feature',properties:{zone},geometry:{type:'MultiPolygon',coordinates:union.union(...polygons.map(p=>[p]))}}))
  zoneHalo=L.geoJSON({type:'FeatureCollection',features:shapes},{interactive:false,style:{color:'var(--lotus-neutral-950)',weight:7,opacity:.65,fillOpacity:0}}).addTo(map)
  zones=L.geoJSON({type:'FeatureCollection',features:shapes},{interactive:false,style:f=>({color:zoneColor(f.properties.zone),weight:4,opacity:1,fillOpacity:0})}).addTo(map)
  zoneLabels=L.layerGroup().addTo(map)
  for(const f of shapes){const text=document.createElement('strong');text.textContent='Khu '+f.properties.zone;text.style.borderColor=zoneColor(f.properties.zone);L.tooltip({permanent:true,direction:'center',className:'care-map-zone',opacity:1}).setLatLng(zoneCenter(f.geometry)).setContent(text).addTo(zoneLabels)}
 }catch{error.value='Không dựng được ranh khu. Ranh từng lô vẫn được hiển thị.'}
 fit()
}
function fit(){const target=[blocks,openEdges,perimeter].find(layer=>layer?.getBounds().isValid());if(target)map.fitBounds(target.getBounds(),{paddingTopLeft:[32,100],paddingBottomRight:[32,125],maxZoom:18})}
function background(){
 if(flycam){flycam.remove();flycam=null}
 if(['LOTUS-222','LOTUS-180'].includes(props.farm))flycam=alignedTiles(L,'https://map.gpcds.site/v2/tiles/farm222/{z}/{x}/{y}.webp?v=20261016-116292',{minZoom:12,maxZoom:22,maxNativeZoom:22,bounds:imagery.bounds,noWrap:true,keepBuffer:2,updateWhenIdle:true,errorTileUrl:'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=',attribution:'Ảnh flycam Lotus Farm 222'},imagery.displayAlignment).addTo(map)
}
onMounted(()=>{
 map=L.map(canvas.value,{minZoom:12,maxZoom:22,zoomControl:false}).setView([11.602,106.79],15)
 L.control.zoom({position:'bottomright'}).addTo(map)
 sketches=L.featureGroup().addTo(map);preview=L.featureGroup().addTo(map);map.on('click',addPoint)
 restore()
 L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:22,maxNativeZoom:19,attribution:'Ảnh vệ tinh © Esri'}).addTo(map)
 background();observer=new ResizeObserver(()=>map?.invalidateSize());observer.observe(canvas.value)
 map.on('zoomend',()=>blocks?.eachLayer(layer=>{const tooltip=layer.getTooltip();if(tooltip){tooltip.options.permanent=map.getZoom()>=16.5;if(tooltip.options.permanent)layer.openTooltip();else layer.closeTooltip()}}));draw()
})
watch(()=>props.collection,draw)
watch(()=>[props.farm,props.user],()=>{if(map){background();selected.value=-1;restore()}})
onActivated(()=>map?.invalidateSize())
onDeactivated(()=>map?.stop())
onBeforeUnmount(()=>{observer?.disconnect();map?.remove();map=null})
</script>
<template><section class="care-map" :class="{'care-map-drawing':mode}">
 <div ref="canvas" class="care-map-canvas" role="region" aria-label="Bản đồ flycam, ranh khu và lô chăm sóc"/>
 <div class="care-map-filters"><slot name="filters"/></div>
 <div class="care-map-tools" role="toolbar" aria-label="Đo vẽ bản đồ">
  <UiButton size="sm" variant="outline" @click="emit('reset');fit()"><LotusIcon name="target"/>Toàn vườn</UiButton>
  <UiButton size="sm" :variant="mode==='line'?'default':'outline'" :disabled="!farm" :aria-pressed="mode==='line'" @click="start('line')"><LotusIcon name="ruler"/>Đo đường</UiButton>
  <UiButton size="sm" :variant="mode==='area'?'default':'outline'" :disabled="!farm" :aria-pressed="mode==='area'" @click="start('area')"><LotusIcon name="map"/>Đo vùng</UiButton>
  <UiButton size="sm" variant="outline" :disabled="selected<0" @click="removeSelected"><LotusIcon name="trash"/>Xoá nét chọn</UiButton>
  <UiButton size="sm" variant="outline" :disabled="!saved.length" @click="exportSketches"><LotusIcon name="receive"/>GeoJSON</UiButton>
  <UiButton size="sm" variant="outline" :disabled="!saved.length" @click="clearSketches">Xoá tất cả</UiButton>
 </div>
 <div class="care-map-status" aria-live="polite">
  <template v-if="mode"><strong>{{mode==='area'?'Vẽ vùng / đo diện tích':'Vẽ đường / đo khoảng cách'}}</strong><span>{{measurement}} · {{points.length}} điểm</span><div class="actions"><UiButton size="sm" :disabled="!canFinish" @click="finish">Hoàn tất</UiButton><UiButton size="sm" variant="outline" :disabled="!points.length" @click="undo">Lùi điểm</UiButton><UiButton size="sm" variant="outline" @click="cancel">Huỷ</UiButton></div><small>Số đo ước tính. Nét vẽ lưu trên máy theo tài khoản và vườn.</small></template>
  <template v-else><span>{{count}} lô chăm sóc · {{saved.length}} nét vẽ<span v-if="drafts"> · Ranh nhập từ Lotus Map, chưa duyệt</span></span><div class="care-map-legend"><span v-for="z in shownZones" :key="z"><i :style="{background:zoneColor(z)}"/>Khu {{z}}</span></div><small v-if="collection?.open_features?.length">C-13: ranh nguồn chưa khép kín, hiển thị nét đứt.</small><small v-if="!count">{{farm?'Chưa có ranh lô trong phạm vi đã chọn.':'Chọn vườn để xem bản đồ.'}}</small></template>
  <p v-if="error||drawingError" role="alert" class="error">{{drawingError||error}}</p>
 </div>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</section></template>

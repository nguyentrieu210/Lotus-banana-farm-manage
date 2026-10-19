import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {load,mount,tick,window} from './support/mount.mjs'
import L from 'leaflet'
import union from 'polygon-clipping'
L.Browser.svg=true
const CareMap=await load('components/CareMap.vue')
const source=JSON.parse(fs.readFileSync(new URL('../../data/farm222-care-boundaries.geojson',import.meta.url),'utf8'))
const rows=source.features.map(f=>{
 const parts=f.geometry.geometries.flatMap(g=>g.type==='Polygon'?[g.coordinates]:g.coordinates)
 return {type:'Feature',properties:{code:f.properties.id,block:f.properties.id,zone:f.properties.id[0],area_ha:f.properties.areaHa,approval_state:'Draft'},geometry:{type:'MultiPolygon',coordinates:parts}}
})
test('KML source keeps 64 care blocks, all 65 polygons and the detached D2 part',()=>{
 assert.equal(rows.length,64)
 assert.equal(new Set(rows.map(f=>f.properties.code)).size,64)
 assert.equal(rows.reduce((n,f)=>n+f.geometry.coordinates.length,0),65)
 assert.equal(rows.find(f=>f.properties.code==='D2').geometry.coordinates.length,2)
 for(const zone of ['A','B','C','D','E']){
  const polygons=rows.filter(f=>f.properties.zone===zone).flatMap(f=>f.geometry.coordinates)
  assert.ok(union.union(...polygons.map(p=>[p])).length,'zone boundary derives from care polygons')
 }
})
test('care map mounts with imagery, no irrigation layer, and removes itself cleanly',async()=>{
 const view=mount(CareMap,{farm:'LOTUS-222',collection:{type:'FeatureCollection',features:rows.slice(0,1)}})
 await tick()
 assert.ok(view.root.querySelector('.leaflet-container'))
 assert.match(view.root.textContent,/1 lô chăm sóc/)
 assert.match(view.root.textContent,/chưa duyệt/)
 assert.match(view.root.textContent,/Ảnh flycam Lotus Farm 222/)
 assert.doesNotMatch(view.root.textContent,/thửa|tưới/)
 assert.ok(view.root.querySelector('.leaflet-interactive'),'care boundary is clickable')
 view.unmount()
})

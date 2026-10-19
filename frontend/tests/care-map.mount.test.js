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
test('map measurement creates a separate saved line, restores per user and can delete it',async()=>{
 const props={farm:'LOTUS-222',user:'map-test',collection:{type:'FeatureCollection',features:[]}}
 window.localStorage.removeItem('lotus-map-sketch|map-test|LOTUS-222')
 let view=mount(CareMap,props,{filters:()=> 'Bộ lọc trong bản đồ'})
 await tick()
 assert.match(view.root.querySelector('.care-map-filters').textContent,/Bộ lọc trong bản đồ/)
 const button=text=>[...view.root.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
 button('Đo đường').click();await tick()
 assert.equal(button('Hoàn tất').disabled,true)
 const canvas=view.root.querySelector('.leaflet-container')
 canvas.dispatchEvent(new window.MouseEvent('click',{bubbles:true,clientX:100,clientY:100}));await tick()
 canvas.dispatchEvent(new window.MouseEvent('click',{bubbles:true,clientX:200,clientY:200}));await tick()
 assert.match(view.root.querySelector('.care-map-status').textContent,/2 điểm/)
 button('Lùi điểm').click();await tick()
 assert.equal(button('Hoàn tất').disabled,true)
 canvas.dispatchEvent(new window.MouseEvent('click',{bubbles:true,clientX:250,clientY:200}));await tick()
 button('Hoàn tất').click();await tick()
 assert.match(view.root.querySelector('.care-map-status').textContent,/1 nét vẽ/)
 assert.equal(props.collection.features.length,0,'drawing does not modify care boundaries')
 view.unmount();view=mount(CareMap,props);await tick()
 assert.match(view.root.querySelector('.care-map-status').textContent,/1 nét vẽ/)
 view.root.querySelector('.leaflet-interactive').dispatchEvent(new window.MouseEvent('click',{bubbles:true,clientX:100,clientY:100}));await tick()
 button('Xoá nét chọn').click();await tick()
 assert.match(view.root.querySelector('.care-map-status').textContent,/0 nét vẽ/)
 view.unmount()
})

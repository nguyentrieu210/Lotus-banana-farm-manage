import test from 'node:test'
import assert from 'node:assert/strict'
import {distance,area,crosses,feature} from '../src/map-measure.js'
test('spherical distance and area use metres and preserve GeoJSON coordinate order',()=>{
 const square=[{lat:0,lng:0},{lat:0,lng:.001},{lat:.001,lng:.001},{lat:.001,lng:0}]
 assert.ok(Math.abs(distance(square.slice(0,2))-111.195)<.01)
 assert.ok(Math.abs(area(square)-12364.35)<1)
 assert.equal(crosses(square),false)
 assert.equal(crosses([square[0],square[2],square[1],square[3]]),true)
 const f=feature('area',square)
 assert.deepEqual(f.geometry.coordinates[0][0],[0,0])
 assert.deepEqual(f.geometry.coordinates[0].at(-1),[0,0])
 assert.ok(f.properties.area_m2>12000)
 assert.equal(area([]),0)
})

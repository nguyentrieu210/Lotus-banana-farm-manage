import test from 'node:test'
import assert from 'node:assert/strict'
import {zoneCenter,zoneColor} from '../src/map-zones.js'
test('zone colors are distinct and stable when filtering',()=>{
 const colors=['A','B','C','D','E','F'].map(zoneColor)
 assert.equal(new Set(colors).size,6)
 assert.equal(zoneColor('B'),'var(--lotus-map-zone-b)')
})
test('fixed label point stays inside a concave zone and chooses the main component',()=>{
 const ring=[[0,0],[4,0],[4,4],[3,4],[3,1],[1,1],[1,4],[0,4],[0,0]]
 const [lat,lng]=zoneCenter({type:'MultiPolygon',coordinates:[[ring],[[[9,9],[9.1,9],[9.1,9.1],[9,9.1],[9,9]]]]})
 assert.ok(lng>=0&&lng<=4&&lat>=0&&lat<=4)
 assert.ok(lat<=1||lng<=1||lng>=3,'never places the label in the empty concave centre')
 assert.deepEqual(zoneCenter({type:'Polygon',coordinates:[ring]}),zoneCenter({type:'Polygon',coordinates:[ring]}),'viewport independent')
})
test('zone label represents all care lots, rather than the largest individual lot',()=>{
 const square=(x,y,w)=>[[x,y],[x+w,y],[x+w,y+w],[x,y+w],[x,y]]
 const centre=zoneCenter({type:'MultiPolygon',coordinates:[[square(0,0,2)],[square(3,0,1.9)],[square(6,0,1.9)]]})
 assert.ok(centre[1]>3&&centre[1]<5,'centre must be in a middle lot, not the largest left-hand lot')
})

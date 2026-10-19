import polylabel from 'polylabel'
const zones=['A','B','C','D','E','F']
export const zoneColor=zone=>`var(--lotus-map-zone-${zones.includes(zone)?zone.toLowerCase():'a'})`
// A fixed interior label point on the largest component. It never depends on
// the current viewport, and avoids concave edges and holes.
export function zoneCenter(geometry){
 const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates
 const ringArea=ring=>Math.abs(ring.reduce((s,p,i)=>{const q=ring[(i+1)%ring.length];return s+p[0]*q[1]-q[0]*p[1]},0))/2
 const largest=polygons.reduce((a,b)=>ringArea(a[0])-a.slice(1).reduce((s,r)=>s+ringArea(r),0)>=ringArea(b[0])-b.slice(1).reduce((s,r)=>s+ringArea(r),0)?a:b)
 const [lng,lat]=polylabel(largest,.000005)
 return [lat,lng]
}

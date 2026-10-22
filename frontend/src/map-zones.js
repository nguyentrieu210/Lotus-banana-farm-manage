import polylabel from 'polylabel'
const zones=['A','B','C','D','E','F']
export const zoneColor=zone=>`var(--lotus-map-zone-${zones.includes(zone)?zone.toLowerCase():'a'})`
// Use the whole zone's area-weighted centre, including all its disconnected
// care lots. Roads split zones into many polygons: choosing the biggest single
// polygon would put a zone label in a corner care lot.
export function zoneCenter(geometry){
 const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates
 const origin=polygons[0][0][0]
 let total=0,x=0,y=0
 for(const polygon of polygons)for(const [index,ring] of polygon.entries()){
  let twice=0,cx=0,cy=0
  for(let i=0;i<ring.length;i++){
   const a=[ring[i][0]-origin[0],ring[i][1]-origin[1]],q=ring[(i+1)%ring.length],b=[q[0]-origin[0],q[1]-origin[1]],cross=a[0]*b[1]-b[0]*a[1]
   twice+=cross;cx+=(a[0]+b[0])*cross;cy+=(a[1]+b[1])*cross
  }
  if(!twice)continue
  const weight=Math.abs(twice)/2*(index===0?1:-1)
  total+=weight;x+=weight*(origin[0]+cx/(3*twice));y+=weight*(origin[1]+cy/(3*twice))
 }
 const centre=total?[x/total,y/total]:polylabel(polygons[0],.000005)
 const inside=(point,ring)=>{let yes=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes}return yes}
 const contains=point=>polygons.some(p=>inside(point,p[0])&&!p.slice(1).some(r=>inside(point,r)))
 // If the centre falls on a road or a concave cutout, choose the interior
 // candidate closest to the shared centre, regardless of a lot's size.
 const scale=Math.cos(centre[1]*Math.PI/180)
 const distance=p=>((p[0]-centre[0])*scale)**2+(p[1]-centre[1])**2
 const [lng,lat]=contains(centre)?centre:polygons.map(p=>polylabel(p,.000005)).reduce((a,b)=>distance(a)<=distance(b)?a:b)
 return [lat,lng]
}

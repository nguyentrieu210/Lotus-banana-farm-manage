// WGS84 coordinates; spherical measurements are estimates for field planning.
const R=6371008.8,rad=n=>n*Math.PI/180
export function distance(points){
 return points.slice(1).reduce((sum,b,i)=>{const a=points[i],lat=rad(b.lat-a.lat),lon=rad(b.lng-a.lng);const h=Math.sin(lat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(lon/2)**2;return sum+2*R*Math.asin(Math.min(1,Math.sqrt(h)))},0)
}
export function area(points){
 if(points.length<3)return 0
 return Math.abs(points.reduce((sum,a,i)=>{const b=points[(i+1)%points.length];return sum+rad(b.lng-a.lng)*(2+Math.sin(rad(a.lat))+Math.sin(rad(b.lat)))},0))*R*R/2
}
export function crosses(points){
 const side=(a,b,c)=>(b.lng-a.lng)*(c.lat-a.lat)-(b.lat-a.lat)*(c.lng-a.lng)
 const within=(a,b,c)=>c.lng>=Math.min(a.lng,b.lng)&&c.lng<=Math.max(a.lng,b.lng)&&c.lat>=Math.min(a.lat,b.lat)&&c.lat<=Math.max(a.lat,b.lat)
 const n=points.length
 for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
  if(j===i+1||(i===0&&j===n-1))continue
  const a=points[i],b=points[(i+1)%n],c=points[j],d=points[(j+1)%n],s=[side(a,b,c),side(a,b,d),side(c,d,a),side(c,d,b)]
  if((s[0]*s[1]<0&&s[2]*s[3]<0)||(!s[0]&&within(a,b,c))||(!s[1]&&within(a,b,d))||(!s[2]&&within(c,d,a))||(!s[3]&&within(c,d,b)))return true
 }
 return false
}
const n=v=>v.toLocaleString('vi-VN',{maximumFractionDigits:1})
export const measureLabel=(kind,points)=>kind==='area'?`${n(area(points))} m² · ${n(area(points)/10000)} ha`:`${n(distance(points))} m`
export function feature(kind,points){
 const coordinates=points.map(p=>[p.lng,p.lat])
 return {type:'Feature',properties:{kind,distance_m:distance(points),...(kind==='area'?{area_m2:area(points)}:{})},geometry:kind==='area'?{type:'Polygon',coordinates:[[...coordinates,coordinates[0]]]}:{type:'LineString',coordinates}}
}

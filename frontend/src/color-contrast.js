// WCAG 2.x contrast ratio, for the showcase's live token table (spec 004, User Story 6, scenario 3).
// Accepts '#rgb', '#rrggbb' and 'rgb(r g b)' / 'rgb(r, g, b)'. Returns null for anything else.
export function parseColour(text){
 const t=String(text||'').trim().toLowerCase()
 let m=/^#([0-9a-f]{3}|[0-9a-f]{6})$/.exec(t)
 if(m){const h=m[1].length===3?[...m[1]].map(c=>c+c).join(''):m[1];return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255)}
 m=/^rgba?\(([^)]+)\)$/.exec(t)
 if(m){const p=m[1].split(/[\s,/]+/).filter(Boolean).slice(0,3).map(Number);return p.length===3&&p.every(Number.isFinite)?p.map(v=>v/255):null}
 return null
}
const lin=c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4
const lum=([r,g,b])=>0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b)
export function contrastRatio(a,b){
 const x=parseColour(a),y=parseColour(b)
 if(!x||!y)return null
 const [hi,lo]=[lum(x),lum(y)].sort((p,q)=>q-p)
 return (hi+0.05)/(lo+0.05)
}

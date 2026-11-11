// Reads a token stylesheet and resolves custom properties per display mode.
// Used by the token tests (contrast, completeness). Pure functions, no DOM.
import {readFileSync} from 'node:fs'

const stripComments=css=>css.replace(/\/\*[\s\S]*?\*\//g,'')

// Flat list of style rules: [{at:['@media …'], selector:':root.dark', decls:Map}], in source order.
export function parseRules(cssText){
 const css=stripComments(cssText),rules=[],stack=[]
 let buffer=''
 const declarations=text=>{
  const decls=new Map()
  for(const part of splitTop(text,';')){
   const colon=part.indexOf(':')
   if(colon<1)continue
   const name=part.slice(0,colon).trim(),value=part.slice(colon+1).trim()
   if(name&&value)decls.set(name,value)
  }
  return decls
 }
 for(const ch of css){
  if(ch==='{'){stack.push({prelude:buffer.trim(),body:''});buffer='';continue}
  if(ch==='}'){
   const frame=stack.pop()
   if(!frame)continue
   frame.body+=buffer;buffer=''
   if(!frame.prelude.startsWith('@')){
    const at=stack.filter(f=>f.prelude.startsWith('@')).map(f=>f.prelude)
    for(const selector of splitTop(frame.prelude,',').map(s=>s.trim()).filter(Boolean))rules.push({at,selector,decls:declarations(frame.body)})
   }
   continue
  }
  buffer+=ch
 }
 return rules
}

// Split on a separator that is not inside parentheses.
function splitTop(text,separator){
 const parts=[];let depth=0,current=''
 for(const ch of text){
  if(ch==='(')depth++
  else if(ch===')')depth=Math.max(0,depth-1)
  if(ch===separator&&depth===0){parts.push(current);current=''}else current+=ch
 }
 parts.push(current)
 return parts
}

export const loadRules=file=>parseRules(readFileSync(file,'utf8'))

// Merge the declarations of the given selectors, in the order given (later wins). Rules inside at-rules are skipped
// unless includeAt returns true for the at-rule list.
export function modeMap(rules,selectors,includeAt=at=>at.length===0){
 const map=new Map()
 for(const selector of selectors)for(const rule of rules)if(rule.selector===selector&&includeAt(rule.at))for(const [k,v] of rule.decls)map.set(k,v)
 return map
}

// Replace var(--x) / var(--x, fallback) recursively. Unknown variables without a fallback stay as written.
export function resolveValue(map,value,depth=0){
 if(depth>24||typeof value!=='string'||!value.includes('var('))return value
 let out='',i=0
 while(i<value.length){
  const start=value.indexOf('var(',i)
  if(start<0){out+=value.slice(i);break}
  out+=value.slice(i,start)
  let level=0,end=start+3
  for(;end<value.length;end++){if(value[end]==='(')level++;else if(value[end]===')'){level--;if(level===0)break}}
  const inner=value.slice(start+4,end),[name,...rest]=splitTop(inner,','),fallback=rest.join(',').trim()
  const found=map.get(name.trim())
  out+=found!==undefined?resolveValue(map,found,depth+1):fallback?resolveValue(map,fallback,depth+1):value.slice(start,end+1)
  i=end+1
 }
 return out
}
export const resolveToken=(map,name)=>resolveValue(map,'var('+name+')')

// '#rgb' | '#rrggbb' | '#rrggbbaa' | rgb()/rgba() | white | black | transparent → [r,g,b,a] with channels 0..1, or null.
export function toRgba(input){
 const text=String(input||'').trim().toLowerCase()
 if(text==='white')return [1,1,1,1]
 if(text==='black')return [0,0,0,1]
 if(text==='transparent')return [0,0,0,0]
 let m=text.match(/^#([0-9a-f]{3,8})$/)
 if(m){
  let h=m[1]
  if(h.length===3||h.length===4)h=[...h].map(c=>c+c).join('')
  if(h.length!==6&&h.length!==8)return null
  const n=i=>parseInt(h.slice(i,i+2),16)/255
  return [n(0),n(2),n(4),h.length===8?n(6):1]
 }
 m=text.match(/^rgba?\(([^)]+)\)$/)
 if(m){
  const parts=m[1].replace(/\//g,' ').split(/[\s,]+/).filter(Boolean)
  if(parts.length<3)return null
  const channel=p=>p.endsWith('%')?parseFloat(p)/100:parseFloat(p)/255
  const alpha=parts[3]===undefined?1:parts[3].endsWith('%')?parseFloat(parts[3])/100:parseFloat(parts[3])
  const rgb=parts.slice(0,3).map(channel)
  return rgb.some(Number.isNaN)||Number.isNaN(alpha)?null:[...rgb,alpha]
 }
 return null
}

const linear=c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4
export const luminance=([r,g,b])=>0.2126*linear(r)+0.7152*linear(g)+0.0722*linear(b)
// Paint a translucent colour over an opaque one.
export const over=(top,bottom)=>[0,1,2].map(i=>top[i]*top[3]+bottom[i]*(1-top[3])).concat(1)

// WCAG 2.x contrast ratio of a foreground on an opaque background (a translucent foreground is composited first).
export function contrast(foreground,background){
 const bg=toRgba(background),fgRaw=toRgba(foreground)
 if(!bg||!fgRaw)return null
 const fg=fgRaw[3]<1?over(fgRaw,bg):fgRaw
 const [hi,lo]=[luminance(fg),luminance(bg)].sort((a,b)=>b-a)
 return (hi+0.05)/(lo+0.05)
}

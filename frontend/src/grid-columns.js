import {statusMeta,dueState} from './ui-status.js'
import {ICON_PATHS} from './icon-paths.js'
import {ribbonBackground,ribbonLabel} from './ribbon-colors.js'
import {formatNumber,formatDelta,initials} from './agri-format.js'
import {isoDateText} from './grid-format.js'

// Typed columns for DataTable (spec 004, FR-014), so screens stop writing their own formatters.
// Each builder returns a plain AG Grid colDef; extra options go through `rest` (sum, minWidth, pinned, hideOnMobile…).
// Cells drawn as DOM use the lotus-kit.css classes of the Vue components: a chip in a table is the same chip as anywhere
// else. valueFormatter always returns the plain text, so header filters, phone cards, the sum row and Excel stay text.

const SVG_NS='http://www.w3.org/2000/svg'
const blank=v=>v===null||v===undefined||v===''
export function iconNode(name){
 const svg=document.createElementNS(SVG_NS,'svg')
 for(const [k,v] of Object.entries({class:'lotus-icon',viewBox:'0 0 24 24',width:'20',height:'20',fill:'none',stroke:'currentColor','stroke-width':'1.7','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false'}))svg.setAttribute(k,v)
 for(const d of ICON_PATHS[name]||[]){const path=document.createElementNS(SVG_NS,'path');path.setAttribute('d',d);svg.appendChild(path)}
 return svg
}
function node(tag,className,text){const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined&&text!==null)el.textContent=text;return el}

// {kind,label,tone,icon} → <span class="lotus-chip …">
export function chipNode(meta,{size='sm'}={}){
 const chip=node('span','lotus-chip lotus-chip--'+(meta.tone||'neutral')+(size==='sm'?' lotus-chip--sm':'')+(meta.icon?'':' lotus-chip--bare'))
 if(meta.kind)chip.dataset.kind=meta.kind
 if(meta.icon)chip.appendChild(iconNode(meta.icon))
 chip.appendChild(node('span','lotus-chip__text',meta.label))
 return chip
}

const numberText=(value,digits,unit)=>{const text=formatNumber(value,{digits});return text===null?'':text+(unit?' '+unit:'')}

// Numbers: right-aligned, tabular, grouped the Vietnamese way. unit is appended in the cell and in exports.
export const numberCol=(field,headerName,{digits=0,unit='',...rest}={})=>({field,headerName,type:'numericColumn',cellClass:'lotus-grid-number',valueFormatter:p=>numberText(p.value,digits,unit),...rest})
export const moneyCol=(field,headerName,rest={})=>numberCol(field,headerName,{digits:0,unit:'đ',...rest})
// Quantity with its unit taken from another field of the row (kg, bao, lít). unitField also tells the sum row
// not to add different units together (grid-totals.js).
export const qtyCol=(field,headerName,{unitField,digits=3,...rest}={})=>({field,headerName,type:'numericColumn',cellClass:'lotus-grid-number',...(unitField?{unitField}:{}),valueFormatter:p=>numberText(p.value,digits,unitField?p.data?.[unitField]:''),...rest})
export const percentCol=(field,headerName,{digits=1,...rest}={})=>({field,headerName,type:'numericColumn',cellClass:'lotus-grid-number',sum:false,valueFormatter:p=>blank(p.value)?'':formatNumber(p.value,{digits})+'%',...rest})
export const dateCol=(field,headerName,rest={})=>({field,headerName,sum:false,minWidth:112,valueFormatter:p=>blank(p.value)?'':isoDateText(p.value)||String(p.value),...rest})

// A due date with its state next to it: "14/11 · Quá 3 ngày" (FR-014, FR-033). today is 'YYYY-MM-DD'.
export const dueCol=(field,headerName,{today,soon=2,...rest}={})=>({field,headerName,sum:false,minWidth:196,
 valueFormatter:p=>blank(p.value)?'':isoDateText(p.value)||String(p.value),
 cellRenderer:p=>{
  if(blank(p.value))return ''
  const wrap=node('span','lotus-grid-due'),state=dueState(p.value,today,{soon})
  wrap.appendChild(node('span','lotus-num',isoDateText(p.value)||String(p.value)))
  if(state&&state.kind!=='upcoming')wrap.appendChild(chipNode(state))
  return wrap
 },...rest})

// Document or work state as a chip (FR-005). labelOf(value,row) supplies the caption (e.g. stateLabel).
export const statusCol=(field,headerName,{labelOf,...rest}={})=>({field,headerName,sum:false,minWidth:120,
 valueFormatter:p=>blank(p.value)?'':statusMeta(p.value,labelOf?.(p.value,p.data)).label,
 cellRenderer:p=>blank(p.value)?'':chipNode(statusMeta(p.value,labelOf?.(p.value,p.data))),...rest})

// Done of total as a thin bar and a percentage. maxField reads the total from the row; max is a fixed total.
export const progressCol=(field,headerName,{max=100,maxField,tone='primary',...rest}={})=>{
 const share=p=>{const total=Number(maxField?p.data?.[maxField]:max);return blank(p.value)||!(total>0)?null:Math.max(0,Math.min(100,Number(p.value)/total*100))}
 return {field,headerName,sum:false,minWidth:130,
  valueFormatter:p=>{const s=share(p);return s===null?'':Math.round(s)+'%'},
  cellRenderer:p=>{
   const s=share(p)
   if(s===null)return ''
   const bar=node('div','lotus-progress lotus-progress--inline lotus-progress--'+tone)
   bar.setAttribute('role','progressbar');bar.setAttribute('aria-valuenow',String(Math.round(s)));bar.setAttribute('aria-valuemin','0');bar.setAttribute('aria-valuemax','100')
   const track=node('div','lotus-progress__track'),fill=node('div','lotus-progress__bar')
   fill.style.width=s+'%';track.appendChild(fill);bar.appendChild(track)
   const meta=node('div','lotus-progress__meta');meta.appendChild(node('strong',null,Math.round(s)+'%'));bar.appendChild(meta)
   return bar
  },...rest}
}

// Ribbon batch: swatch + name (+ ISO week). The value is the ribbon code (DO, XANH_LA_DO…).
export const ribbonCol=(field,headerName,{labelField,weekField,...rest}={})=>({field,headerName,sum:false,minWidth:160,
 valueFormatter:p=>blank(p.value)?'':(labelField&&p.data?.[labelField])||ribbonLabel(p.value)||String(p.value),
 cellRenderer:p=>{
  if(blank(p.value))return ''
  const wrap=node('span','lotus-grid-ribbon'),dot=node('span','lotus-ribbon')
  dot.style.setProperty('--ribbon',ribbonBackground(p.value));dot.setAttribute('aria-hidden','true')
  wrap.appendChild(dot);wrap.appendChild(node('span',null,(labelField&&p.data?.[labelField])||ribbonLabel(p.value)||String(p.value)))
  if(weekField&&!blank(p.data?.[weekField]))wrap.appendChild(node('span','lotus-ribbon-chip__week','T'+p.data[weekField]))
  return wrap
 },...rest})

// A person: initials, name and (optionally) the team under it.
export const personCol=(field,headerName,{teamField,...rest}={})=>({field,headerName,sum:false,minWidth:150,
 valueFormatter:p=>blank(p.value)?'':String(p.value),
 cellRenderer:p=>{
  if(blank(p.value))return ''
  const wrap=node('span','lotus-crew'),name=String(p.value)
  let hue=0;for(const ch of name)hue=(hue*31+ch.codePointAt(0))>>>0
  const avatar=node('span','lotus-avatar lotus-avatar--sm',initials(name));avatar.dataset.hue=String(hue%6);avatar.setAttribute('aria-hidden','true')
  const text=node('span','lotus-crew__text');text.appendChild(node('span','lotus-crew__name',name))
  if(teamField&&!blank(p.data?.[teamField]))text.appendChild(node('span','lotus-crew__team',String(p.data[teamField])))
  wrap.appendChild(avatar);wrap.appendChild(text)
  return wrap
 },...rest})

// Signed change with an arrow, good or bad by direction (goodWhen 'up' | 'down').
export const deltaCol=(field,headerName,{digits=0,unit='',goodWhen='up',...rest}={})=>({field,headerName,type:'numericColumn',cellClass:'lotus-grid-number',
 valueFormatter:p=>blank(p.value)?'':formatDelta(p.value,{digits})+(unit?' '+unit:''),
 cellRenderer:p=>{
  if(blank(p.value))return ''
  const n=Number(p.value),dir=n>0?'up':n<0?'down':'flat'
  const wrap=node('span','lotus-stat__delta lotus-stat__delta--'+(dir==='flat'?'flat':dir===goodWhen?'good':'bad'))
  if(dir!=='flat')wrap.appendChild(iconNode(dir==='up'?'arrow-up':'arrow-down'))
  wrap.appendChild(node('span',null,formatDelta(n,{digits})+(unit?' '+unit:'')))
  return wrap
 },...rest})

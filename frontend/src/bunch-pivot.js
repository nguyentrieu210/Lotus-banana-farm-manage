// Pivots the bunch report on the screen, from the flat rows the server sends: one row per week, khu, lô, tổ, colour, lần and công đoạn.
export const DIMENSIONS=[{id:'z',label:'Khu',filter:'zone'},{id:'w',label:'Tuần',filter:'week'},{id:'m',label:'Tháng',filter:'month'},{id:'c',label:'Màu dây',filter:'colour'},{id:'t',label:'Tổ',filter:'team'},{id:'b',label:'Lô',filter:'block'},{id:'r',label:'Lý do',filter:''}]
export const dimensionById=id=>DIMENSIONS.find(d=>d.id===id)
export const stageOf=id=>STAGES.find(s=>s.id===id)
export const SPLITS=[{id:'',label:'Không'},{id:'z',label:'Khu'},{id:'t',label:'Tổ'},{id:'l',label:'Lần cắt'}]
export const STAGES=[{id:'inject',label:'Chích bắp',unit:'buồng'},{id:'prop',label:'Chống đổ',unit:'cây'},{id:'care',label:'Tỉa, vệ sinh',unit:'buồng'},{id:'cut',label:'Cắt bắp',unit:'buồng'},{id:'bag',label:'Bao buồng',unit:'buồng'},{id:'reject',label:'Hủy buồng',unit:'buồng'},{id:'left',label:'Tồn buồng',unit:'buồng'},{id:'harvest',label:'Thu hoạch',unit:'buồng'}]
// Before cắt bắp there is no ribbon yet; tồn is counted per colour and lô, not per tổ.
const NOT_APPLICABLE={c:['inject','prop','care'],t:['left'],m:[],w:[],z:[]}
export const notApplicable=(stage,dim)=>(NOT_APPLICABLE[dim]||[]).includes(stage)
// What a chart of this công đoạn can be cut by: no ribbon before cắt bắp, a reason only for hủy buồng.
export const dimensionsFor=stage=>DIMENSIONS.filter(d=>!notApplicable(stage,d.id)&&(d.id!=='r'||stage==='reject'))
const EMPTY='(Không có)'
const MAX_SPLIT=5,MAX_COLUMNS=15
export const OTHER='Khác'
// A chart of ribbon colours is drawn in those colours: a slice called Đỏ must not be green. White is a light grey so it shows on the page.
const RIBBONS=[['tím','#7a4fa3'],['đỏ','#c43224'],['trắng','#cfd3d8'],['cam','#e08a1e'],['đen','#2c3036'],['xanh dương','#2f5c9f'],['xanh lá','#21835b'],['vàng','#e3b52f'],['hồng','#d9659b'],['nâu','#7c5a3c']]
export function ribbonColour(name){const text=String(name||'').toLowerCase();return RIBBONS.map(([word,hex])=>[text.indexOf(word),hex]).filter(([at])=>at>=0).sort((a,b)=>a[0]-b[0])[0]?.[1]||null}

export function label(dim,value){
 if(!value)return EMPTY
 if(dim==='w')return 'T'+Number(value.split('-W')[1])
 if(dim==='m')return 'Tháng '+Number(value.slice(5,7))+'/'+value.slice(2,4)
 if(dim==='z')return 'Khu '+value
 return value
}
const ascending=(a,b)=>a<b?-1:a>b?1:0

// The columns every stage shares, so the charts line up. Weeks and months keep their calendar order; khu always shows all of its khu.
export function categories(rows,dim,baseline=[]){
 const found=new Set(baseline)
 for(const r of rows)if(r[dim])found.add(r[dim])
 const sorted=[...found].sort(ascending)
 if(dim==='m'&&sorted.length>1)return monthsBetween(sorted[0],sorted.at(-1))
 return sorted
}
function monthsBetween(first,last){
 const out=[];let [y,m]=first.split('-').map(Number)
 for(let key=first;key<=last;key=y+'-'+String(m).padStart(2,'0')){out.push(key);m++;if(m>12){m=1;y++}}
 return out
}
const add=(map,key,row)=>{const s=map.get(key)||{qty:0,kg:0};s.qty+=row.q;s.kg+=row.k;map.set(key,s);return map}

export function chart(rows,stage,dim,split,columns){
 const own=rows.filter(r=>r.s===stage)
 const index=new Map(columns.map((c,i)=>[c,i]))
 if(!split||split===dim){
  const data=columns.map(()=>0)
  for(const r of own)if(index.has(r[dim]))data[index.get(r[dim])]+=r.q
  return {series:[{name:STAGES.find(s=>s.id===stage).label,data}],stacked:false}
 }
 const totals=new Map()
 for(const r of own){const k=r[split]||'';totals.set(k,(totals.get(k)||0)+r.q)}
 const ranked=[...totals.entries()].sort((a,b)=>b[1]-a[1]||ascending(a[0],b[0])).map(e=>e[0])
 const kept=split==='z'?[...ranked].sort(ascending):ranked.slice(0,MAX_SPLIT)
 const keep=new Set(kept),hasOther=split!=='z'&&ranked.length>MAX_SPLIT
 const data=new Map(kept.map(k=>[k,columns.map(()=>0)]))
 if(hasOther)data.set(OTHER,columns.map(()=>0))
 for(const r of own){
  if(!index.has(r[dim]))continue
  const k=r[split]||''
  data.get(keep.has(k)?k:OTHER)[index.get(r[dim])]+=r.q
 }
 return {series:[...data.entries()].map(([k,values])=>({name:k===OTHER?OTHER:split==='l'?(k?'Lần '+k:EMPTY):label(split,k),data:values,other:k===OTHER})),stacked:true}
}
export function total(rows,stage){return rows.filter(r=>r.s===stage).reduce((n,r)=>n+r.q,0)}

// The lô behind one column of one stage.
export function lots(rows,stage,dim,value){
 const found=new Map()
 for(const r of rows)if(r.s===stage&&r[dim]===value)add(found,r.b,r)
 return [...found.entries()].map(([code,s])=>({code,qty:s.qty,kg:s.kg})).sort((a,b)=>a.code.length-b.code.length||ascending(a.code,b.code))
}

// Kg per bunch for each column of the harvest.
export function kgPerBunch(rows,dim,columns){
 const found=new Map()
 for(const r of rows)if(r.s==='harvest')add(found,r[dim],r)
 return columns.map(c=>{const s=found.get(c);return s&&s.qty?Math.round(s.kg/s.qty*100)/100:null})
}

// One row per column, one figure per stage: the pivot table at the foot of the page.
export function table(rows,dim,columns){
 const lines=new Map(columns.map(c=>[c,Object.fromEntries(STAGES.map(s=>[s.id,0]))]))
 for(const r of rows){const line=lines.get(r[dim]);if(line&&r.s in line)line[r.s]+=r.q}
 return columns.map(c=>({key:c,name:label(dim,c),...lines.get(c)}))
}

// One chart: its columns, in the order that suits what they are. Time keeps the calendar, khu its own order; the rest go largest first, the tail folded.
export function pivotChart(rows,{stage,dim,split='',metric='',baseline={},sorted=false}){
 const own=rows.filter(r=>r.s===stage)
 const timeLike=dim==='w'||dim==='m'
 let keys=categories(own,dim,baseline[dim]||[])
 const amount=new Map(keys.map(k=>[k,0]))
 for(const r of own)if(amount.has(r[dim]))amount.set(r[dim],amount.get(r[dim])+r.q)
 if(!timeLike&&(dim!=='z'||sorted))keys=[...keys].sort((a,b)=>amount.get(b)-amount.get(a)||ascending(a,b))
 if(sorted&&timeLike)keys=keys.filter(k=>amount.get(k))
 const limit=sorted?MAX_SPLIT:MAX_COLUMNS
 const folded=!timeLike&&dim!=='z'&&keys.length>limit
 const shown=folded?keys.slice(0,limit):keys
 if(metric==='kg_per')return {keys:shown,names:shown.map(k=>label(dim,k)),series:[{name:'Kg/buồng',data:kgPerBunch(rows,dim,shown)}],stacked:false}
 const source=folded?own.map(r=>shown.includes(r[dim])?r:{...r,[dim]:OTHER}):own
 const finalKeys=folded?[...shown,OTHER]:shown
 const c=chart(source,stage,dim,split,finalKeys)
 return {keys:finalKeys,names:finalKeys.map(k=>k===OTHER?OTHER:label(dim,k)),pointColors:dim==='c'&&!c.stacked?finalKeys.map(ribbonColour):null,...c}
}

// Lô down the side, weeks across. The busiest lô come first when there are too many to read.
export function heat(rows,stage,weeks,limit=MAX_COLUMNS){
 const lots=new Map()
 for(const r of rows){
  if(r.s!==stage||!weeks.includes(r.w))continue
  const line=lots.get(r.b)||weeks.map(()=>0)
  line[weeks.indexOf(r.w)]+=r.q
  lots.set(r.b,line)
 }
 const sum=a=>a.reduce((n,v)=>n+v,0)
 const chosen=[...lots.entries()].sort((a,b)=>sum(b[1])-sum(a[1])).slice(0,limit).sort((a,b)=>a[0].length-b[0].length||ascending(a[0],b[0]))
 return {columns:weeks.map(w=>({key:w,name:label('w',w)})),rows:chosen.map(([key,values])=>({key,values}))}
}

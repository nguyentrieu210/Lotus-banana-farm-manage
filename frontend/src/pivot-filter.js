// A filter that works like an Excel pivot. A field missing from the selection means everything is ticked; an empty list means nothing is.
export const isTicked=(selection,field,value)=>!selection[field]||selection[field].includes(value)
export const isFiltered=(selection,field)=>!!selection[field]
export const allTicked=(selection,field)=>!selection[field]

export function toggle(selection,field,value,options){
 const all=options.map(o=>o.value),current=selection[field]||all
 const next=current.includes(value)?current.filter(v=>v!==value):[...current,value]
 const result={...selection}
 if(all.every(v=>next.includes(v)))delete result[field]
 else result[field]=next
 return result
}
export function toggleAll(selection,field){
 const result={...selection}
 if(result[field])delete result[field]
 else result[field]=[]
 return result
}
export function buttonLabel(label,selection,field){
 return selection[field]?label+' ('+selection[field].length+')':label
}
// A click on a chart, as in Power BI: filter to that value, or lift the filter when it is the one already chosen.
export function crossFilter(selection,field,value){
 const result={...selection}
 if(result[field]?.length===1&&result[field][0]===value)delete result[field]
 else result[field]=[value]
 return result
}
export const matches=(option,text)=>!text||option.label.toLowerCase().includes(text.trim().toLowerCase())

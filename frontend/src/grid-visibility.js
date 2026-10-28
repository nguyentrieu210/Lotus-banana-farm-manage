// Display-only preferences per table and browser. Never affect source data or server permissions.
const legacyPrefix='lotus-grid-hidden:'
const layoutPrefix='lotus-grid-layout:'
export const columnId=column=>column.colId||column.field||column.headerName
const editable=c=>!c.hide&&!c.lockVisible&&!c.columnChooserLocked
export const selectableColumns=columns=>columns.filter(editable)
const unique=v=>[...new Set(Array.isArray(v)?v.filter(x=>typeof x==='string'):[])]
export function normalizeHiddenColumns(columns,hidden){
 const ids=selectableColumns(columns).map(columnId)
 const chosen=unique(hidden).filter(v=>ids.includes(v))
 if(ids.length&&chosen.length===ids.length)return chosen.filter(v=>v!==ids[0])
 return chosen
}
export function changeColumnVisibility(columns,hidden,id){
 const current=normalizeHiddenColumns(columns,hidden)
 if(!selectableColumns(columns).some(c=>columnId(c)===id))return current
 return normalizeHiddenColumns(columns,current.includes(id)?current.filter(c=>c!==id):[...current,id])
}
export function loadHiddenColumns(key){
 if(!key)return []
 try{const v=JSON.parse(localStorage.getItem(legacyPrefix+key)||'[]');return unique(v)}catch{return []}
}
export function saveHiddenColumns(key,hidden){
 if(!key)return
 try{localStorage.setItem(legacyPrefix+key,JSON.stringify(unique(hidden)))}catch{}
}
export function normalizeColumnLayout(columns,layout={}){
 const ids=selectableColumns(columns).map(columnId)
 const hidden=normalizeHiddenColumns(columns,layout.hidden)
 const order=[...unique(layout.order).filter(id=>ids.includes(id)),...ids.filter(id=>!unique(layout.order).includes(id))]
 // Keep only visible and selectable columns pinned; prevent a huge pinned section.
 const pinned=unique(layout.pinned).filter(id=>ids.includes(id)&&!hidden.includes(id)).slice(0,2)
 return {hidden,order,pinned}
}
export function loadColumnLayout(key,columns){
 let saved={}
 if(key){try{saved=JSON.parse(localStorage.getItem(layoutPrefix+key)||'{}')||{}}catch{}}
 if(!Array.isArray(saved.hidden))saved.hidden=loadHiddenColumns(key)
 return normalizeColumnLayout(columns,saved)
}
export function saveColumnLayout(key,columns,layout){
 const next=normalizeColumnLayout(columns,layout)
 if(key){try{localStorage.setItem(layoutPrefix+key,JSON.stringify(next))}catch{}}
 saveHiddenColumns(key,next.hidden)
 return next
}
export function orderedColumns(columns,layout){
 const ordered=normalizeColumnLayout(columns,layout).order
 const picker=new Map(selectableColumns(columns).map(col=>[columnId(col),col]))
 const available=ordered.map(id=>picker.get(id)).filter(Boolean)
 let i=0
 return columns.map(col=>editable(col)?available[i++]:col)
}
export function displayedColumns(columns,layout){
 const normalized=normalizeColumnLayout(columns,layout)
 const shown=orderedColumns(columns,normalized).filter(col=>!col.hide&&!normalized.hidden.includes(columnId(col)))
 return [...shown.filter(col=>normalized.pinned.includes(columnId(col))),...shown.filter(col=>!normalized.pinned.includes(columnId(col)))]
}
export function moveColumn(columns,layout,id,direction){
 const next=normalizeColumnLayout(columns,layout)
 const pos=next.order.indexOf(id),to=pos+direction
 if(pos<0||to<0||to>=next.order.length)return next
 const order=next.order.slice()
 ;[order[pos],order[to]]=[order[to],order[pos]]
 return {...next,order}
}
export function pinColumn(columns,layout,id){
 const next=normalizeColumnLayout(columns,layout)
 if(!next.order.includes(id)||next.hidden.includes(id))return next
 const pinned=next.pinned.includes(id)?next.pinned.filter(x=>x!==id):[...next.pinned,id]
 return normalizeColumnLayout(columns,{...next,pinned})
}
export function setVisibleColumns(columns,layout,visible){
 const ids=selectableColumns(columns).map(columnId)
 const visibleIds=new Set(visible)
 return normalizeColumnLayout(columns,{...layout,hidden:ids.filter(id=>!visibleIds.has(id))})
}

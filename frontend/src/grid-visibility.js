// Column visibility is a display preference only; the server filters and permissions are unchanged.
const prefix='lotus-grid-hidden:'
export const columnId=column=>column.colId||column.field||column.headerName
const editable=column=>!column.hide&&!column.lockVisible&&!column.columnChooserLocked
export const selectableColumns=columns=>columns.filter(editable)
export function normalizeHiddenColumns(columns,hidden){
 const ids=selectableColumns(columns).map(columnId)
 const chosen=[...new Set(Array.isArray(hidden)?hidden.filter(v=>typeof v==='string'&&ids.includes(v)):[])]
 // Never hide all display columns; keep the first visible.
 if(ids.length&&chosen.length===ids.length) return chosen.filter(v=>v!==ids[0])
 return chosen
}
export function changeColumnVisibility(columns,hidden,id){
 const current=normalizeHiddenColumns(columns,hidden)
 if(!selectableColumns(columns).some(c=>columnId(c)===id))return current
 return normalizeHiddenColumns(columns,current.includes(id)?current.filter(c=>c!==id):[...current,id])
}
export function loadHiddenColumns(key){
 if(!key)return []
 try{
  const raw=JSON.parse(localStorage.getItem(prefix+key)||'[]')
  return Array.isArray(raw)?raw.filter(v=>typeof v==='string'):[]
 }catch{return []}
}
export function saveHiddenColumns(key,hidden){
 if(!key)return
 try{localStorage.setItem(prefix+key,JSON.stringify(hidden))}catch{/* Storage disabled: table still works. */}
}

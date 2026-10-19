// Remembered AG Grid column widths, per table. Only widths: restoring sort would re-trigger server-side loads.
const prefix='lotus-grid-widths:'
export function loadColumnWidths(key){
 try{const saved=JSON.parse(localStorage.getItem(prefix+key)||'[]');return Array.isArray(saved)?saved.filter(c=>c&&c.colId&&Number(c.width)>0).map(c=>({colId:c.colId,width:Number(c.width),flex:null})):[]}catch{return []}
}
export function saveColumnWidths(key,state){
 try{localStorage.setItem(prefix+key,JSON.stringify((state||[]).filter(c=>c.colId&&c.width).map(c=>({colId:c.colId,width:Math.round(c.width)}))))}catch{}
}

// Named table views (column filters + sort), per table and per browser.
const viewPrefix='lotus-grid-views:'
export function loadViews(key){try{const views=JSON.parse(localStorage.getItem(viewPrefix+key)||'[]');return Array.isArray(views)?views.filter(v=>v&&v.name):[]}catch{return []}}
export function saveView(key,view){
 const views=loadViews(key).filter(v=>v.name!==view.name)
 views.push({name:view.name,filters:view.filters||{},sort:view.sort||[]})
 try{localStorage.setItem(viewPrefix+key,JSON.stringify(views.slice(-12)))}catch{}
 return loadViews(key)
}
export function deleteView(key,name){const views=loadViews(key).filter(v=>v.name!==name);try{localStorage.setItem(viewPrefix+key,JSON.stringify(views))}catch{};return views}

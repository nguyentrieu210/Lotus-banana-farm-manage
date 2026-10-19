// Remembered AG Grid column widths, per table. Only widths: restoring sort would re-trigger server-side loads.
const prefix='lotus-grid-widths:'
export function loadColumnWidths(key){
 try{const saved=JSON.parse(localStorage.getItem(prefix+key)||'[]');return Array.isArray(saved)?saved.filter(c=>c&&c.colId&&Number(c.width)>0).map(c=>({colId:c.colId,width:Number(c.width),flex:null})):[]}catch{return []}
}
export function saveColumnWidths(key,state){
 try{localStorage.setItem(prefix+key,JSON.stringify((state||[]).filter(c=>c.colId&&c.width).map(c=>({colId:c.colId,width:Math.round(c.width)}))))}catch{}
}

// Resolve grid actions and updates by business identity, never by visual row index.
// Shared by sorted/filtered views: the same document keeps its ID across reloads.
const anonymous=new WeakMap()
let nextAnonymous=0
export function gridRowId(row,field){
 if(!row||typeof row!=='object')return String(row??'')
 if(field&&row[field]!=null&&row[field]!=='')return String(row[field])
 for(const key of ['name','id','row_key','employee','task_id','block_code','work_code','source_ref']){
  if(row[key]!=null&&row[key]!=='')return String(row[key])
 }
 if(!anonymous.has(row))anonymous.set(row,'anonymous-'+(++nextAnonymous))
 return anonymous.get(row)
}

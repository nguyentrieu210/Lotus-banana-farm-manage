const DB='lotus-vue-field-v1',STORE='queue'
const syncing=new Map()
function openDB(){return new Promise((resolve,reject)=>{const request=indexedDB.open(DB,1);request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains(STORE))request.result.createObjectStore(STORE,{keyPath:'key'})};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)})}
async function tx(mode,action){
  const db=await openDB()
  return new Promise((resolve,reject)=>{
    const t=db.transaction(STORE,mode)
    let result
    t.oncomplete=()=>{db.close();resolve(result)}
    t.onabort=()=>{db.close();reject(t.error||new Error('Không lưu được hàng chờ trên máy.'))}
    try{const req=action(t.objectStore(STORE));req.onsuccess=()=>{result=req.result}}
    catch(error){t.abort();reject(error)}
  })
}
export async function queueCapture(user,event,photo=null){
  if(!user||user==='Guest'||!event.client_event_id)throw new Error('Cần tài khoản và mã bản ghi hiện trường.')
  const entry={key:user+'|'+event.client_event_id,user,event,status:'Pending',error:'',result:null,photo,created:new Date().toISOString()}
  // Insert once: retries must never overwrite a received or edited event.
  await tx('readwrite',s=>s.add(entry))
  return entry
}
export async function queueRows(user){const rows=await tx('readonly',s=>s.getAll());return rows.filter(r=>r.user===user).sort((a,b)=>a.created.localeCompare(b.created))}
export async function pendingCount(user){return (await queueRows(user)).filter(r=>!['Sent','Discarded'].includes(r.status)).length}
export function syncCaptures(user,api){
  if(syncing.has(user))return syncing.get(user)
  const job=sendCaptures(user,api).finally(()=>syncing.delete(user))
  syncing.set(user,job)
  return job
}
async function sendCaptures(user,{call,upload}){
  const rows=(await queueRows(user)).filter(r=>!['Sent','Discarded'].includes(r.status)),results=[]
  for(const entry of rows){
    entry.status='Syncing';await tx('readwrite',s=>s.put(entry))
    try{
      const session=await call('lotus_farm.field.session_info')
      if(session.user!==user)throw new Error('Tài khoản đã thay đổi; hàng chờ vẫn được giữ cho người nhập.')
      if(entry.photo&&!entry.event.photo){
        const up=await upload(entry.photo)
        entry.event.photo=up.file_url
        await tx('readwrite',s=>s.put(entry))
      }
      entry.result=await call('lotus_farm.field.capture',entry.event,true)
      entry.status='Sent';entry.error='';entry.photo=null
    }catch(e){entry.status='Error';entry.error=e.message||String(e)}
    await tx('readwrite',s=>s.put(entry));results.push(entry)
    if(entry.error.includes('Tài khoản đã thay đổi'))break
  }
  return results
}
export async function reconcileCapture(user,key,{call},discardReason=''){const entry=await tx('readonly',s=>s.get(key));if(!entry||entry.user!==user)throw new Error('Bản ghi không thuộc tài khoản hiện tại.');const status=await call('lotus_farm.field.capture_status',{client_event_id:entry.event.client_event_id});if(status.received){entry.status='Sent';entry.result=status;entry.error='';entry.photo=null}else{if(!discardReason.trim())return {entry,received:false};entry.status='Discarded';entry.discard_reason=discardReason.trim()}await tx('readwrite',s=>s.put(entry));return {entry,received:!!status.received}}
export async function clearSent(user){for(const row of await queueRows(user))if(row.status==='Sent')await tx('readwrite',s=>s.delete(row.key))}

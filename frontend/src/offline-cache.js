const DB='lotus-vue-read-cache-v1',STORE='reads',MAX_AGE=24*60*60*1000
let active=''
try{active=localStorage.getItem('lotus-vue-active-user')||''}catch{}
const allowed=new Set(['lotus_farm.console.bootstrap','lotus_farm.console.schema','lotus_farm.console.scope_options','lotus_farm.console.link_options','lotus_farm.console.listing','lotus_farm.daily_api.daily_overview','lotus_farm.field.bootstrap','lotus_farm.field.available_labor'])
export const cachedMethod=method=>allowed.has(method)
export function activeUser(){return active}
export function setActiveUser(user){active=user==='Guest'?'':user;try{if(active)localStorage.setItem('lotus-vue-active-user',active);else localStorage.removeItem('lotus-vue-active-user')}catch{}}
const key=(user,method,args)=>JSON.stringify([user,method,Object.entries(args).filter(([,v])=>v!==undefined&&v!==null&&v!=='').sort(([a],[b])=>a.localeCompare(b))])
async function request(mode,fn){const db=await new Promise((resolve,reject)=>{const req=indexedDB.open(DB,1);req.onupgradeneeded=()=>req.result.createObjectStore(STORE,{keyPath:'key'});req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)});return new Promise((resolve,reject)=>{const tx=db.transaction(STORE,mode);let value;tx.oncomplete=()=>{db.close();resolve(value)};tx.onabort=()=>{db.close();reject(tx.error)};try{const req=fn(tx.objectStore(STORE));req.onsuccess=()=>value=req.result}catch(e){tx.abort();reject(e)}})}
export async function saveRead(user,method,args,value){if(!user||!cachedMethod(method))return;let data=value;if(method==='lotus_farm.console.bootstrap'){data={...value};delete data.csrf_token}await request('readwrite',s=>s.put({key:key(user,method,args),user,created:Date.now(),value:data}))}
export async function cachedRead(user,method,args){if(!user||!cachedMethod(method))return null;const row=await request('readonly',s=>s.get(key(user,method,args)));if(!row||Date.now()-row.created>MAX_AGE)return null;return row.value}

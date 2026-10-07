const attempts=new Map()
const user=()=>{try{return localStorage.getItem('lotus-vue-active-user')||''}catch{return ''}}
const storageKey=key=>'lotus-command-attempt|'+key
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v
export function retryAttempt(method,args){const payload={...args};delete payload.client_event_id;const key=user()+'|'+method+'|'+JSON.stringify(canonical(payload));if(!attempts.has(key)){let saved;try{saved=sessionStorage.getItem(storageKey(key))}catch{}attempts.set(key,saved||crypto.randomUUID());try{sessionStorage.setItem(storageKey(key),attempts.get(key))}catch{}}return {key,args:{...args,client_event_id:attempts.get(key)}}}
export function acceptAttempt(key){attempts.delete(key);try{sessionStorage.removeItem(storageKey(key))}catch{}}

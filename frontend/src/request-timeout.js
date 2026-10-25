// Bound both header and response-body waits. A timed-out write is ambiguous and
// is never retried automatically; callers keep the original command identity.
export async function requestJSON(url,options={},timeoutMs=30000){
 const controller=new AbortController()
 let timer
 try{return await Promise.race([
  (async()=>{const response=await fetch(url,{...options,signal:controller.signal});return {response,data:await response.json()}})(),
  new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();const e=new Error('Máy chủ phản hồi quá lâu.');e.code='RequestTimeout';reject(e)},timeoutMs)})
 ])}finally{clearTimeout(timer)}
}

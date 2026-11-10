// Uniform deep links for every Lotus phone app (spec 003, FR-004).
// The server only sends doctype + name; each app registers how it opens a document, and the parameters
// are removed from the address bar once read so a reload does not reopen the same sheet.
//   ?sign_dt=&sign_dn=      signing sheet of one document (alerts, Chờ tôi ký)
//   ?doctype=&doc=          detail of one document
//   ?doc=  (no doctype)     older Mua hàng links: a purchase order
//   ?proposal=              older Mua hàng links: a purchase proposal
//   ?request=, ?tab=        older entry points kept for bookmarks
export const DEEP_LINK_KEYS=['sign_dt','sign_dn','doctype','doc','proposal','request','tab']

export function readDeepLink(search=''){
 const q=new URLSearchParams(search)
 const value=key=>String(q.get(key)||'').trim()
 if(value('sign_dt')&&value('sign_dn'))return {kind:'sign',doctype:value('sign_dt'),name:value('sign_dn')}
 if(value('doc'))return {kind:'open',doctype:value('doctype'),name:value('doc')}
 if(value('proposal'))return {kind:'open',doctype:'Material Request',name:value('proposal')}
 if(value('request'))return {kind:'request',name:value('request')}
 if(value('tab'))return {kind:'tab',name:value('tab')}
 return null
}

export function clearDeepLink({history=globalThis.history,location=globalThis.location}={}){
 if(!history||!location)return false
 const url=new URL(location.href)
 const found=DEEP_LINK_KEYS.filter(key=>url.searchParams.has(key))
 if(!found.length)return false
 for(const key of found)url.searchParams.delete(key)
 history.replaceState(history.state,'',url.pathname+url.search+url.hash)
 return true
}

// openers: {sign(link), open(link), [doctype](link), request(link), tab(link)}; a doctype-specific opener wins
// over the generic `open`. Returns the link that was handled, or null.
export async function openDeepLink(openers={},{location=globalThis.location,history=globalThis.history}={}){
 const link=readDeepLink(location?.search||'')
 if(!link)return null
 clearDeepLink({history,location})
 const handler=link.kind==='open'?(openers[link.doctype]||openers.open):openers[link.kind]
 if(typeof handler!=='function')return null
 await handler(link)
 return link
}

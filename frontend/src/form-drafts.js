// Local drafts of new documents (per doctype, per browser). Only unsaved new records are kept; they expire after 7 days.
const prefix='lotus-draft:',maxAge=7*24*3600*1000
export function saveDraft(doctype,values){try{localStorage.setItem(prefix+doctype,JSON.stringify({savedAt:Date.now(),values}))}catch{}}
export function loadDraft(doctype){
 try{
  const draft=JSON.parse(localStorage.getItem(prefix+doctype)||'null')
  if(!draft||!draft.values||Date.now()-draft.savedAt>maxAge){localStorage.removeItem(prefix+doctype);return null}
  return draft
 }catch{return null}
}
export function clearDraft(doctype){try{localStorage.removeItem(prefix+doctype)}catch{}}

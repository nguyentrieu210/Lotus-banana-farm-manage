// Chờ tôi ký and the shared signing sheet (spec 003, US1), the same on phone and desktop.
// Signing, returning and reassigning go through lotus_farm.signing, which hands each document to its own chain
// (proposal, order, voucher, stock, period) so the checks are the ones of that document's screen.
// api.js is loaded on first use so this module stays testable in node (tests pass their own call function).
async function call(method,args,write){const api=await import('./api');return api.call(method,args,write)}

export const signingApi=(method,args={},write=false,callFn=call)=>callFn('lotus_farm.signing.'+method,args,write)

export const inbox=(args={},callFn=call)=>signingApi('inbox',{limit:100,...args},false,callFn)
export async function inboxCount(callFn=call){return Number((await signingApi('inbox_count',{},false,callFn))?.count||0)}
export const chainStatus=(row,callFn=call)=>signingApi('chain_status',{doctype:row.doctype,name:row.name},false,callFn)
export const signerOptions=(chain,company,callFn=call)=>signingApi('candidates',{chain,company},false,callFn)

// One confirmation for one or many documents; results come back per document.
export async function signDocuments(rows,callFn=call){
 const items=rows.map(({doctype,name,modified})=>({doctype,name,modified:modified||''}))
 return signingApi('sign_many',{items},true,callFn)
}
export async function signDocument(row,callFn=call){
 const result=await signDocuments([row],callFn)
 const one=result?.results?.[0]
 if(!one?.ok)throw Error(one?.message||'Không ký được chứng từ này.')
 return one
}
export function returnDocument(row,reason,callFn=call){
 const text=String(reason||'').trim()
 if(text.length<3)throw Error('Ghi lý do trả lại (ít nhất 3 ký tự).')
 return signingApi('return_any',{doctype:row.doctype,name:row.name,reason:text,modified:row.modified||''},true,callFn)
}
export function reassignStep(row,step,user,reason,callFn=call){
 const text=String(reason||'').trim()
 if(!user)throw Error('Chọn người ký thay.')
 if(text.length<3)throw Error('Ghi lý do chuyển người ký.')
 return signingApi('reassign',{doctype:row.doctype,name:row.name,step,user,reason:text},true,callFn)
}

export function money(value,currency='VND'){
 if(value==null||value==='')return ''
 const amount=Number(value)
 if(!Number.isFinite(amount))return ''
 return amount.toLocaleString('vi-VN',{maximumFractionDigits:0})+(currency&&currency!=='VND'?' '+currency:' đ')
}
export function shortDate(value){
 const text=String(value||'')
 return text.length>=10&&text[4]==='-'?text.slice(8,10)+'/'+text.slice(5,7)+'/'+text.slice(0,4)+(text.length>=16?' '+text.slice(11,16):''):text
}

// FR-012: the confirmation names what is being signed before anything is written.
export function confirmText(rows){
 const list=(Array.isArray(rows)?rows:[rows]).filter(Boolean)
 if(!list.length)return ''
 if(list.length===1){
  const r=list[0]
  return [r.chain_label||r.doctype,r.name,r.amount!=null&&r.amount!==''?money(r.amount,r.currency):'',r.step_title?'bước '+r.step_title:'']
   .filter(Boolean).join(' · ')+'. Ký bằng tài khoản đang đăng nhập?'
 }
 const total=list.reduce((sum,r)=>sum+(Number(r.amount)||0),0)
 return 'Ký '+list.length+' chứng từ'+(total?' · tổng '+money(total):'')+' ('+list.map(r=>r.name).join(', ')+'). Mỗi chứng từ được kiểm tra và ký riêng.'
}

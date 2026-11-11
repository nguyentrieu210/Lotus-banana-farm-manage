import test from 'node:test'
import assert from 'node:assert/strict'
import * as signing from '../src/use-signing.js'

function fakeCall(answers={}){
 const calls=[]
 const fn=async(method,args,write)=>{calls.push({method,args,write});const answer=answers[method.split('.').pop()];return typeof answer==='function'?answer(args):answer}
 fn.calls=calls
 return fn
}

test('signing one or many goes through sign_many with the version the list showed',async()=>{
 const callFn=fakeCall({sign_many:args=>({results:args.items.map(i=>({...i,ok:i.name!=='PO-2',message:i.name==='PO-2'?'Chứng từ đã thay đổi':'Đã ký'})),signed:1})})
 const rows=[{doctype:'Purchase Order',name:'PO-1',modified:'2026-11-10 08:00:00',amount:5},{doctype:'Purchase Order',name:'PO-2',modified:'x'}]
 const batch=await signing.signDocuments(rows,callFn)
 assert.equal(callFn.calls[0].method,'lotus_farm.signing.sign_many')
 assert.equal(callFn.calls[0].write,true)
 assert.deepEqual(callFn.calls[0].args.items[0],{doctype:'Purchase Order',name:'PO-1',modified:'2026-11-10 08:00:00'})
 assert.equal(batch.signed,1)
 await assert.rejects(signing.signDocument(rows[1],callFn),/Chứng từ đã thay đổi/)
 assert.equal((await signing.signDocument(rows[0],callFn)).ok,true)
})

test('return and reassign need a reason before anything is sent',async()=>{
 const callFn=fakeCall({return_any:{ok:1},reassign:{ok:1}})
 const row={doctype:'Payment Entry',name:'ACC-PAY-1',modified:'m'}
 assert.throws(()=>signing.returnDocument(row,' ab ',callFn),/lý do/)
 assert.throws(()=>signing.reassignStep(row,'CHIEF','u@x',' ',callFn),/lý do/)
 assert.throws(()=>signing.reassignStep(row,'CHIEF','','Nghỉ phép',callFn),/người ký thay/)
 assert.equal(callFn.calls.length,0)
 await signing.returnDocument(row,'Sai số tiền',callFn)
 assert.deepEqual(callFn.calls[0].args,{doctype:'Payment Entry',name:'ACC-PAY-1',reason:'Sai số tiền',modified:'m'})
 await signing.reassignStep(row,'CHIEF','u@x','Nghỉ phép',callFn)
 assert.equal(callFn.calls[1].method,'lotus_farm.signing.reassign')
})

test('the confirmation names type, number, amount and step',()=>{
 const one=signing.confirmText({chain_label:'Phiếu chi',name:'ACC-PAY-1',amount:12500000,currency:'VND',step_title:'Giám đốc duyệt chi'})
 assert.match(one,/Phiếu chi · ACC-PAY-1 · 12\.500\.000 đ · bước Giám đốc duyệt chi/)
 const many=signing.confirmText([{name:'A',amount:1000},{name:'B',amount:2000}])
 assert.match(many,/Ký 2 chứng từ · tổng 3\.000 đ \(A, B\)/)
 assert.equal(signing.confirmText([]),'')
 assert.equal(signing.shortDate('2026-11-10 14:05:00'),'10/11/2026 14:05')
 assert.equal(signing.money(null),'')
})

test('the badge count reads inbox_count',async()=>{
 const callFn=fakeCall({inbox_count:{count:3}})
 assert.equal(await signing.inboxCount(callFn),3)
 assert.equal(callFn.calls[0].write,false)
})

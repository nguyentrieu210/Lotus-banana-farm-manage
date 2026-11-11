import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document} from './support/mount.mjs'

let calls=[],reply=null
globalThis.fetch=async(url)=>{
 const u=new URL(url,'http://localhost')
 calls.push({method:u.pathname.split('/api/method/')[1],query:Object.fromEntries(u.searchParams)})
 return {ok:true,status:200,json:async()=>({message:reply})}
}
const Queue=await load('components/stock/IssueRequestQueue.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const rows=[
 {name:'MR-3',crew_name:'Đội C',team_name:'Tổ 7',work_name:'Bón phân',blocks:['C1'],warehouse:'Kho vườn',needed:'2026-11-15',open_lines:1,approved_by_name:'Đội trưởng C'},
 {name:'MR-1',crew_name:'Đội A + B',team_name:'Tổ 3',work_name:'Phun thuốc',blocks:['A12','A13'],warehouse:'Kho vườn',needed:'2026-11-09',open_lines:2,approved_by_name:'Đội trưởng A'},
 {name:'MR-2',crew_name:'Đội A + B',work_name:'Phun thuốc',blocks:'B4',warehouse:'Kho tổng',needed:'2026-11-12',open_lines:3},
]

test('cards by ngày cần, overdue in red, each with số, đội/tổ, lô, việc, kho, dòng còn, người duyệt; the count goes up',async()=>{
 reply={rows};calls=[]
 const counts=[],issued=[],handle={value:null}
 const view=mount({setup:()=>()=>h(Queue,{ref:r=>handle.value=r,company:'C',warehouse:'K',active:true,today:'2026-11-11',onCount:n=>counts.push(n),onIssue:n=>issued.push(n)})})
 await settle()
 assert.equal(calls[0].method,'lotus_farm.warehouse.issue_queue');assert.equal(calls[0].query.company,'C');assert.equal(calls[0].query.warehouse,'K')
 assert.equal(counts.at(-1),3)
 handle.value.show();await settle()
 const cards=[...document.querySelectorAll('dialog[open] .issue-queue__card')]
 assert.deepEqual(cards.map(c=>c.querySelector('strong').textContent.split(' · ')[0]),['MR-1','MR-2','MR-3'])
 assert.ok(cards[0].classList.contains('is-late'));assert.match(cards[0].textContent,/Quá hạn chưa cấp/)
 assert.ok(!cards[1].classList.contains('is-late'))
 assert.match(cards[0].textContent,/Đội A \+ B · Tổ 3.*Phun thuốc · cần 09\/11\/2026.*Lô A12, A13.*Kho vườn · còn 2 dòng · duyệt: Đội trưởng A/)
 assert.match(cards[1].textContent,/Đội A \+ B · Cả đội/)
 cards[0].querySelector('button').click();await settle()
 assert.deepEqual(issued,['MR-1'],'"Lập phiếu xuất" hands the request to the issue form')
 assert.equal(document.querySelector('dialog[open] .issue-queue__card'),null,'the list closes')
 view.unmount()
})

test('nothing is read while Xuất kho is not on screen',async()=>{
 reply={rows};calls=[]
 const view=mount({setup:()=>()=>h(Queue,{company:'C',active:false})})
 await settle()
 assert.equal(calls.length,0)
 view.unmount()
})

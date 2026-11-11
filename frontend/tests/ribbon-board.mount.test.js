import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document} from './support/mount.mjs'

const lotRow=(code,extra={})=>({block:'b-'+code,code,zone:'A',cut:50,bag:40,bag_left:10,rejected:2,harvested:8,kg:160,left:40,quarantine_until:null,...extra})
const card=(extra={})=>({tag:'red43',colour:'Đỏ',code:'DO',week:43,year:2026,lan:1,first_cut:'2026-08-20',start:'2026-11-02',end:'2026-11-20',status:'due',
 age_weeks:11,cut:100,bag:80,rejected:4,harvested:16,left:80,lots:[lotRow('A5'),lotRow('A6',{quarantine_until:'2026-11-14'})],...extra})
const due=(c,lot)=>({...lot,tag:c.tag,colour:c.colour,code_colour:c.code,week:c.week,lan:c.lan,start:c.start,end:c.end,status:c.status})
function board(cards=[card()],extra={}){
 const rows=cards.filter(c=>['due','overdue'].includes(c.status)).flatMap(c=>c.lots.filter(l=>l.left>0).map(l=>due(c,l)))
 return {farm:'F',zone:'',farms:[{name:'F',farm_name:'Vườn 222'}],zones:['A','B'],cards,due_rows:rows,day:'2026-11-10',
  left:cards.reduce((n,c)=>n+c.left,0),due:cards.filter(c=>c.status==='due').reduce((n,c)=>n+c.left,0),
  overdue:cards.filter(c=>c.status==='overdue').reduce((n,c)=>n+c.left,0),...extra}
}

let calls=[],reply=()=>board()
globalThis.fetch=async(url)=>{
 const u=new URL(url,'http://localhost')
 calls.push({method:u.pathname.replace('/api/method/',''),query:Object.fromEntries(u.searchParams)})
 return {ok:true,status:200,json:async()=>({message:reply()})}
}
const Board=await load('components/field/RibbonBoard.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const show=(props={})=>{calls=[];return mount({setup:()=>()=>h(Board,{farm:'F',...props})})}

test('the board reads the confirmed sổ lô of the farm and puts the totals first',async()=>{
 reply=()=>board()
 const view=show();await settle()
 assert.equal(calls[0].method,'lotus_farm.ribbon_board.board');assert.equal(calls[0].query.farm,'F')
 assert.match(view.root.querySelector('.ribbon-board__totals').textContent,/Còn trên cây\s*80.*Đến tuổi thu\s*80.*Quá tuổi thu\s*0/)
 view.unmount()
})

test('the due list names lô and colour with what is left, and a lô under quarantine says it cannot be harvested',async()=>{
 reply=()=>board()
 const view=show();await settle()
 const rows=[...view.root.querySelectorAll('.ribbon-due')]
 assert.equal(rows.length,2)
 assert.match(rows[0].textContent,/Lô A5 · Đỏ tuần 43 lần 1.*Còn 40 buồng/)
 assert.ok(!rows[0].classList.contains('is-held'))
 assert.ok(rows[1].classList.contains('is-held'));assert.match(rows[1].textContent,/Đang cách ly đến 14\/11\/2026: chưa được thu/)
 view.unmount()
})

test('one card per colour of a week, newest first; harvested-out colours only on request',async()=>{
 reply=()=>board([card(),card({tag:'white45',colour:'Trắng',code:'TRANG',week:45,status:'waiting',first_cut:'2026-09-03'}),card({tag:'blue40',colour:'Xanh',week:40,status:'done',left:0,first_cut:'2026-07-30'})])
 const view=show();await settle()
 const cards=[...view.root.querySelectorAll('.ribbon-card')]
 assert.deepEqual(cards.map(c=>c.querySelector('strong').textContent),['Trắng tuần 45 lần 1','Đỏ tuần 43 lần 1'])
 // Spec 004: the card is the kit ribbon batch card — status chip, age and lots, then the four counts.
 assert.match(cards[1].textContent,/11 tuần tuổi · 2 lô.*Đến tuổi thu.*Cắt bắp\s*100.*Bao\s*80.*Đã thu\s*16.*Còn trên cây\s*80/)
 view.root.querySelector('.ribbon-board__tools input[type=checkbox],.ribbon-board__tools button[role=checkbox]').click();await settle()
 assert.equal(view.root.querySelectorAll('.ribbon-card').length,3,'the done colour shows once asked')
 view.unmount()
})

test('a colour card opens its lô in a dialog',async()=>{
 reply=()=>board()
 const view=show();await settle()
 view.root.querySelector('.ribbon-card').click();await settle()
 assert.ok(dialog(),'a dialog opens')
 assert.match(dialog().textContent,/Đỏ tuần 43 lần 1/)
 assert.match(dialog().textContent,/thu dự kiến 02\/11\/2026 – 20\/11\/2026/)
 await new Promise(r=>setTimeout(r,300));await settle()
 assert.ok(dialog().querySelector('.ag-row[row-id="b-A5"]')&&dialog().querySelector('.ag-row[row-id="b-A6"]'),'one row per lô')
 view.unmount()
})

test('on the phone the board is compact: due list first, colour cards behind one button',async()=>{
 reply=()=>board()
 const view=show({mobile:true,compact:true});await settle()
 assert.equal(view.root.querySelectorAll('.ribbon-card').length,0)
 assert.equal(view.root.querySelectorAll('.ribbon-due').length,2)
 ;[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Xem từng màu dây')).click();await settle()
 assert.equal(view.root.querySelectorAll('.ribbon-card').length,1)
 view.unmount()
})

test('an empty sổ lô says so',async()=>{
 reply=()=>board([])
 const view=show();await settle()
 assert.match(view.root.textContent,/Chưa có màu nào đến tuổi thu/)
 assert.match(view.root.textContent,/Chưa có buồng đã cắt bắp trong sổ lô/)
 view.unmount()
})

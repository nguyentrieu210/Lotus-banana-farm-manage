import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,h} from './support/mount.mjs'
import {supplierOffer,cheapestCost,needsReason,defaultChoices,compareSelections} from '../src/procurement.js'
import {procurementNavigation,normalizeBuyingView} from '../src/procurement-navigation.js'
const Compare=await load('components/ProcurementCompare.vue')

// One request line quoted by two suppliers (unit_cost = landed cost per stock unit), one item quoted outside a request.
const urea={key:'MRL-1',item:'UREA',item_name:'Ure Phú Mỹ',stock_uom:'Kg',request:'MR-1',request_line:'MRL-1',need_qty:1000,approved:true,best_line:'Q2-1',offers:[
 {quotation:'Q1',line:'Q1-1',supplier:'KN',docstatus:1,unit_cost:13000,rate:13000,qty:20,uom:'Bao',stock_qty:1000,modified:'m1'},
 {quotation:'Q2',line:'Q2-1',supplier:'NN',docstatus:0,unit_cost:12400,rate:12400,qty:30,uom:'Bao',stock_qty:1500,modified:'m2'}]}
const lime={key:'item:VOI',item:'VOI',item_name:'Vôi bột',stock_uom:'Kg',request:'',request_line:'',need_qty:null,approved:false,best_line:'Q3-1',offers:[
 {quotation:'Q3',line:'Q3-1',supplier:'KN',docstatus:1,unit_cost:3000,rate:3000,qty:500,uom:'Kg',stock_qty:500,modified:'m3'}]}

test('comparison helpers choose the cheapest landed cost and ask a reason only for dearer picks',()=>{
 assert.equal(supplierOffer(urea,'NN').line,'Q2-1')
 assert.equal(supplierOffer(urea,'XX'),null)
 assert.equal(cheapestCost(urea),12400)
 assert.equal(needsReason(urea,'Q2-1'),false)
 assert.equal(needsReason(urea,'Q1-1'),true)
 assert.deepEqual(defaultChoices([urea,lime]),{'MRL-1':'Q2-1','item:VOI':'Q3-1'})
 // Never order more than the request still needs: 1000 kg of a 1500 kg quote = 20 bags of 50 kg.
 const [first,second]=compareSelections([urea,lime],defaultChoices([urea,lime]))
 assert.deepEqual(first,{quotation:'Q2',line:'Q2-1',modified:'m2',qty:20,reason:''})
 assert.deepEqual(second,{quotation:'Q3',line:'Q3-1',modified:'m3',qty:500,reason:''})
 assert.equal(compareSelections([urea],{'MRL-1':'Q1-1'},{'MRL-1':' Giao nhanh hơn '})[0].reason,'Giao nhanh hơn')
})

test('price comparison is a purchase menu entry after quotes',()=>{
 const ids=procurementNavigation.map(r=>r.id)
 assert.equal(ids[ids.indexOf('quotes')+1],'compare')
 assert.equal(normalizeBuyingView('compare'),'compare')
})

test('comparison table preselects the cheapest supplier, asks a reason for another and creates orders',async()=>{
 const calls=[]
 const api=async(name,args)=>{calls.push({name,args});if(name==='compare')return {rows:[urea],suppliers:[{name:'KN',label:'Kết Nông'},{name:'NN',label:'Nguyễn Ngọc'}],requests:[{name:'MR-1',approved:true,state:'Đã duyệt'}]};if(name==='select_quotes')return {orders:['PO-1'],approved:['PO-1']}}
 let created=null
 const view=mount({render:()=>h(Compare,{company:'C',canCreate:true,api,onCreated:r=>{created=r}})})
 await tick();await tick();await tick()
 const offer=label=>[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')===label)
 const cheap=offer('Chọn Nguyễn Ngọc cho Ure Phú Mỹ'),dear=offer('Chọn Kết Nông cho Ure Phú Mỹ')
 assert.ok(cheap&&dear,'one button per supplier offer')
 assert.equal(cheap.getAttribute('aria-pressed'),'true','cheapest is chosen by default')
 assert.match(cheap.textContent,/rẻ nhất/)
 const createButton=()=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith('Tạo đơn từ lựa chọn'))
 assert.equal(createButton().disabled,false)
 dear.click();await tick();await tick()
 assert.ok(document.querySelector('[aria-label="Lý do chọn Ure Phú Mỹ"]'),'a dearer pick asks why')
 assert.equal(createButton().disabled,true,'no order without the reason')
 offer('Chọn Nguyễn Ngọc cho Ure Phú Mỹ').click();await tick();await tick()
 createButton().click();await tick();await tick();await tick()
 const request=calls.find(c=>c.name==='select_quotes')
 assert.ok(request);assert.equal(request.args.selections[0].line,'Q2-1');assert.equal(request.args.selections[0].reason,'')
 assert.deepEqual(created,{orders:['PO-1'],approved:['PO-1']})
 view.unmount()
})

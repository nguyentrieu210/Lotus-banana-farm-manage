import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,loadModule,createApp,h,tick,document,window} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'

// vue-router reads the global history even with a memory history.
globalThis.history??=window.history
const calls=[]
let routes={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 const handler=routes[method]
 if(!handler)return {ok:false,status:404,json:async()=>({exc_type:'DoesNotExistError',message:method})}
 return {ok:true,status:200,json:async()=>({message:typeof handler==='function'?handler(args):handler})}
}
const pinia=createPinia();setActivePinia(pinia)
const FarmLandApp=await load('FarmLandApp.vue')
const {useSession}=await loadModule('store.js')
Object.assign(useSession(),{user:'farm@lotus',today:'2026-10-21',ready:true,farms:[],modules:{farms:['Farm Block']},capabilities:{},commands:{}})
const L='lotus_farm.farm_land.'
const lot=(code,over={})=>({name:'B-'+code,modified:'m',farm:'LOTUS-222',block_code:code,block_name:'Lô '+code,farm_zone:code[0],area_ha:2.5,plots:2,plots_area_ha:2.5,variety:'VIP 126',variety_label:'VIP 126',
 lotus_tree_count:6000,density:2400,planting_date:'',lotus_inferred_planting_date:'2026-04-01',lotus_estimated_flowering_date:'2026-11-01',lotus_estimated_sucker_selection_date:'2026-07-01',active:1,has_map:true,gaps:[],...over})
const overview=(canEdit)=>({farms:[{name:'LOTUS-180',farm_name:'Vườn 180'},{name:'LOTUS-222',farm_name:'Vườn 222'}],farm:'',can_edit:canEdit,varieties:['VIP 126'],
 gap_labels:{trees:'Chưa có số cây',variety:'Chưa có giống',map:'Chưa có ranh giới',planting:'Chưa có ngày trồng'},editable:[{field:'farm_zone',label:'Khu',kind:'text'},{field:'lotus_tree_count',label:'Số cây kiểm kê',kind:'int'}],
 blocks:[lot('A1'),lot('A2',{lotus_tree_count:0,density:null,gaps:['trees']}),lot('B1',{variety:null,variety_label:'',gaps:['variety']})],
 zones:[{zone:'A',blocks:2,area_ha:5,trees:6000,trees_per_ha:2400},{zone:'B',blocks:1,area_ha:2.5,trees:6000,trees_per_ha:2400}],
 summary:{blocks:3,area_ha:7.5,plots:6,counted_blocks:2,trees:12000,counted_area_ha:5,trees_per_ha:2400,gaps:{trees:1,variety:1,map:0,planting:0}}})
async function open(path){
 const router=createRouter({history:createMemoryHistory('/lotus'),routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push(path);await router.isReady()
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(FarmLandApp,{embedded:true})});app.use(pinia);app.use(router);app.mount(root)
 await tick();await tick()
 return {root,router,unmount:()=>{app.unmount();root.remove()}}
}
const text=root=>root.textContent.replace(/\s+/g,' ')
const rows=root=>[...root.querySelectorAll('.land-table tbody tr')].map(tr=>tr.querySelector('b').textContent)

test('lots list shows area, trees and density; the gap tile filters to lots missing a count',async()=>{
 calls.length=0;routes={[L+'overview']:overview(false)}
 const view=await open('/farms')
 assert.match(text(view.root),/7,5 ha.*3 lô · 6 thửa/)
 assert.match(text(view.root),/12\.000.*đã đếm 2\/3 lô/)
 assert.match(text(view.root),/2\.400 cây\/ha/)
 assert.deepEqual(rows(view.root),['A1','A2','B1'])
 view.root.querySelector('.land-gaps').click();await tick()
 assert.deepEqual(rows(view.root),['A2'],'only lots without a tree count')
 assert.ok(![...view.root.querySelectorAll('button')].some(b=>/Nhập Excel|Sửa .* lô/.test(b.textContent)),'no editing for readers')
 view.unmount()
})

test('a zone card filters the list and a row opens the lot page',async()=>{
 routes={[L+'overview']:overview(true),[L+'block_detail']:a=>a.section==='overview'?{can_edit:true,block:{...lot('B1'),farm_name:'Vườn 222'},plots:[{name:'P1',plot_code:'B1-1',plot_name:'Thửa 1',area_ha:1.2,active:1}],geometry:null,history:[]}:{}}
 const view=await open('/farms?farm=LOTUS-222')
 ;[...view.root.querySelectorAll('.land-zone')].find(b=>b.textContent.includes('Khu B')).click();await tick()
 assert.deepEqual(rows(view.root),['B1'])
 view.root.querySelector('.land-table tbody tr').click();await tick();await tick();await tick()
 assert.equal(view.router.currentRoute.value.query.block,'B-B1')
 assert.match(text(view.root),/Lô B1.*Vườn 222 · Khu B/)
 assert.match(text(view.root),/Thửa trong lô.*B1-1/)
 assert.match(text(view.root),/Lô chưa có ranh giới/)
 assert.ok([...view.root.querySelectorAll('button')].some(b=>b.textContent.includes('Sửa lô')),'land managers can edit')
 view.unmount()
})

import test from 'node:test'
import assert from 'node:assert/strict'
import {readdirSync,readFileSync} from 'node:fs'
import {label,stateLabel,docLabel} from '../src/labels.js'
import {workspaceDirectory,mergeWorkspaceActions} from '../src/workspace-directory.js'
import {hasMobileAccess,mobileActions} from '../src/mobile-menu.js'
import {createRouter,createMemoryHistory} from 'vue-router'
import {pages,pageRoutes} from '../src/domain.js'
import {internalWorkspaceTarget,workspaceModules} from '../src/workspace-routes.js'

test('cross-module links stay inside the workspace and preserve their query',()=>{
 const origin='http://localhost:8080'
 for(const path of Object.keys(workspaceModules))assert.deepEqual(internalWorkspaceTarget('/lotus/'+path+'?farm=LOTUS-222',origin),{path:'/'+path,query:{farm:'LOTUS-222'}})
 assert.deepEqual(internalWorkspaceTarget('/lotus/giao-viec?farm=F1',origin),{path:'/cong-viec',query:{farm:'F1'}})
 assert.deepEqual(internalWorkspaceTarget('/lotus/nhat-ky-cong-viec?farm=F1',origin),{path:'/cong-viec',query:{farm:'F1'}})
 assert.equal(internalWorkspaceTarget('https://example.com/lotus/kho',origin),null)
 assert.equal(internalWorkspaceTarget('/private/files/report.pdf',origin),null)
})

test('every workspace page resolves independently, including both planning pages',()=>{
 const router=createRouter({history:createMemoryHistory(),routes:pageRoutes({template:'<div />'})})
 for(const [path] of pages){
  const resolved=router.resolve('/'+path)
  assert.equal(resolved.matched.length,1,path)
  assert.equal(resolved.name,path)
 }
 assert.notEqual(router.resolve('/plans').name,router.resolve('/plan-norm').name)
})

test('schedule fields and choices are Vietnamese while enum keys stay intact',()=>{
 for(const field of ['rule_name','anchor','offset_days','repeat_days','quantity_basis'])assert.notEqual(label(field),field.replaceAll('_',' '))
 assert.equal(stateLabel('Planting'),'Trồng mới')
 assert.equal(stateLabel('Selected Suckers'),'Số chồi đã chọn')
 assert.equal(stateLabel('Area'),'Diện tích')
 assert.equal(docLabel('Plan Cohort'),'Đợt cây dự kiến')
 assert.equal(stateLabel('LOTUS-BAG'),'LOTUS-BAG')
})

test('every visible field and enum in custom schemas has a display translation',()=>{
 const root=new URL('../../lotus_farm/lotus_farm/doctype/',import.meta.url)
 const technical=new Set(['A','B','C','D','ADMS','CSV','File CSV','JSON','LAN SDK','Facebook','Zalo'])
 const missing=[]
 for(const folder of readdirSync(root)){
  let doc
  try{doc=JSON.parse(readFileSync(new URL(folder+'/'+folder+'.json',root),'utf8'))}catch{continue}
  assert.notEqual(docLabel(doc.name),doc.name,doc.name)
  for(const f of doc.fields||[]){
   if(f.hidden||['Section Break','Column Break','Tab Break','HTML','Button','Password'].includes(f.fieldtype))continue
   const text=label(f.fieldname,f.label)
   if(text===f.label&&/^[\x00-\x7f]+$/.test(text)&&/[A-Za-z]/.test(text))missing.push(doc.name+': '+f.fieldname)
   if(f.fieldtype==='Select')for(const option of (f.options||'').split('\n').filter(Boolean)){
    const caption=stateLabel(option)
    if(caption===option&&/^[\x00-\x7f]+$/.test(caption)&&/[A-Za-z]/.test(caption)&&!technical.has(option))missing.push(doc.name+': '+option)
   }
  }
 }
 assert.deepEqual(missing,[])
})

test('HR, attendance and labor remain separate destinations and honor permissions',()=>{
 const user={modules:{labor:['Labor Allocation']},capabilities:{hr:true,attendance:true}}
 const links=workspaceDirectory(user)
 assert.equal(links.find(a=>a.id==='global-hr').href,'/lotus/nhan-su')
 assert.equal(links.find(a=>a.id==='global-attendance').href,'/lotus/cham-cong')
 assert.equal(links.find(a=>a.id==='global-labor').href,'/lotus/labor')
 assert.ok(!workspaceDirectory({}).some(a=>a.id==='global-hr'))
 assert.ok(mobileActions(user).some(a=>a.id==='hr'))
 assert.ok(!mobileActions({modules:{labor:['Labor Allocation']}}).some(a=>a.id==='hr'))
 assert.equal(hasMobileAccess({capabilities:{hr:true}}),true)
})

test('shared directory preserves local actions and avoids duplicate destinations',()=>{
 const local=[{id:'home',label:'Trang chủ Lotus',href:'/lotus/mobile?farm=F1'},{id:'labor',label:'Bố trí nhân công',run:()=>{}}]
 const merged=mergeWorkspaceActions(local,workspaceDirectory({modules:{labor:['Labor Allocation']},capabilities:{hr:true}}))
 assert.equal(merged.filter(a=>a.href?.startsWith('/lotus/mobile')).length,1)
 assert.equal(merged.filter(a=>a.label==='Bố trí nhân công').length,1)
 assert.ok(merged.includes(local[1]))
 assert.ok(merged.some(a=>a.href==='/lotus/nhan-su'))
})

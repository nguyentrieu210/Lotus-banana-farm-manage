import test from 'node:test'
import assert from 'node:assert/strict'
import {loadModule} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createMemoryHistory} from 'vue-router'
import {hrNavigation,visibleHrNavigation,normalizeHrView,hrHref,hrPageTitle} from '../src/hr-navigation.js'
import {workspaceDirectory,mergeWorkspaceActions} from '../src/workspace-directory.js'
const {createLotusRouter,permittedRoute}=await loadModule('router.js')
const {useSession}=await loadModule('store.js')

test('shared HR targets preserve existing paths and distinguish quick-search destinations',()=>{
 const manager={capabilities:{hr:true,hr_manage:true,attendance:true}}
 assert.equal(visibleHrNavigation(manager).length,8)
 assert.equal(hrHref(hrNavigation[0]),'/lotus/nhan-su')
 assert.equal(hrHref(hrNavigation[1]),'/lotus/nhan-su?hr_view=candidates')
 assert.equal(hrHref(hrNavigation[3]),'/lotus/cham-cong')
 assert.equal(hrPageTitle('organization'),'Cơ cấu & chức danh')
 assert.equal(normalizeHrView(['payroll','employees']),'employees')
 const links=workspaceDirectory(manager)
 const merged=mergeWorkspaceActions([{label:'Tuyển dụng',href:'/lotus/nhan-su?hr_view=candidates&company=A'}],links)
 assert.equal(merged.filter(a=>a.label==='Tuyển dụng').length,1)
 assert.equal(merged.filter(a=>a.href?.startsWith('/lotus/nhan-su')).length,7)
 assert.ok(!permittedRoute('/nhan-su',{capabilities:{hr:true}}, {hr_view:'payroll'}))
 assert.ok(permittedRoute('/nhan-su',manager,{hr_view:'payroll'}))
})

test('real router handles direct HR links, normalization, reload and Back/Forward',async()=>{
 setActivePinia(createPinia())
 Object.assign(useSession(),{ready:true,capabilities:{hr:true,hr_manage:true,attendance:true},modules:{},farms:[]})
 const router=createLotusRouter({history:createMemoryHistory('/lotus')})
 await router.push('/nhan-su?hr_view=devices&company=A')
 assert.equal(router.currentRoute.value.query.hr_view,'devices')
 await router.push('/nhan-su?hr_view=candidates&company=A')
 router.back();await new Promise(resolve=>setTimeout(resolve,30))
 assert.equal(router.currentRoute.value.query.hr_view,'devices')
 router.forward();await new Promise(resolve=>setTimeout(resolve,30))
 assert.equal(router.currentRoute.value.query.hr_view,'candidates')
 await router.push('/nhan-su?hr_view=unknown&company=A')
 assert.deepEqual(router.currentRoute.value.query,{company:'A'})
 await router.push('/nhan-su?hr_view=employees');assert.equal(router.currentRoute.value.fullPath,'/nhan-su')
 const reloaded=createLotusRouter({history:createMemoryHistory('/lotus')})
 await reloaded.push('/nhan-su?hr_view=organization');assert.equal(reloaded.currentRoute.value.query.hr_view,'organization')
 useSession().capabilities.hr_manage=false
 await router.push('/nhan-su?hr_view=payroll');assert.equal(router.currentRoute.value.path,'/denied')
 useSession().capabilities={attendance:true}
 await router.push('/cham-cong');assert.equal(router.currentRoute.value.path,'/cham-cong')
 await router.push('/nhan-su?hr_view=devices');assert.equal(router.currentRoute.value.path,'/denied')
})

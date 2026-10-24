import {createRouter,createWebHistory} from 'vue-router'
import {pages,moduleKey,pageRoutes} from './domain'
import {useSession} from './store'
import {hasMobileAccess} from './mobile-menu'
import {workspaceModules} from './workspace-routes'
import {normalizeHrView,hrViewAllowed} from './hr-navigation.js'
import {procurementNavigation,normalizeBuyingView} from './procurement-navigation'
const placeholder={template:'<span />'}
export function permittedRoute(path,session,query={}){
 const page=path.replace(/^\//,'')
 if(page==='denied')return true
 if(page==='mobile')return hasMobileAccess(session)
 if(page==='nhan-su')return hrViewAllowed(query.hr_view,session)
 if(page==='mua-hang'){
  const item=procurementNavigation.find(r=>r.id===normalizeBuyingView(query.buying_view))
  return !!session.capabilities?.purchasing&&(!item.finance||!!session.capabilities?.purchasing_finance)&&(!item.invoice||!!session.capabilities?.purchasing_invoice_read)
 }
 if(workspaceModules[page]){const module=workspaceModules[page];return module.capability?!!session.capabilities?.[module.capability]:!!session.modules?.[module.module]?.length}
 if(['today','reports'].includes(page))return !!session.capabilities.home
 if(/^(farms|farm|blocks|block|plots|plot|cycles|cycle)\//.test(page))return !!session.modules.farms?.length
 const key=moduleKey(page)
 return pages.some(([p])=>p===page)&&!!session.modules[key]?.length
}
export function routeScope(route){const q={...route.query};for(const key of ['farm','block','plot','cycle'])if(route.params?.[key])q[key]=String(route.params[key]);return q}
export function createLotusRouter({history=createWebHistory('/lotus')}={}){
 const routes=[{path:'/',redirect:'/mobile'},{path:'/mobile',name:'mobile',component:placeholder,beforeEnter:()=>useSession().capabilities.home?{path:'/reports'}:true},{path:'/today',redirect:to=>({path:'/reports',query:to.query})},{path:'/giao-viec',redirect:to=>({path:'/cong-viec',query:{...to.query,action:'assign'}})},...pageRoutes(placeholder),
 ...[['farm','farms'],['block','blocks']].map(([name,path])=>({path:'/'+path+'/:'+name,alias:'/'+name+'/:'+name,redirect:to=>({path:'/farms',query:{...to.query,[name]:to.params[name]}})})),
 ...[['plot','plots'],['cycle','cycles']].map(([name,path])=>({path:'/'+path+'/:'+name,name,alias:'/'+name+'/:'+name,component:placeholder})),
 {path:'/denied',name:'denied',component:placeholder},{path:'/:pathMatch(.*)*',redirect:'/denied'}]
 const router=createRouter({history,routes})
 router.beforeEach(async to=>{
  const session=useSession()
  if(to.name==='denied')return true
  try{await session.load()}catch{return {name:'denied'}}
  const q=routeScope(to)
  if(to.path==='/nhan-su'&&q.hr_view!=null&&(normalizeHrView(q.hr_view)!==q.hr_view||q.hr_view==='employees')){
   const query={...to.query};delete query.hr_view
   return {path:to.path,query,replace:true}
  }
  if(!permittedRoute(to.path,session,q)||(q.farm&&!session.farms.some(f=>f.name===q.farm)))return {name:'denied'}
  return true
 })
 return router
}

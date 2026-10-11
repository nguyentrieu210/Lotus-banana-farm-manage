import {createRouter,createWebHistory} from 'vue-router'
import {pages,moduleKey} from './domain'
import {useSession} from './store'
import {hasMobileAccess} from './mobile-menu'
const placeholder={template:'<span />'}
export function permittedRoute(path,session){
 const page=path.replace(/^\//,'')
 if(page==='denied')return true
 if(page==='mobile')return hasMobileAccess(session)
 if(['today','reports'].includes(page))return !!session.capabilities.home
 if(/^(farms|farm|blocks|block|plots|plot|cycles|cycle)\//.test(page))return !!session.modules.farms?.length
 const key=moduleKey(page)
 return pages.some(([p])=>p===page)&&!!session.modules[key]?.length
}
export function routeScope(route){const q={...route.query};for(const key of ['farm','block','plot','cycle'])if(route.params?.[key])q[key]=String(route.params[key]);return q}
export function createLotusRouter(){
 const routes=[{path:'/',redirect:'/mobile'},...pages.map(([path])=>({path:'/'+path,name:moduleKey(path),component:placeholder})),
 ...[['farm','farms'],['block','blocks'],['plot','plots'],['cycle','cycles']].map(([name,path])=>({path:'/'+path+'/:'+name,name,alias:'/'+name+'/:'+name,component:placeholder})),
 {path:'/denied',name:'denied',component:placeholder},{path:'/:pathMatch(.*)*',redirect:'/denied'}]
 const router=createRouter({history:createWebHistory('/lotus'),routes})
 router.beforeEach(async to=>{
  const session=useSession()
  if(to.name==='denied')return true
  try{await session.load()}catch{return {name:'denied'}}
  const q=routeScope(to)
  if(!permittedRoute(to.path,session)||(q.farm&&!session.farms.some(f=>f.name===q.farm)))return {name:'denied'}
  return true
 })
 return router
}

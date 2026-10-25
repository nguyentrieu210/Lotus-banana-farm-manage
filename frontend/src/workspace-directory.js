import {visibleHrNavigation,hrHref,normalizeHrView} from './hr-navigation.js'
// One permission-checked directory for all Lotus desktop entrypoints.
export function workspaceDirectory(session){
 const links=[{id:'global-home',label:'Tổng quan',href:'/lotus/reports'}]
 if(session?.capabilities?.['work_journal.read'])links.push({id:'global-journal',label:'Nhật ký công việc',href:'/lotus/nhat-ky-cong-viec'})
 if(session?.capabilities?.user_admin)links.push({id:'global-users',label:'Người dùng & phân quyền',href:'/lotus/nguoi-dung'})
 for(const item of visibleHrNavigation(session))links.push({id:item.id==='employees'?'global-hr':item.id==='attendance'?'global-attendance':'global-hr-'+item.id,label:item.label,href:hrHref(item)})
 if(session?.modules?.labor?.length)links.push({id:'global-labor',label:'Bố trí nhân công',href:'/lotus/labor'})
 if(session?.modules?.plans?.length)links.push({id:'global-plan-norm',label:'Cấu hình kế hoạch & định mức',href:'/lotus/plan-norm'})
 if(session?.capabilities?.stock)links.push({id:'global-stock',label:'Quản lý kho',href:'/lotus/kho'})
 return links.map(link=>({...link,navigation:true}))
}
let pending
export function loadWorkspaceDirectory(loader){return pending??=loader().then(workspaceDirectory).catch(()=>{pending=null;return []})}
function destinationKey(href){
 if(!href)return null
 try{const url=new URL(href,'http://lotus.local');const view=normalizeHrView(url.searchParams.get('hr_view'));return url.pathname+(url.pathname==='/lotus/nhan-su'&&view!=='employees'?'?hr_view='+view:'')}
 catch{return href}
}
export function mergeWorkspaceActions(local,global){
 const seen=new Set()
 return [...local,...global].filter(action=>{
  const path=destinationKey(action.href)
  if(seen.has(action.label)||(path&&seen.has(path)))return false
  seen.add(action.label);if(path)seen.add(path);return true
 })
}

// One permission-checked directory for all Lotus desktop entrypoints.
export function workspaceDirectory(session){
 const links=[{id:'global-home',label:'Trang chủ',href:'/lotus/mobile'}]
 if(session?.capabilities?.user_admin)links.push({id:'global-users',label:'Người dùng & phân quyền',href:'/lotus/nguoi-dung'})
 if(session?.capabilities?.hr)links.push({id:'global-hr',label:'Hồ sơ nhân sự',href:'/lotus/nhan-su'})
 if(session?.capabilities?.attendance)links.push({id:'global-attendance',label:'Chấm công',href:'/lotus/cham-cong'})
 if(session?.modules?.labor?.length)links.push({id:'global-labor',label:'Bố trí nhân công',href:'/lotus/labor'})
 if(session?.modules?.plans?.length)links.push({id:'global-plan-norm',label:'Cấu hình kế hoạch & định mức',href:'/lotus/plan-norm'})
 if(session?.capabilities?.stock)links.push({id:'global-stock',label:'Quản lý kho',href:'/lotus/kho'})
 return links.map(link=>({...link,navigation:true}))
}
let pending
export function loadWorkspaceDirectory(loader){return pending??=loader().then(workspaceDirectory).catch(()=>{pending=null;return []})}
export function mergeWorkspaceActions(local,global){
 const seen=new Set()
 return [...local,...global].filter(action=>{
  const path=action.href?.split('?')[0]
  if(seen.has(action.label)||(path&&seen.has(path)))return false
  seen.add(action.label);if(path)seen.add(path);return true
 })
}

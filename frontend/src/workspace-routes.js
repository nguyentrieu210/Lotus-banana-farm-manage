// The desktop modules share the parent shell instead of reloading standalone entrypoints.
export const workspaceModules={
 'nguoi-dung':{label:'Người dùng & phân quyền',capability:'user_admin'},
 'nhan-su':{label:'Hồ sơ nhân sự',capability:'hr'},
 'cham-cong':{label:'Chấm công',capability:'attendance'},
 'kho':{label:'Quản lý kho',capability:'stock'},
 'cong-viec':{label:'Công việc vườn',module:'work'},
 farms:{label:'Vườn & lô',module:'farms'},
}
export function internalWorkspaceTarget(href,origin){
 let url
 try{url=new URL(href,origin)}catch{return null}
 if(url.origin!==origin||!url.pathname.startsWith('/lotus/'))return null
 const path=url.pathname.slice('/lotus/'.length).replace(/\/$/,'')
 if(path==='giao-viec'){url.pathname='/lotus/cong-viec';url.searchParams.set('action','assign')}
 return {path:url.pathname.slice('/lotus'.length),query:Object.fromEntries(url.searchParams)}
}

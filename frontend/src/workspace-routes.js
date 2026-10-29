// The desktop modules share the parent shell instead of reloading standalone entrypoints.
export const workspaceModules={
 'mua-hang':{label:'Mua hàng',capability:'purchasing'},
 'nguoi-dung':{label:'Người dùng & phân quyền',capability:'user_admin'},
 'nhan-su':{label:'Hồ sơ nhân viên',capability:'hr'},
 'cham-cong':{label:'Chấm công',capability:'attendance'},
 'kho':{label:'Quản lý kho',capability:'stock'},
 'cong-viec':{label:'Báo cáo ngày',capability:'field_report'},
 farms:{label:'Vườn & lô',module:'farms'},
 forecast:{label:'Dự thu',module:'forecast'},
 'mau-day':{label:'Danh mục màu dây',module:'mau-day'},
 'tai-chinh':{label:'Tài chính – Kế toán',capability:'finance'},
}
export function internalWorkspaceTarget(href,origin){
 let url
 try{url=new URL(href,origin)}catch{return null}
 if(url.origin!==origin||!url.pathname.startsWith('/lotus/'))return null
 const path=url.pathname.slice('/lotus/'.length).replace(/\/$/,'')
 // Old giao việc / nhật ký links open the đội daily report.
 if(path==='giao-viec'||path==='nhat-ky-cong-viec')url.pathname='/lotus/cong-viec'
 return {path:url.pathname.slice('/lotus'.length),query:Object.fromEntries(url.searchParams)}
}

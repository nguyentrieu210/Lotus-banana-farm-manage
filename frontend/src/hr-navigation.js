import {erpSection,withErpNav,erpViewLabel} from './erp-sections.js'
// Shared desktop HR destinations: sidebar, quick search, titles and route checks.
export const hrNavigation=[
 {id:'employees',label:'Hồ sơ nhân viên',icon:'id-card',path:'nhan-su',capability:'hr'},
 {id:'candidates',label:'Tuyển dụng',icon:'people',path:'nhan-su',capability:'hr'},
 {id:'onboarding',label:'Tiếp nhận',icon:'check',path:'nhan-su',capability:'hr'},
 {id:'attendance',label:'Chấm công',icon:'clock',path:'cham-cong',capability:'attendance'},
 {id:'payroll',label:'Kỳ công & bảng lương',icon:'wallet',path:'nhan-su',capability:'hr',manager:true},
 {id:'teams',label:'Phân tổ/đội',icon:'users',path:'nhan-su',capability:'hr',manager:true,setup:true},
 {id:'organization',label:'Cơ cấu & chức danh',icon:'people',path:'nhan-su',capability:'hr',setup:true},
 {id:'devices',label:'Máy chấm công',icon:'clock',path:'nhan-su',capability:'hr',setup:true},
 {id:'import',label:'Nhập dữ liệu nhân sự',icon:'upload',path:'nhan-su',capability:'hr',setup:true},
]
export function normalizeHrView(value){return hrNavigation.some(x=>x.path==='nhan-su'&&x.id===value)||erpSection('hr',value)?value:'employees'}
export function hrQuery(id){return id==='employees'||id==='attendance'?{}:{hr_view:id}}
export function hrHref(item){const query=new URLSearchParams(hrQuery(item.id)).toString();return '/lotus/'+item.path+(query?'?'+query:'')}
export function hrItemAllowed(item,session){return !!session?.capabilities?.[item.capability]&&(!item.manager||!!session?.capabilities?.hr_manage)}
// ERP sections (Nghỉ phép, Biến động, Thưởng & khấu trừ…) open inside the HR page; the server already filtered them by permission.
export function visibleHrNavigation(session){const items=hrNavigation.filter(x=>hrItemAllowed(x,session));return session?.capabilities?.hr?withErpNav(items,'hr',{path:'nhan-su',capability:'hr'}):items}
export function hrViewAllowed(value,session){const id=normalizeHrView(value);return erpSection('hr',id)?!!session?.capabilities?.hr:hrItemAllowed(hrNavigation.find(x=>x.id===id),session)}
export function hrPageTitle(value){const id=normalizeHrView(value);return erpViewLabel('hr',id)||hrNavigation.find(x=>x.id===id).label}

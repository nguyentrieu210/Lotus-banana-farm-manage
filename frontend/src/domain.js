export const pages=[['nguoi-dung','Người dùng & phân quyền'],['tai-chinh','Tài chính – Kế toán'],['nhan-su','Hồ sơ nhân sự'],['cham-cong','Chấm công'],['kho','Quản lý kho'],['cong-viec','Công việc ngoài vườn'],['alerts','Cảnh báo'],['farms','Vườn & lô'],['forecast','Dự thu'],['mau-day','Danh mục màu dây'],['map','Bản đồ chăm sóc'],['reports','Tổng quan'],['admin/masters','Danh mục'],['admin/settings','Cấu hình']]
pages.push(['mua-hang','Mua hàng'])
export const titles=Object.fromEntries(pages)
// Sidebar grouping of `pages`: [path, LotusIcon name, optional shorter sidebar label]. Every page belongs to exactly one group.
export const navGroups=[
 {label:'Tổng quan',icon:'chart',items:[['reports','chart','Tổng quan'],['alerts','alert','Cảnh báo']]},
 {label:'Việc hằng ngày',icon:'clipboard',kind:'field',items:[['cong-viec','clipboard','Việc hằng ngày'],['forecast','trending','Dự thu'],['mau-day','calendar','Màu dây cắt bắp']]},
 {label:'Vườn & lô',icon:'sprout',items:[['farms','sprout','Danh mục lô'],['map','map','Bản đồ lô']]},
 {label:'Kho',icon:'warehouse',kind:'stock',items:[['kho','warehouse','Quản lý kho']]},
 {label:'Mua hàng',icon:'cart',kind:'buying',items:[['mua-hang','cart','Mua hàng']]},
 {label:'Tài chính – Kế toán',icon:'wallet',kind:'finance',items:[['tai-chinh','wallet','Tài chính – Kế toán']]},
 {label:'Nhân sự',icon:'people',kind:'hr',items:[['nhan-su','id-card','Hồ sơ nhân viên'],['cham-cong','clock','Chấm công']]},
 {label:'Thiết lập',icon:'settings',items:[['admin/masters','database','Danh mục'],['admin/settings','settings','Cấu hình'],['nguoi-dung','user-cog','Người dùng & phân quyền']]},
]
export const moduleKey=p=>p.replace('admin/','')
// A permission module can contain several pages; router names must remain unique.
export const pageRoutes=component=>pages.map(([path])=>({path:'/'+path,name:path,component}))
export const fmt=v=>v==null?'—':typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:3}):String(v)
export const cleanFields=(schema,doc)=>Object.fromEntries(schema.fields.filter(f=>!f.read_only&&f.fieldtype!=='Table').map(f=>[f.fieldname,doc[f.fieldname]??(f.default??null)]).concat(schema.fields.filter(f=>!f.read_only&&f.fieldtype==='Table').map(f=>[f.fieldname,(doc[f.fieldname]||[]).map(row=>Object.fromEntries(schema.tables[f.options].filter(c=>!c.read_only).map(c=>[c.fieldname,row[c.fieldname]??null])))])))

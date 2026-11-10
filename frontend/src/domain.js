export const pages=[['nguoi-dung','Người dùng & phân quyền'],['tai-chinh','Tài chính – Kế toán'],['nhan-su','Hồ sơ nhân sự'],['cham-cong','Chấm công'],['kho','Quản lý kho'],['cong-viec','Công việc ngoài vườn'],['alerts','Cảnh báo'],['farms','Vườn & lô'],['forecast','Dự thu'],['mau-day','Danh mục màu dây'],['work','Công việc'],['materials','Vật tư'],['measurements','Đo trái'],['harvest','Thu hoạch'],['incoming-qc','QC đầu vào'],['packhouse','Xưởng đóng gói'],['cycle-close','Kết vụ'],['trace','Truy xuất'],['map','Bản đồ chăm sóc'],['reports','Tổng quan'],['admin/masters','Danh mục'],['admin/imports','Nhập dữ liệu'],['admin/settings','Cấu hình']]
pages.push(['cho-ky','Chờ tôi ký'],['mua-hang','Mua hàng'])
export const titles=Object.fromEntries(pages)
// Sidebar grouping of `pages`: [path, LotusIcon name, optional shorter sidebar label]. Every page belongs to exactly one group.
export const navGroups=[
 {label:'Tổng quan',icon:'chart',items:[['reports','chart','Tổng quan'],['cho-ky','edit','Chờ tôi ký'],['alerts','alert','Cảnh báo']]},
 {label:'Việc hằng ngày',icon:'clipboard',kind:'field',items:[['cong-viec','clipboard','Việc hằng ngày'],['forecast','trending','Dự thu'],['mau-day','calendar','Màu dây cắt bắp']]},
 {label:'Vườn & lô',icon:'sprout',items:[['farms','sprout','Danh mục lô'],['map','map','Bản đồ lô'],['work','list','Sâu bệnh & ghi nhận khác'],['materials','boxes','Vật tư theo việc'],['cycle-close','flag','Kết vụ']]},
 {label:'Sau thu hoạch',icon:'basket',items:[['harvest','basket','Lô thu hoạch'],['measurements','ruler','Đo trái'],['incoming-qc','shield','QC đầu vào'],['packhouse','package','Đóng gói'],['trace','route','Truy xuất']]},
 {label:'Kho',icon:'warehouse',kind:'stock',items:[['kho','warehouse','Quản lý kho']]},
 {label:'Mua hàng',icon:'cart',kind:'buying',items:[['mua-hang','cart','Mua hàng']]},
 {label:'Tài chính – Kế toán',icon:'wallet',kind:'finance',items:[['tai-chinh','wallet','Tài chính – Kế toán']]},
 {label:'Nhân sự',icon:'people',kind:'hr',items:[['nhan-su','id-card','Hồ sơ nhân viên'],['cham-cong','clock','Chấm công']]},
 {label:'Thiết lập',icon:'settings',items:[['admin/masters','database','Danh mục'],['admin/imports','upload','Nhập dữ liệu'],['admin/settings','settings','Cấu hình'],['nguoi-dung','user-cog','Người dùng & phân quyền']]},
]
export const moduleKey=p=>p==='forecast-onedrive'?'forecast':p.replace('admin/','')
// A permission module can contain several pages; router names must remain unique.
export const pageRoutes=component=>pages.map(([path])=>({path:'/'+path,name:path,component}))
export const fmt=v=>v==null?'—':typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:3}):String(v)
export const cleanFields=(schema,doc)=>Object.fromEntries(schema.fields.filter(f=>!f.read_only&&f.fieldtype!=='Table').map(f=>[f.fieldname,doc[f.fieldname]??(f.default??null)]).concat(schema.fields.filter(f=>!f.read_only&&f.fieldtype==='Table').map(f=>[f.fieldname,(doc[f.fieldname]||[]).map(row=>Object.fromEntries(schema.tables[f.options].filter(c=>!c.read_only).map(c=>[c.fieldname,row[c.fieldname]??null])))])))

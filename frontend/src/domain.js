export const pages=[['nguoi-dung','Người dùng & phân quyền'],['nhan-su','Hồ sơ nhân sự'],['cham-cong','Chấm công'],['kho','Quản lý kho'],['cong-viec','Công việc vườn'],['alerts','Cảnh báo'],['farms','Vườn'],['plans','Kế hoạch'],['plan-norm','Cấu hình kế hoạch & định mức'],['forecast','Dự thu'],['work','Công việc'],['labor','Bố trí nhân công'],['materials','Vật tư'],['losses','Hủy & tổn thất'],['measurements','Đo trái'],['harvest','Thu hoạch'],['incoming-qc','QC đầu vào'],['packhouse','Xưởng đóng gói'],['daily-close','Chốt ngày'],['cycle-close','Kết vụ'],['trace','Truy xuất'],['map','Bản đồ chăm sóc'],['reports','Tổng quan'],['admin/masters','Danh mục'],['admin/imports','Nhập dữ liệu'],['admin/settings','Cấu hình']]
export const titles=Object.fromEntries(pages)
// Sidebar grouping of `pages`: [path, LotusIcon name, optional shorter sidebar label]. Every page belongs to exactly one group.
export const navGroups=[
 // Ordered by the operating flow: land & cycle → daily work → plant & bunch → harvest → forecast.
 {label:'Tổng quan',items:[['reports','chart']]},
 {label:'Bản đồ',items:[['map','map','Bản đồ chăm sóc']]},
 {label:'Vườn & vụ',items:[['farms','sprout']]},
 {label:'Công việc hằng ngày',items:[['cong-viec','check'],['plans','clipboard'],['work','list','Tiến độ công việc'],['labor','people'],['materials','boxes','Vật tư theo việc'],['daily-close','lock']]},
 {label:'Cây & buồng',items:[['measurements','ruler'],['losses','trash'],['cycle-close','flag']]},
 {label:'Thu hoạch & đóng gói',items:[['harvest','basket'],['incoming-qc','shield'],['packhouse','package'],['trace','route']]},
 {label:'Dự thu',items:[['forecast','trending']]},
 {label:'Kho & mua hàng',items:[['kho','warehouse']]},
 {label:'Nhân sự',items:[['nhan-su','id-card'],['cham-cong','clock']]},
 {label:'Thiết lập',items:[['alerts','alert'],['admin/masters','database'],['plan-norm','sliders','Cấu hình KH & định mức'],['admin/imports','upload'],['admin/settings','settings'],['nguoi-dung','user-cog']]},
]
export const moduleKey=p=>p==='plan-norm'?'plans':p.replace('admin/','')
// A permission module can contain several pages; router names must remain unique.
export const pageRoutes=component=>pages.map(([path])=>({path:'/'+path,name:path,component}))
export const fmt=v=>v==null?'—':typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:3}):String(v)
export const cleanFields=(schema,doc)=>Object.fromEntries(schema.fields.filter(f=>!f.read_only&&f.fieldtype!=='Table').map(f=>[f.fieldname,doc[f.fieldname]??(f.default??null)]).concat(schema.fields.filter(f=>!f.read_only&&f.fieldtype==='Table').map(f=>[f.fieldname,(doc[f.fieldname]||[]).map(row=>Object.fromEntries(schema.tables[f.options].filter(c=>!c.read_only).map(c=>[c.fieldname,row[c.fieldname]??null])))])))
export function laborMatrix(tasks,snapshots){const groups=new Map();for(const task of tasks){const key=task.work_category||task.work_type;const g=groups.get(key)||{name:key,required:0,allocated:0,present:null,absent:null};g.required+=Number(task.required_workdays||0);g.allocated+=Number(task.allocated_workdays||0);groups.set(key,g)}for(const row of snapshots){const g=groups.get(row.work_category)||{name:row.work_category,required:0,allocated:0,present:null,absent:null};g.present=(g.present||0)+Number(row.present||0);g.absent=(g.absent||0)+Number(row.absent||0);groups.set(row.work_category,g)}return [...groups.values()].map(g=>({...g,gap:g.present==null?null:g.present-g.required,allocation_gap:g.allocated-g.required}))}

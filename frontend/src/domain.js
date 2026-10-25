export const pages=[['nguoi-dung','Người dùng & phân quyền'],['tai-chinh','Tài chính – Kế toán'],['nhan-su','Hồ sơ nhân sự'],['cham-cong','Chấm công'],['kho','Quản lý kho'],['cong-viec','Công việc vườn'],['alerts','Cảnh báo'],['farms','Vườn & lô'],['plans','Kế hoạch'],['plan-norm','Cấu hình kế hoạch & định mức'],['forecast','Dự thu'],['forecast-onedrive','Dự thu OneDrive'],['work','Công việc'],['labor','Bố trí nhân công'],['materials','Vật tư'],['losses','Hủy & tổn thất'],['measurements','Đo trái'],['harvest','Thu hoạch'],['incoming-qc','QC đầu vào'],['packhouse','Xưởng đóng gói'],['daily-close','Chốt ngày'],['cycle-close','Kết vụ'],['trace','Truy xuất'],['map','Bản đồ chăm sóc'],['reports','Tổng quan'],['admin/masters','Danh mục'],['admin/imports','Nhập dữ liệu'],['admin/settings','Cấu hình']]
pages.push(['mua-hang','Mua hàng'])
export const titles=Object.fromEntries(pages)
// Sidebar grouping of `pages`: [path, LotusIcon name, optional shorter sidebar label]. Every page belongs to exactly one group.
export const navGroups=[
 {label:'Tổng quan',icon:'chart',items:[['reports','chart','Tổng quan'],['alerts','alert','Cảnh báo']]},
 {label:'Quản lý vườn',icon:'sprout',items:[['farms','sprout','Vườn & lô'],['map','map','Bản đồ lô'],['cycle-close','flag','Kết vụ']]},
 {label:'Kế hoạch sản xuất',icon:'clipboard',items:[['plans','clipboard','Kế hoạch sản xuất']]},
 {label:'Điều hành công việc',icon:'check',items:[['cong-viec','check','Công việc ngoài vườn'],['work','list','Tiến độ & kết quả'],['labor','people','Bố trí nhân công'],['materials','boxes','Vật tư theo việc'],['daily-close','lock','Chốt ngày']]},
 {label:'Dự thu',icon:'trending',items:[['forecast','trending','Dự thu'],['forecast-onedrive','route','Dự thu OneDrive']]},
 {label:'Thu hoạch & đóng gói',icon:'basket',items:[['harvest','basket','Thu hoạch'],['measurements','ruler','Đo trái'],['losses','trash','Hủy & tổn thất'],['incoming-qc','shield','QC đầu vào'],['packhouse','package','Đóng gói'],['trace','route','Truy xuất']]},
 {label:'Kho',icon:'warehouse',kind:'stock',items:[['kho','warehouse','Quản lý kho']]},
 {label:'Mua hàng',icon:'cart',kind:'buying',items:[['mua-hang','cart','Mua hàng']]},
 {label:'Tài chính – Kế toán',icon:'wallet',items:[['tai-chinh','wallet','Tài chính – Kế toán']]},
 {label:'Nhân sự',icon:'people',kind:'hr',items:[['nhan-su','id-card','Hồ sơ nhân viên'],['cham-cong','clock','Chấm công']]},
 {label:'Thiết lập',icon:'settings',items:[['admin/masters','database','Danh mục'],['plan-norm','sliders','Định mức & chu kỳ'],['admin/imports','upload','Nhập dữ liệu'],['admin/settings','settings','Cấu hình'],['nguoi-dung','user-cog','Người dùng & phân quyền']]},
]
export const moduleKey=p=>p==='plan-norm'?'plans':p==='forecast-onedrive'?'forecast':p.replace('admin/','')
// A permission module can contain several pages; router names must remain unique.
export const pageRoutes=component=>pages.map(([path])=>({path:'/'+path,name:path,component}))
export const fmt=v=>v==null?'—':typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:3}):String(v)
export const cleanFields=(schema,doc)=>Object.fromEntries(schema.fields.filter(f=>!f.read_only&&f.fieldtype!=='Table').map(f=>[f.fieldname,doc[f.fieldname]??(f.default??null)]).concat(schema.fields.filter(f=>!f.read_only&&f.fieldtype==='Table').map(f=>[f.fieldname,(doc[f.fieldname]||[]).map(row=>Object.fromEntries(schema.tables[f.options].filter(c=>!c.read_only).map(c=>[c.fieldname,row[c.fieldname]??null])))])))
export function laborMatrix(tasks,snapshots){const groups=new Map();for(const task of tasks){const key=task.work_category||task.work_type;const g=groups.get(key)||{name:key,required:0,allocated:0,present:null,absent:null};g.required+=Number(task.required_workdays||0);g.allocated+=Number(task.allocated_workdays||0);groups.set(key,g)}for(const row of snapshots){const g=groups.get(row.work_category)||{name:row.work_category,required:0,allocated:0,present:null,absent:null};g.present=(g.present||0)+Number(row.present||0);g.absent=(g.absent||0)+Number(row.absent||0);groups.set(row.work_category,g)}return [...groups.values()].map(g=>({...g,gap:g.present==null?null:g.present-g.required,allocation_gap:g.allocated-g.required}))}

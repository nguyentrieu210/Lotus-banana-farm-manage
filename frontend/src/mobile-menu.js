// Mobile navigation is derived from real Frappe permissions, not the displayed job title.
// A user with multiple roles receives the union of the work they can actually access.
const items = [
  {group:'Quản trị',id:'users',label:'Người dùng & phân quyền',detail:'Tài khoản, vai trò và phạm vi vườn',icon:'people',href:'/lotus/nguoi-dung',capability:'user_admin'},
  {group:'Nhân sự và chấm công',id:'hr',label:'Hồ sơ nhân sự',detail:'Nhân viên, tuyển dụng và tiếp nhận',icon:'people',href:'/lotus/nhan-su',capability:'hr'},
  {group:'Nhân sự và chấm công',id:'attendance',label:'Chấm công',detail:'Công ngày, đội khoán và bảng công tháng',icon:'clock',href:'/lotus/cham-cong',capability:'attendance'},
  {group:'Công việc ngoài Vườn',id:'farm-work',label:'Công việc ngoài Vườn',detail:'Giao việc, báo kết quả trên điện thoại',icon:'check',href:'/work',module:'work'},
  {group:'Xưởng và vật tư',id:'stock',label:'Quản lý kho',detail:'Tồn, nhập xuất và kiểm kê',icon:'warehouse',href:'/lotus/kho',capability:'stock'},
  {group:'Công việc ngoài Vườn',id:'assign',label:'Giao việc cho tổ',detail:'Chọn lô lớn và công việc',icon:'send',href:'/work?action=assign',module:'work',command:'work'},
  {group:'Công việc ngoài Vườn',id:'work',label:'Xem công việc',detail:'Kế hoạch và tiến độ hôm nay',icon:'list',path:'work',module:'work'},
  {group:'Công việc ngoài Vườn',id:'actual',label:'Báo kết quả',detail:'Ghi số lượng đã làm',icon:'tick',path:'work',module:'work',doctype:'Daily Work Result',create:'Daily Work Result'},
  {group:'Nhân sự và chấm công',id:'labor',label:'Bố trí nhân công',detail:'Phân bổ lao động theo công việc',icon:'people',path:'labor',module:'labor'},
  {group:'Công việc ngoài Vườn',id:'disease',label:'Kiểm tra sâu bệnh',detail:'Ghi nhận tình hình vườn',icon:'leaf',path:'work',module:'work',doctype:'Disease Observation',create:'Disease Observation'},
  {group:'Công việc ngoài Vườn',id:'losses',label:'Hủy buồng',detail:'Ghi nhận hủy và tổn thất',icon:'alert',path:'losses',module:'losses'},
  {group:'Công việc ngoài Vườn',id:'fruit',label:'Đo trái',detail:'Theo dõi mẫu đo',icon:'target',path:'measurements',module:'measurements'},
  {group:'Công việc ngoài Vườn',id:'harvest',label:'Thu hoạch',detail:'Sản lượng và nguồn lô',icon:'receive',path:'harvest',module:'harvest'},
  {group:'Công việc ngoài Vườn',id:'map',label:'Bản đồ thửa',detail:'Xem vị trí ngoài vườn',icon:'map',path:'map',module:'map'},
  {group:'Xưởng và vật tư',id:'qc',label:'Kiểm tra chất lượng',detail:'Tiếp nhận và kiểm tra chuối',icon:'check-circle',path:'incoming-qc',module:'incoming-qc'},
  {group:'Xưởng và vật tư',id:'packhouse',label:'Xưởng đóng gói',detail:'Ca làm và thành phẩm',icon:'boxes',path:'packhouse',module:'packhouse'},
  {group:'Xưởng và vật tư',id:'materials',label:'Vật tư',detail:'Nhu cầu và sử dụng vật tư',icon:'cart',path:'materials',module:'materials'},
  {group:'Điều hành và báo cáo',id:'farms',label:'Vườn',detail:'Lô, thửa và vụ chuối',icon:'home',path:'farms',module:'farms'},
  {group:'Điều hành và báo cáo',id:'plans',label:'Kế hoạch',detail:'Lập và theo dõi kế hoạch',icon:'calendar',path:'plans',module:'plans'},
  {group:'Điều hành và báo cáo',id:'plan-norm',label:'Kế hoạch & định mức',detail:'Chu kỳ cây, lịch công việc và đơn giá',icon:'settings',path:'plan-norm',module:'plans'},
  {group:'Điều hành và báo cáo',id:'forecast',label:'Dự thu',detail:'Sản lượng dự kiến',icon:'chart',path:'forecast',module:'forecast'},
  {group:'Điều hành và báo cáo',id:'close',label:'Chốt ngày',detail:'Kiểm tra kết quả cuối ngày',icon:'check-circle',path:'daily-close',module:'daily-close'},
  {group:'Điều hành và báo cáo',id:'reports',label:'Báo cáo',detail:'Theo dõi và đối chiếu',icon:'document',path:'reports',capability:'home'},
  {group:'Điều hành và báo cáo',id:'alerts',label:'Cảnh báo',detail:'Điểm cần xử lý',icon:'alert',path:'alerts',module:'alerts'}
]

export function hasMobileAccess(session) {
  return !!session && (Object.values(session.modules || {}).some(types => Array.isArray(types) && types.length) || !!session.capabilities?.field || !!session.capabilities?.stock || !!session.capabilities?.hr || !!session.capabilities?.attendance || !!session.capabilities?.user_admin)
}

export function mobileActions(session) {
  if (!session) return []
  return items.filter(item =>
    (!item.module || !!session.modules?.[item.module]?.length) &&
    (!item.capability || !!session.capabilities?.[item.capability]) &&
    (!item.command || !!session.commands?.[item.command]) &&
    (!item.create || session.creatable?.[item.create] === true)
  )
}

export function mobileGroups(session) {
  const groups = new Map()
  for (const action of mobileActions(session)) {
    if (!groups.has(action.group)) groups.set(action.group, [])
    groups.get(action.group).push(action)
  }
  return [...groups].map(([title, actions]) => ({title, actions}))
}

export function mobileTabs(session) {
  const all = mobileActions(session)
  // Every tab must actually open a permitted route. Do not pin empty or unauthorized screens.
  const order = ['work','qc','packhouse','harvest','farms','materials','map','forecast','labor','alerts','reports']
  const tabs = [{id:'mobile',label:'Trang chủ',path:'mobile',icon:'home'}]
  for (const id of order) {
    const action = all.find(row => row.id === id && row.path)
    if (action && tabs.length < 4 && !tabs.some(tab => tab.path === action.path)) {
      tabs.push({id:action.id,label:action.label,path:action.path,icon:action.icon})
    }
  }
  return tabs
}

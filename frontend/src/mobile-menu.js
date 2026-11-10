// Mobile navigation is derived from real Frappe permissions, not the displayed job title.
// A user with multiple roles receives the union of the work they can actually access.
const items = [
  {group:'Quản trị',id:'users',label:'Người dùng & phân quyền',detail:'Tài khoản, vai trò và phạm vi vườn',icon:'people',href:'/lotus/nguoi-dung',capability:'user_admin'},
  {group:'Nhân sự và chấm công',id:'hr',label:'Hồ sơ nhân sự',detail:'Nhân viên, tuyển dụng và tiếp nhận',icon:'people',href:'/lotus/nhan-su',capability:'hr'},
  {group:'Nhân sự và chấm công',id:'attendance',label:'Chấm công',detail:'Công ngày, đội khoán và bảng công tháng',icon:'clock',href:'/lotus/cham-cong',capability:'attendance'},
  {group:'Công việc ngoài Vườn',id:'farm-work',label:'Việc hôm nay',detail:'Phiếu giao việc theo lô, báo cáo, nghiệm thu',icon:'check',href:'/work',capability:'field_report'},
  {group:'Xưởng và vật tư',id:'stock',label:'Quản lý kho',detail:'Tồn, nhập xuất và kiểm kê',icon:'warehouse',href:'/lotus/kho',capability:'stock'},
  {group:'Công việc ngoài Vườn',id:'map',label:'Bản đồ lô',detail:'Xem vị trí ngoài vườn',icon:'map',path:'map',module:'map'},
  {group:'Xưởng và vật tư',id:'packhouse',label:'Xưởng đóng gói',detail:'Ca làm và thành phẩm',icon:'boxes',href:'/lotus/cong-viec?field_view=packhouse',capability:'packhouse'},
  {group:'Điều hành và báo cáo',id:'farms',label:'Vườn',detail:'Khu và lô chuối',icon:'home',path:'farms',module:'farms'},
  {group:'Điều hành và báo cáo',id:'forecast',label:'Dự thu',detail:'Sản lượng dự kiến',icon:'chart',path:'forecast',module:'forecast'},
  {group:'Điều hành và báo cáo',id:'reports',label:'Báo cáo',detail:'Theo dõi và đối chiếu',icon:'document',path:'reports',capability:'home'},
  {group:'Điều hành và báo cáo',id:'alerts',label:'Cảnh báo',detail:'Điểm cần xử lý',icon:'alert',path:'alerts',module:'alerts'}
]

export function hasMobileAccess(session) {
  return !!session && (Object.values(session.modules || {}).some(types => Array.isArray(types) && types.length) || !!session.capabilities?.field_report || !!session.capabilities?.packhouse || !!session.capabilities?.stock || !!session.capabilities?.hr || !!session.capabilities?.attendance || !!session.capabilities?.user_admin)
}

export function mobileActions(session) {
  if (!session) return []
  return items.filter(item =>
    (!item.module || !!session.modules?.[item.module]?.length) &&
    (!item.capability || !!session.capabilities?.[item.capability])
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
  const order = ['farms','map','forecast','alerts','reports']
  const tabs = [{id:'mobile',label:'Trang chủ',path:'mobile',icon:'home'}]
  for (const id of order) {
    const action = all.find(row => row.id === id && row.path)
    if (action && tabs.length < 4 && !tabs.some(tab => tab.path === action.path)) {
      tabs.push({id:action.id,label:action.label,path:action.path,icon:action.icon})
    }
  }
  return tabs
}

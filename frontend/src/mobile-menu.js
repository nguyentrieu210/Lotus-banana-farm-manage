// Mobile navigation is derived from real Frappe permissions, not the displayed job title.
// A user with multiple roles receives the union of the work they can actually access.
const items = [
  {group:'Công việc ngoài vườn',id:'assign',label:'Giao việc cho tổ',detail:'Chọn lô, thửa và công việc',symbol:'↗',href:'/lotus/giao-viec',module:'work',command:'work'},
  {group:'Công việc ngoài vườn',id:'work',label:'Xem công việc',detail:'Kế hoạch và tiến độ hôm nay',symbol:'☑',path:'work',module:'work'},
  {group:'Công việc ngoài vườn',id:'actual',label:'Báo kết quả',detail:'Ghi số lượng đã làm',symbol:'✓',path:'work',module:'work',doctype:'Daily Work Result',create:'Daily Work Result'},
  {group:'Công việc ngoài vườn',id:'labor',label:'Nhân công',detail:'Bố trí và chấm công',symbol:'♙',path:'labor',module:'labor'},
  {group:'Công việc ngoài vườn',id:'disease',label:'Kiểm tra sâu bệnh',detail:'Ghi nhận tình hình vườn',symbol:'✿',path:'work',module:'work',doctype:'Disease Observation',create:'Disease Observation'},
  {group:'Công việc ngoài vườn',id:'losses',label:'Hủy buồng',detail:'Ghi nhận hủy và tổn thất',symbol:'!',path:'losses',module:'losses'},
  {group:'Công việc ngoài vườn',id:'fruit',label:'Đo trái',detail:'Theo dõi mẫu đo',symbol:'◉',path:'measurements',module:'measurements'},
  {group:'Công việc ngoài vườn',id:'harvest',label:'Thu hoạch',detail:'Sản lượng và nguồn lô',symbol:'◈',path:'harvest',module:'harvest'},
  {group:'Công việc ngoài vườn',id:'map',label:'Bản đồ thửa',detail:'Xem vị trí ngoài vườn',symbol:'⌖',path:'map',module:'map'},
  {group:'Xưởng và vật tư',id:'qc',label:'Kiểm tra chất lượng',detail:'Tiếp nhận và kiểm tra chuối',symbol:'⊙',path:'incoming-qc',module:'incoming-qc'},
  {group:'Xưởng và vật tư',id:'packhouse',label:'Xưởng đóng gói',detail:'Ca làm và thành phẩm',symbol:'▣',path:'packhouse',module:'packhouse'},
  {group:'Xưởng và vật tư',id:'materials',label:'Vật tư',detail:'Nhu cầu và sử dụng vật tư',symbol:'▤',path:'materials',module:'materials'},
  {group:'Điều hành và báo cáo',id:'farms',label:'Nông trường',detail:'Lô, thửa và vụ chuối',symbol:'⌂',path:'farms',module:'farms'},
  {group:'Điều hành và báo cáo',id:'plans',label:'Kế hoạch',detail:'Lập và theo dõi kế hoạch',symbol:'☷',path:'plans',module:'plans'},
  {group:'Điều hành và báo cáo',id:'forecast',label:'Dự thu',detail:'Sản lượng dự kiến',symbol:'▥',path:'forecast',module:'forecast'},
  {group:'Điều hành và báo cáo',id:'close',label:'Chốt ngày',detail:'Kiểm tra kết quả cuối ngày',symbol:'✓',path:'daily-close',module:'daily-close'},
  {group:'Điều hành và báo cáo',id:'reports',label:'Báo cáo',detail:'Theo dõi và đối chiếu',symbol:'▦',path:'reports',capability:'home'},
  {group:'Điều hành và báo cáo',id:'alerts',label:'Cảnh báo',detail:'Điểm cần xử lý',symbol:'!',path:'alerts',module:'alerts'}
]

export function hasMobileAccess(session) {
  return !!session && (Object.values(session.modules || {}).some(types => Array.isArray(types) && types.length) || !!session.capabilities?.field)
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
  const tabs = [{id:'mobile',label:'Trang chủ',path:'mobile',symbol:'⌂'}]
  for (const id of order) {
    const action = all.find(row => row.id === id && row.path)
    if (action && tabs.length < 4 && !tabs.some(tab => tab.path === action.path)) {
      tabs.push({id:action.id,label:action.label,path:action.path,symbol:action.symbol})
    }
  }
  return tabs
}

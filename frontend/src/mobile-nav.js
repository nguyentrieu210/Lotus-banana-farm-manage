/** Build shortcuts from capabilities returned by the backend, not the job title. */
export const has=(profile,feature)=>!!profile?.features?.includes(feature)
export function shortcuts(profile,session={}){
 const modules=session.modules||{}
 const commands=session.commands||{}
 const items=[
  {feature:'assign',name:'Giao việc',detail:'Giao nhiều việc cho một tổ',icon:'＋',url:'/lotus/giao-viec',ready:!!commands.work},
  {feature:'tasks',name:'Kế hoạch ngày',detail:'Xem, theo dõi công việc',icon:'☷',url:'/lotus/work',ready:!!modules.work?.length},
  {feature:'observation',name:'Kiểm tra vườn',detail:'Ghi nhận cây bị bệnh',icon:'✿',tab:'entry',ready:true},
  {feature:'management',name:'Vật tư',detail:'Nhu cầu và thực dùng',icon:'▣',url:'/lotus/materials',ready:!!modules.materials?.length},
  {feature:'qc',name:'Kiểm tra chất lượng',detail:'Kiểm tra đầu vào',icon:'✓',url:'/lotus/incoming-qc',ready:!!modules['incoming-qc']?.length},
  {feature:'packhouse',name:'Xưởng đóng gói',detail:'Ca và sản lượng đóng gói',icon:'▤',url:'/lotus/packhouse',ready:!!modules.packhouse?.length},
  {feature:'forecast',name:'Dự báo thu hoạch',detail:'Số lượng dự kiến',icon:'◫',url:'/lotus/forecast',ready:!!modules.forecast?.length},
  {feature:'imports',name:'Nhập dữ liệu',detail:'Kiểm tra dữ liệu từ nguồn',icon:'⇥',url:'/lotus/admin/imports',ready:!!modules.imports?.length},
 ]
 return items.filter(item=>has(profile,item.feature)&&item.ready)
}
export function taskStatus(status){
 return {Completed:'Đã hoàn thành',Planned:'Đã lên kế hoạch',Ready:'Sẵn sàng','In Progress':'Đang làm',Blocked:'Đang vướng'}[status]||status
}
export function pathWithFarm(path,farm){
 if(!farm)return path
 return path+(path.includes('?')?'&':'?')+'farm='+encodeURIComponent(farm)
}

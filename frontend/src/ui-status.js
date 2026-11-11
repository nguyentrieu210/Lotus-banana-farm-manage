// One vocabulary for document and work states (spec 004, FR-005): the same state shows the same chip
// — label, tone, icon — in every module, on desktop, phone, table cells and Excel.
// Labels for raw codes stay the existing Vietnamese captions (labels.js stateLabel), passed in by the caller,
// so this module has no dependency and fits the phone bundles. It adds the tone and the icon.
export const TONES=Object.freeze(['neutral','info','primary','success','warning','danger'])

// Kinds, in the order they are shown in the catalogue. icon = a LotusIcon name.
export const STATUS_KINDS=Object.freeze({
 draft:{label:'Nháp',tone:'neutral',icon:'edit'},
 pending:{label:'Chờ duyệt',tone:'warning',icon:'clock'},
 to_sign:{label:'Chờ ký',tone:'info',icon:'pen'},
 waiting:{label:'Đang chờ',tone:'info',icon:'clock'},
 sent:{label:'Đã gửi',tone:'info',icon:'send'},
 in_progress:{label:'Đang làm',tone:'info',icon:'progress'},
 partial:{label:'Một phần',tone:'info',icon:'progress'},
 approved:{label:'Đã duyệt',tone:'success',icon:'tick'},
 done:{label:'Đã xong',tone:'success',icon:'check-circle'},
 active:{label:'Đang hoạt động',tone:'success',icon:'dot'},
 returned:{label:'Trả lại',tone:'danger',icon:'undo'},
 reopened:{label:'Mở lại',tone:'warning',icon:'refresh'},
 cancelled:{label:'Đã hủy',tone:'neutral',icon:'ban'},
 locked:{label:'Đã khoá',tone:'neutral',icon:'lock'},
 due:{label:'Đến hạn',tone:'warning',icon:'calendar'},
 overdue:{label:'Quá hạn',tone:'danger',icon:'alert'},
 quarantine:{label:'Cách ly',tone:'danger',icon:'shield'},
 warning:{label:'Cảnh báo',tone:'warning',icon:'alert'},
 critical:{label:'Nghiêm trọng',tone:'danger',icon:'alert'},
 present:{label:'Có mặt',tone:'success',icon:'tick'},
 absent:{label:'Vắng',tone:'danger',icon:'x'},
 half_day:{label:'Nửa ngày',tone:'warning',icon:'clock'},
 on_leave:{label:'Nghỉ phép',tone:'info',icon:'calendar'},
})

// Raw codes seen in Lotus and ERPNext/HRMS documents → kind. docstatus numbers are matched as strings.
// Codes not listed here are shown as neutral chips with their own caption: never guess a tone.
const RAW=Object.freeze({
 '0':'draft',Draft:'draft',
 Pending:'pending',Hold:'pending','On Hold':'pending',Open:'pending','Pending Approval':'pending','Waiting Approval':'pending','To Approve':'pending',Unpaid:'pending',Unreconciled:'pending',
 'To Sign':'to_sign',
 'To Bill':'waiting','To Receive':'waiting','To Deliver':'waiting','To Receive and Bill':'waiting','To Deliver and Bill':'waiting',Planned:'waiting',Ready:'waiting',
 Sent:'sent',Reported:'sent',
 Doing:'in_progress','In Progress':'in_progress',Harvesting:'in_progress',
 'Partly Paid':'partial','Partly Paid and Discounted':'partial','Partially Received':'partial','Partially Ordered':'partial','Partly Reconciled':'partial',
 '1':'approved',Submitted:'approved',Approved:'approved',Released:'approved',Confirmed:'approved',Acknowledged:'approved',Ordered:'approved',
 Completed:'done',Done:'done',Accepted:'done',Closed:'done',Paid:'done',Delivered:'done',Received:'done',Reconciled:'done',Resolved:'done',Passed:'done',Pass:'done',Issued:'done',Transferred:'done',
 Active:'active',
 Rejected:'returned',Returned:'returned',Rework:'returned',Failed:'returned',Fail:'returned',Block:'returned',Lost:'returned',
 Reopened:'reopened',
 '2':'cancelled',Cancelled:'cancelled',Voided:'cancelled',Superseded:'cancelled',Stopped:'cancelled',Expired:'cancelled',Ended:'cancelled',
 Locked:'locked',
 Due:'due',Overdue:'overdue',Quarantine:'quarantine',
 Warning:'warning',Critical:'critical',Blocked:'critical',
 Present:'present',Absent:'absent','Half Day':'half_day','On Leave':'on_leave',
})

export const statusKind=code=>code==null||code===''?null:RAW[String(code)]||(STATUS_KINDS[code]?String(code):null)

// {code, kind, label, tone, icon}. label: the caller's caption (e.g. stateLabel(code)) when it differs from the raw code,
// else the kind's label, else the code itself. Unknown codes: tone neutral, no icon.
export function statusMeta(code,label){
 const kind=statusKind(code),meta=kind?STATUS_KINDS[kind]:null
 const own=label!=null&&label!==''&&String(label)!==String(code)?String(label):''
 return {code,kind,label:own||meta?.label||(code==null?'':String(code)),tone:meta?.tone||'neutral',icon:meta?.icon||''}
}

// Days until a date (local calendar days; negative = past). today/target: Date | 'YYYY-MM-DD'.
const dayNumber=value=>{
 if(value instanceof Date)return Math.floor(Date.UTC(value.getFullYear(),value.getMonth(),value.getDate())/864e5)
 const m=String(value||'').match(/^(\d{4})-(\d{2})-(\d{2})/)
 return m?Math.floor(Date.UTC(+m[1],+m[2]-1,+m[3])/864e5):null
}
export function daysBetween(today,target){
 const a=dayNumber(today),b=dayNumber(target)
 return a==null||b==null?null:b-a
}

// A due date read as a state: not yet due (n days left), due today / within `soon` days, or overdue by n days.
export function dueState(target,today,{soon=0}={}){
 const days=daysBetween(today,target)
 if(days==null)return null
 if(days<0)return {kind:'overdue',days,label:`Quá ${-days} ngày`,tone:'danger',icon:'alert'}
 if(days===0)return {kind:'due',days,label:'Đến hạn hôm nay',tone:'warning',icon:'calendar'}
 if(days<=soon)return {kind:'due',days,label:`Còn ${days} ngày`,tone:'warning',icon:'calendar'}
 return {kind:'upcoming',days,label:`Còn ${days} ngày`,tone:'neutral',icon:'calendar'}
}

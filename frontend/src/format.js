// Vietnamese date display shared by desktop and PWA. Inputs are Frappe ISO strings (YYYY-MM-DD[ HH:mm:ss]);
// UTC keeps the calendar day unchanged whatever the device timezone.
const dayFormat=new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'})
const parts=value=>/^(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(String(value||''))
export function formatDate(value,empty='—'){
 const m=parts(value);if(!m||!m[3])return value?String(value):empty
 return dayFormat.format(Date.UTC(+m[1],+m[2]-1,+m[3]))
}
export function formatMonthShort(value,empty='—'){
 const m=parts(value);if(!m)return value?String(value):empty
 // compact axis label: MM/YY (Intl vi-VN would print 'tháng 03, 26')
 return m[2]+'/'+m[1].slice(2)
}

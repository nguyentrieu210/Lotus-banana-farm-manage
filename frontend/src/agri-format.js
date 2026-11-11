// Farm formatting shared by the agritech components (spec 004): ISO weeks, numbers with units, short dates.
// Pure functions, no dependency, used on desktop and in the phone PWAs.

const toUtcDay=value=>{
 if(value instanceof Date)return new Date(Date.UTC(value.getFullYear(),value.getMonth(),value.getDate()))
 const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(String(value||''))
 return m?new Date(Date.UTC(+m[1],+m[2]-1,+m[3])):null
}

// ISO 8601 week: weeks start on Monday; week 1 holds the year's first Thursday. 2026 has 53 weeks.
export function isoWeek(value){
 const d=toUtcDay(value)
 if(!d)return null
 const day=d.getUTCDay()||7
 d.setUTCDate(d.getUTCDate()+4-day)
 const year=d.getUTCFullYear(),start=Date.UTC(year,0,1)
 return {year,week:Math.ceil(((d-start)/864e5+1)/7)}
}
// Monday of an ISO week, as 'YYYY-MM-DD'.
export function isoWeekMonday(year,week){
 const jan4=new Date(Date.UTC(year,0,4)),day=jan4.getUTCDay()||7
 const monday=new Date(jan4);monday.setUTCDate(jan4.getUTCDate()-day+1+(week-1)*7)
 return monday.toISOString().slice(0,10)
}
export const weeksInYear=year=>isoWeek(`${year}-12-28`).week
// Step n ISO weeks forward (or back) from {year, week}.
export function addWeeks({year,week},n){
 const monday=toUtcDay(isoWeekMonday(year,week))
 monday.setUTCDate(monday.getUTCDate()+7*n)
 return isoWeek(monday)
}
// 'T46' (short) or 'Tuần 46/2026'.
export const weekLabel=({year,week},{short=false}={})=>short?`T${week}`:`Tuần ${week}/${year}`
// 'Tuần 46: 09/11 – 15/11'
export function weekRange({year,week}){
 const monday=toUtcDay(isoWeekMonday(year,week)),sunday=new Date(monday);sunday.setUTCDate(monday.getUTCDate()+6)
 const dm=d=>String(d.getUTCDate()).padStart(2,'0')+'/'+String(d.getUTCMonth()+1).padStart(2,'0')
 return `${dm(monday)} – ${dm(sunday)}`
}
export const sameWeek=(a,b)=>!!a&&!!b&&a.year===b.year&&a.week===b.week
// '2026-W46': the key used for per-week maps (harvest weeks, ribbons cut, forecast values).
export const weekKey=w=>w.year+'-W'+String(w.week).padStart(2,'0')

// Numbers in Vietnamese style: 9.328 and 3,96. null/undefined/'' → null (callers show '—', never 0).
export function formatNumber(value,{digits=0,min=0}={}){
 if(value===null||value===undefined||value==='')return null
 const n=Number(value)
 if(!Number.isFinite(n))return null
 return n.toLocaleString('vi-VN',{minimumFractionDigits:min,maximumFractionDigits:digits})
}
// Signed change: '+12', '−3,5' (true minus sign), '0'.
export function formatDelta(value,{digits=0}={}){
 const text=formatNumber(Math.abs(Number(value)),{digits})
 if(text===null)return null
 const n=Number(value)
 return n>0?'+'+text:n<0?'−'+text:text
}
// dd/mm
export function shortDate(value){
 const d=toUtcDay(value)
 return d?String(d.getUTCDate()).padStart(2,'0')+'/'+String(d.getUTCMonth()+1).padStart(2,'0'):''
}
// Initials for an avatar: last two words of a Vietnamese name ("Nguyễn Văn An" → "VA").
export function initials(name){
 const words=String(name||'').trim().split(/\s+/).filter(Boolean)
 if(!words.length)return ''
 const pick=words.length>1?words.slice(-2):words
 return pick.map(w=>w[0]).join('').toUpperCase()
}

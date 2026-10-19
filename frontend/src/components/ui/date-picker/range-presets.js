import {parseDate,startOfMonth,endOfMonth,startOfWeek,endOfWeek} from '@internationalized/date'
// Quick ranges for report filters. range(todayISO) -> [fromISO,toISO]; weeks start on Monday (vi-VN).
const day=text=>parseDate(text)
export const rangePresets=[
 {id:'today',label:'Hôm nay',range:t=>[t,t]},
 {id:'7d',label:'7 ngày qua',range:t=>[day(t).subtract({days:6}).toString(),t]},
 {id:'week',label:'Tuần này',range:t=>[startOfWeek(day(t),'vi-VN').toString(),endOfWeek(day(t),'vi-VN').toString()]},
 {id:'month',label:'Tháng này',range:t=>[startOfMonth(day(t)).toString(),endOfMonth(day(t)).toString()]},
 {id:'last-month',label:'Tháng trước',range:t=>{const m=startOfMonth(day(t)).subtract({months:1});return [m.toString(),endOfMonth(m).toString()]}},
 {id:'30d',label:'30 ngày qua',range:t=>[day(t).subtract({days:29}).toString(),t]},
]

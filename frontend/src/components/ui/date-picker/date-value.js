import {parseDate,today,getLocalTimeZone} from '@internationalized/date'
// Frappe stores dates as 'YYYY-MM-DD'; reka pickers work with CalendarDate. Invalid/empty -> undefined.
export function toCalendarDate(value){
 const text=String(value||'').slice(0,10)
 if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return undefined
 try{return parseDate(text)}catch{return undefined}
}
export function fromCalendarDate(date){return date?date.toString():''}
export function formatDateInput(value){
 const date=toCalendarDate(value)
 return date?`${String(date.day).padStart(2,'0')}/${String(date.month).padStart(2,'0')}/${String(date.year).padStart(4,'0')}`:''
}
export function parseDateInput(value){
 const match=String(value||'').trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
 if(!match||Number(match[3])<1)return ''
 const iso=`${match[3]}-${match[2].padStart(2,'0')}-${match[1].padStart(2,'0')}`
 return toCalendarDate(iso)?iso:''
}
export function todayValue(){return today(getLocalTimeZone()).toString()}

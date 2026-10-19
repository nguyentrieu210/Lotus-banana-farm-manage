import {parseDate,today,getLocalTimeZone} from '@internationalized/date'
// Frappe stores dates as 'YYYY-MM-DD'; reka pickers work with CalendarDate. Invalid/empty -> undefined.
export function toCalendarDate(value){
 const text=String(value||'').slice(0,10)
 if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return undefined
 try{return parseDate(text)}catch{return undefined}
}
export function fromCalendarDate(date){return date?date.toString():''}
export function todayValue(){return today(getLocalTimeZone()).toString()}

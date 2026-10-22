// Lotus farms use Vietnam local calendar dates. Keep invalid persisted filters out of date arithmetic.
export function isISODate(value){
 const text=String(value||'')
 if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return false
 const date=new Date(text+'T00:00:00Z')
 return !Number.isNaN(date.getTime())&&date.toISOString().slice(0,10)===text
}
export function lotusToday(){
 return new Date(Date.now()+7*60*60*1000).toISOString().slice(0,10)
}
export function safeLotusDate(...values){
 return values.find(isISODate)||lotusToday()
}
export function lotusDateMinus(value,days){
 const date=new Date(safeLotusDate(value)+'T00:00:00Z')
 date.setUTCDate(date.getUTCDate()-days)
 return date.toISOString().slice(0,10)
}
export function lotusDatePlus(value,days){
 return lotusDateMinus(value,-days)
}

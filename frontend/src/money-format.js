// Money typed and shown the Vietnamese way: 1.250.000 (thousands with ".", decimals after ","). Values stay plain numbers.
export function formatMoneyInput(value){
 if(value===''||value==null||Number.isNaN(Number(value)))return ''
 const [whole,fraction]=String(value).split('.')
 const grouped=whole.replace(/^(-?)(\d+)$/,(m,sign,digits)=>sign+digits.replace(/\B(?=(\d{3})+(?!\d))/g,'.'))
 return fraction!==undefined?grouped+','+fraction:grouped
}
// Typed or pasted text → number ('' while empty). Accepts every way people write a number here:
//  "26.571.428,571" (Vietnamese) · "26,571,428.571" (English, pasted from invoices) · "531428,57" · "531428.57" (numpad dot).
//  Both separators: the last one starts the decimals. Only ",": one comma = decimals, several = thousands.
//  Only ".": groups of exactly 3 digits are thousands ("1.250.000"), otherwise the last dot starts the decimals ("996.4").
export function parseMoneyInput(text){
 let s=String(text??'').replace(/[^\d,.-]/g,'')
 const negative=s.startsWith('-')
 s=s.replace(/-/g,'')
 if(!s)return ''
 const commas=(s.match(/,/g)||[]).length,dots=(s.match(/\./g)||[]).length
 const thousands=sep=>s.split(sep).slice(1).every(group=>group.length===3)
 let decimal=-1
 if(commas&&dots)decimal=Math.max(s.lastIndexOf(','),s.lastIndexOf('.'))
 else if(commas)decimal=commas===1||!thousands(',')?s.lastIndexOf(','):-1
 else if(dots)decimal=thousands('.')?-1:s.lastIndexOf('.')
 const whole=(decimal<0?s:s.slice(0,decimal)).replace(/[.,]/g,'')
 const fraction=decimal<0?'':s.slice(decimal+1).replace(/[.,]/g,'')
 if(!whole&&!fraction)return ''
 const number=Number((negative?'-':'')+(whole||'0')+(fraction?'.'+fraction:''))
 return Number.isFinite(number)?number:''
}
// While typing the text stays exactly as typed (only foreign characters are dropped), so a "." or "," the user is
// still completing is never re-interpreted halfway; the field shows the grouped form again when it loses focus.
export function reformatMoneyInput(element){
 const before=element.value,caret=element.selectionStart??before.length
 const clean=before.replace(/[^\d,.\s-]/g,'')
 if(clean!==before){
  element.value=clean
  const position=Math.max(0,caret-(before.length-clean.length))
  try{element.setSelectionRange(position,position)}catch{}
 }
 return parseMoneyInput(clean)
}

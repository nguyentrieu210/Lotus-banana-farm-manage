// Money typed and shown the Vietnamese way: 1.250.000 (thousands with ".", decimals after ","). Values stay plain numbers.
export function formatMoneyInput(value){
 if(value===''||value==null||Number.isNaN(Number(value)))return ''
 const [whole,fraction]=String(value).split('.')
 const grouped=whole.replace(/^(-?)(\d+)$/,(m,sign,digits)=>sign+digits.replace(/\B(?=(\d{3})+(?!\d))/g,'.'))
 return fraction!==undefined?grouped+','+fraction:grouped
}
// Typed text → number ('' while empty). "." groups thousands, "," starts the decimals; a lone trailing "," is kept for typing.
export function parseMoneyInput(text){
 const clean=String(text??'').replace(/[^\d,.-]/g,'').replace(/\./g,'')
 if(!clean||clean==='-')return ''
 const [whole,...rest]=clean.split(',')
 const number=Number(whole+(rest.length?'.'+rest.join(''):''))
 return Number.isFinite(number)?number:''
}
// Re-format while typing and keep the caret after the same number of digits.
export function reformatMoneyInput(element){
 const before=element.value,caret=element.selectionStart??before.length
 const significant=text=>text.replace(/[^\d,]/g,'')
 const keep=significant(before.slice(0,caret)).length
 const value=parseMoneyInput(before)
 const comma=before.indexOf(',')
 // Group the whole part; keep the decimals exactly as typed (including a trailing ",").
 let text=value===''?'':formatMoneyInput(Math.trunc(value))
 if(comma>=0)text=(text||'0')+','+before.slice(comma+1).replace(/\D/g,'')
 element.value=text
 let seen=0,position=0
 while(position<text.length&&seen<keep){if(/[\d,]/.test(text[position]))seen++;position++}
 try{element.setSelectionRange(position,position)}catch{}
 return value
}

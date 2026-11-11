// Ribbon (màu dây) colours (spec 004, FR-031). The Bunch Tag catalogue stores codes — DO, CAM, XANH_LA,
// two-colour XANH_LA_DO… — not CSS colours. Each base colour is a token in lotus-tokens.css, so light, dark
// and outdoor modes stay consistent. --lotus-ribbon-outline keeps Trắng and Đen visible on any surface.
export const RIBBON_COLOURS=Object.freeze({
 DO:{label:'Đỏ',token:'--lotus-ribbon-do'},
 TRANG:{label:'Trắng',token:'--lotus-ribbon-trang'},
 TIM:{label:'Tím',token:'--lotus-ribbon-tim'},
 CAM:{label:'Cam',token:'--lotus-ribbon-cam'},
 DEN:{label:'Đen',token:'--lotus-ribbon-den'},
 XANH_DUONG:{label:'Xanh dương',token:'--lotus-ribbon-xanh-duong'},
 XANH_LA:{label:'Xanh lá',token:'--lotus-ribbon-xanh-la'},
})
export const RIBBON_OUTLINE='var(--lotus-ribbon-outline)'
const KEYS=Object.keys(RIBBON_COLOURS).sort((a,b)=>b.length-a.length)
const isCss=code=>/^(#|rgb|hsl)/i.test(String(code||'').trim())

// 'XANH_LA_DO' → [{key:'XANH_LA',label:'Xanh lá',colour:'var(--lotus-ribbon-xanh-la)'},{key:'DO',…}].
// A raw CSS colour stored in old rows is passed through as one part. Unknown codes → [].
export function ribbonParts(code){
 if(!code)return []
 if(isCss(code))return [{key:'',label:'',colour:String(code).trim()}]
 // Codes, and Vietnamese names typed by hand ('Xanh lá', 'Đỏ') both resolve.
 let rest=String(code).trim().toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/Đ/g,'D').replace(/[\s-]+/g,'_')
 const parts=[]
 while(rest){
  const key=KEYS.find(k=>rest===k||rest.startsWith(k+'_'))
  if(!key)return []
  parts.push({key,label:RIBBON_COLOURS[key].label,colour:`var(${RIBBON_COLOURS[key].token})`})
  rest=rest.slice(key.length).replace(/^_/,'')
 }
 return parts
}

// 'Xanh lá – Đỏ'. Empty for unknown codes.
export const ribbonLabel=code=>ribbonParts(code).map(p=>p.label).filter(Boolean).join(' – ')

// CSS background for a swatch: one colour, or two halves side by side. 'transparent' for unknown codes.
export function ribbonBackground(code){
 const parts=ribbonParts(code)
 if(!parts.length)return 'transparent'
 if(parts.length===1)return parts[0].colour
 const step=100/parts.length
 return `linear-gradient(90deg,${parts.map((p,i)=>`${p.colour} ${i*step}% ${(i+1)*step}%`).join(',')})`
}

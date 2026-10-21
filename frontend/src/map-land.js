// How a lot is coloured on the land map (pure, tested in tests/map-land.test.js).
// zone: the zone palette; variety: one fixed colour per variety in sorted order (never cycled by rank);
// density / flowering: one hue light -> dark. A lot without the value is grey and listed as "chưa có".
const ZONES=['A','B','C','D','E','F']
// Same palette as map-zones.zoneColor (kept import-free so it runs in node tests).
const zoneColor=zone=>`var(--lotus-map-zone-${ZONES.includes(zone)?zone.toLowerCase():'a'})`

export const COLOR_MODES=[['zone','Theo khu'],['variety','Theo giống'],['density','Theo mật độ cây'],['flowering','Theo tháng trổ dự kiến']]
const MISSING='var(--lotus-neutral-300)'
const DENSITY_EDGES=[1500,1800,2100,2400]
const DENSITY_STEPS=['var(--lotus-success-100)','var(--lotus-success-300)','var(--lotus-success-500)','var(--lotus-success-700)','var(--lotus-success-900)']
const MONTH_STEPS=['var(--lotus-info-200)','var(--lotus-info-400)','var(--lotus-info-600)','var(--lotus-info-800)']
const CATEGORY=['a','b','c','d','e','f'].map(z=>`var(--lotus-map-zone-${z})`)

function densityStep(value){return value==null?null:DENSITY_EDGES.filter(edge=>value>=edge).length}

// Months ahead of `today` (0 = this month); past months count as 0.
function monthsAhead(month,today){
 if(!month)return null
 const [y,m]=month.split('-').map(Number),[ty,tm]=today.slice(0,7).split('-').map(Number)
 return Math.max(0,(y-ty)*12+(m-tm))
}

export function fillFor(props,mode,context={}){
 if(mode==='variety'){const i=(context.varieties||[]).indexOf(props.variety);return i<0?MISSING:CATEGORY[i%CATEGORY.length]}
 if(mode==='density'){const step=densityStep(props.density);return step==null?MISSING:DENSITY_STEPS[step]}
 if(mode==='flowering'){const ahead=monthsAhead(props.flowering_month,context.today||new Date().toISOString().slice(0,10));return ahead==null?MISSING:MONTH_STEPS[Math.min(ahead,MONTH_STEPS.length-1)]}
 return zoneColor(props.zone)
}

export function legendFor(mode,context={}){
 if(mode==='variety')return [...(context.varieties||[]).map((v,i)=>({label:v,color:CATEGORY[i%CATEGORY.length]})),{label:'Chưa có giống',color:MISSING}]
 if(mode==='density')return [{label:'< 1.500 cây/ha',color:DENSITY_STEPS[0]},{label:'1.500–1.799',color:DENSITY_STEPS[1]},{label:'1.800–2.099',color:DENSITY_STEPS[2]},{label:'2.100–2.399',color:DENSITY_STEPS[3]},{label:'≥ 2.400',color:DENSITY_STEPS[4]},{label:'Chưa đếm cây',color:MISSING}]
 if(mode==='flowering')return [{label:'Tháng này',color:MONTH_STEPS[0]},{label:'Tháng sau',color:MONTH_STEPS[1]},{label:'2 tháng nữa',color:MONTH_STEPS[2]},{label:'3+ tháng nữa',color:MONTH_STEPS[3]},{label:'Chưa có ngày trổ',color:MISSING}]
 return null
}

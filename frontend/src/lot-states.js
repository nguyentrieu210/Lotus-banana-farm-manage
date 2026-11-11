// Lot states for lot cards and the lot grid (spec 004, FR-029, FR-030). Each state has a label, an icon and a fill
// token (--lotus-lot-<state>), so a state never depends on colour alone (FR-008). Pure data, used on desktop and phone.
export const LOT_STATES=Object.freeze({
 empty:{label:'Chưa nhập',icon:''},
 entered:{label:'Đã nhập, chưa gửi',icon:'edit'},
 sent:{label:'Đã gửi',icon:'send'},
 confirmed:{label:'Đã xác nhận',icon:'tick'},
 ok:{label:'Chưa đến hạn',icon:'tick'},
 due:{label:'Đến hạn',icon:'clock'},
 overdue:{label:'Quá hạn',icon:'alert'},
 quarantine:{label:'Đang cách ly',icon:'shield'},
})

// The lot grid can colour the farm by one metric at a time; each metric uses a fixed subset of states, in legend order.
export const LOT_METRICS=Object.freeze({
 report:{label:'Báo cáo hôm nay',states:['empty','entered','sent','confirmed']},
 care:{label:'Đến hạn chăm sóc',states:['ok','due','overdue']},
 harvest:{label:'Đến tuổi thu',states:['empty','ok','due']},
 quarantine:{label:'Cách ly thuốc',states:['ok','quarantine']},
})

// A lot code's zone: 'A5' → 'A'. Zones A–F map to the six fixed map colours.
export const zoneOf=code=>{const m=/^([A-Za-z])/.exec(String(code||''));return m?m[1].toUpperCase():''}
export const zoneColour=zone=>{const z=String(zone||'').toLowerCase();return /^[a-f]$/.test(z)?`var(--lotus-map-zone-${z})`:'var(--lotus-border-strong)'}

// Natural order for lot codes: A2 before A10.
export function compareLotCodes(a,b){
 const pa=/^([A-Za-z]*)(\d*)(.*)$/.exec(String(a)),pb=/^([A-Za-z]*)(\d*)(.*)$/.exec(String(b))
 return pa[1].localeCompare(pb[1])||(Number(pa[2]||0)-Number(pb[2]||0))||pa[3].localeCompare(pb[3])
}

// Group lots by zone, sorted, with a count per state for the legend.
export function groupLots(lots){
 const zones=new Map(),counts={}
 for(const lot of lots){
  const zone=lot.zone||zoneOf(lot.code)
  if(!zones.has(zone))zones.set(zone,[])
  zones.get(zone).push(lot)
  counts[lot.state]=(counts[lot.state]||0)+1
 }
 const groups=[...zones.entries()].sort(([a],[b])=>String(a).localeCompare(String(b))).map(([zone,items])=>({zone,lots:items.sort((x,y)=>compareLotCodes(x.code,y.code))}))
 return {groups,counts}
}

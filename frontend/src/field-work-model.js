// Công việc ngoài vườn: phiếu giao việc theo lô (lotus_farm.field_report). Pure helpers shared by the desktop workspace
// and the /work phone app: labels, the money preview of a phiếu and the lô × việc board. Day reports live in
// lot-entry-model.js. The server stays the authority on every number.
export const groups={Bunch:'Chăm sóc buồng',Field:'Việc vườn',Protection:'BVTV / phân bón'}
export const payModes={Count:'Khoán số lượng',Lot:'Khoán lô (nghiệm thu)',Daywork:'Công nhật'}
export const payShort={Count:'Khoán SL',Lot:'Khoán lô',Daywork:'Công nhật'}
export const capBases={CutBud:'Số buồng đã cắt bắp cùng màu',LotTrees:'Số cây của lô',LotArea:'Diện tích lô',None:'Không giới hạn'}
export const states={Open:'Đang làm',Assigned:'Đã giao',Working:'Đang làm',Late:'Quá hạn',Reported:'Tổ báo xong',Approved:'Chờ nghiệm thu',
 Passed:'Đạt',Failed:'Không đạt – làm lại',Locked:'Đã khoá, tính tiền',Cancelled:'Đã huỷ',Done:'Xong',Ended:'Hết giao'}
export const stateTone={Assigned:'neutral',Working:'info',Open:'info',Late:'danger',Reported:'warning',Approved:'warning',
 Passed:'success',Failed:'danger',Locked:'success',Cancelled:'muted'}
export const unitText=(uom,basis)=>basis==='Area'?'ha':basis==='Trees'?'cây':uom||''
export const money=v=>Math.round(Number(v||0)).toLocaleString('vi-VN')+' đ'
export const amountText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})

export function wholeLot(ticket){
 if(ticket?.basis==='Area')return Number(ticket.lot_area_ha||0)
 if(ticket?.basis==='Trees')return Number(ticket.lot_trees||0)
 return null
}
// Same rule as field_report_rules.pay_amount: counted work pays what was reported, khoán lô the whole lô once it passes.
export function previewAmount(ticket,qtyTotal){
 if(ticket?.pay_mode==='Count')return Math.round(Number(qtyTotal||0)*Number(ticket.rate||0))
 if(ticket?.pay_mode==='Lot')return Math.round(Number(wholeLot(ticket)||0)*Number(ticket.rate||0))
 return 0
}
// Lô × việc: one row per lô, one key per việc holding the phiếu of that cell (latest first).
export function boardRows(board){
 const rows=(board?.blocks||[]).map(b=>({...b,key:b.name,cells:{}}))
 const by=Object.fromEntries(rows.map(r=>[r.name,r]))
 for(const c of board?.cells||[]){
  const row=by[c.farm_block];if(!row)continue
  ;(row.cells[c.work_type]||=[]).push(c)
 }
 for(const r of rows)for(const list of Object.values(r.cells))list.sort((a,b)=>String(b.assigned_on).localeCompare(String(a.assigned_on)))
 return rows
}

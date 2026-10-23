export const assetSections=[
 {id:'assets',label:'Tài sản',icon:'boxes'},
 {id:'categories',label:'Nhóm tài sản',icon:'list'},
 {id:'locations',label:'Vị trí',icon:'map'},
 {id:'accounts',label:'Tài khoản',icon:'document'},
 {id:'depreciation',label:'Khấu hao',icon:'calendar'},
 {id:'operations',label:'Biến động',icon:'transfer'},
 {id:'report',label:'Báo cáo',icon:'chart'},
]
export const assetView=value=>assetSections.some(s=>s.id===value)?value:'assets'
export const searchable=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll('đ','d').replaceAll('Đ','D').toLowerCase()
export const matches=(row,query,fields)=>!query||searchable(fields.map(k=>row[k]??'').join(' ')).includes(searchable(query))
export function registerRows(data={}){
 return [
  ...(data.pending_assets||[]).map(row=>({...row,row_key:'operation:'+row.operation,pending:true})),
  ...(data.assets||[]).map(row=>({...row,row_key:'asset:'+row.name,pending:false})),
 ]
}
export const assetStatus=row=>row.pending?'Pending':row.docstatus===2?'Cancelled':row.lotus_usage_suspended?'Suspended':row.status
export function filterRegister(rows,query,filters={}){
 return rows.filter(row=>matches(row,query,['lotus_asset_code','asset_name','lotus_serial_no'])&&
  (!filters.category||row.asset_category===filters.category)&&(!filters.location||row.location===filters.location)&&
  (!filters.farm||row.lotus_farm===filters.farm)&&(!filters.status||assetStatus(row)===filters.status))
}

// Display only: do not change ERPNext document states.
export function purchaseOrderStatus(order={}){
 if(order.docstatus===2)return 'Đã hủy'
 if(order.status==='Đã đóng'||order.status==='Closed')return 'Đã đóng'
 if(order.status==='Đã nhận đủ'||order.status==='Completed')return 'Đã nhận đủ'
 if(order.status==='Quá hẹn')return 'Quá hẹn'
 if(order.status==='Về một phần')return 'Về một phần'
 if(order.docstatus===0)return order.approval_status||'Nháp'
 if(order.status==='Chờ hàng')return 'Chờ giao'
 return order.approval_status||order.status||'Nháp'
}
export function purchaseStatusTone(order){
 const status=purchaseOrderStatus(order)
 return ({
  'Nháp':'draft','Chờ duyệt':'pending','Từ chối':'rejected',
  'Đã duyệt':'approved','Chờ giao':'approved','Đã nhận đủ':'done',
  'Về một phần':'partial','Quá hẹn':'late','Đã đóng':'closed','Đã hủy':'cancelled'
 })[status]||'draft'
}

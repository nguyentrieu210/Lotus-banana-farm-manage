// Display only: the server computes the status (lotus_farm.purchase_status.order_state, spec 003 FR-003);
// names stored or cached by older releases are mapped to the one vocabulary.
import {purchaseState,stateTone} from './purchase-status.js'
export function purchaseOrderStatus(order={}){
 if(order.docstatus===2)return 'Đã hủy'
 if(order.status==='Closed')return 'Đã đóng'
 if(order.status==='Completed')return 'Đã nhận đủ'
 return purchaseState('order',order.status||order.approval_status)||'Nháp'
}
// Late delivery is a flag beside the status: the chip turns red, the text stays the status.
export function purchaseStatusTone(order={}){
 return order.overdue?'late':stateTone(purchaseOrderStatus(order))
}
export const purchaseOrderLate=order=>!!order?.overdue||order?.status==='Quá hẹn'

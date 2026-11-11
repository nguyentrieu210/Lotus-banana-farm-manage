// One status vocabulary for purchase documents (spec 003, FR-003); mirrors lotus_farm/purchase_status.py
// and lotus_farm/proposal_rules.py. Display only: the server computes the status, screens show it and pick a tone.
export const PROPOSAL_STAGES=['Nháp','Đang ký','Bị trả lại','Chờ mua','Đang mua','Đã nhận đủ','Đã xong','Đã hủy']
export const ORDER_STATES=['Nháp','Chờ duyệt','Bị trả lại','Đã duyệt','Đã gửi NCC','NCC đã xác nhận','Đang nhận','Đã nhận đủ','Đã đóng','Đã hủy']
export const RECEIPT_STATES=['Nháp','Đã nhập kho','Đã hủy']
export const BILLING_STATES=['Chưa có hóa đơn','Có hóa đơn một phần','Đã có hóa đơn','Đã trả hết hàng']
export const INVOICE_STATES=['Chưa trả','Trả một phần','Đã trả','Quá hạn','Đã hủy']
export const VOUCHER_STATES=['Nháp','Đang ký','Bị trả lại','Đã chi','Đã đảo']
export const QUOTE_STATES=['Nháp','Đã xác nhận','Đã chọn','Đã hủy']
export const QUICK_PURCHASE='Mua nhanh'

// Names older releases stored or returned, per kind of document.
const LEGACY={
 proposal:{'Trả lại':'Bị trả lại','Chờ ký':'Đang ký','Đã duyệt chờ mua':'Chờ mua','Đã duyệt':'Chờ mua','Hoàn tất':'Đã xong'},
 order:{'Từ chối':'Bị trả lại','Trả lại':'Bị trả lại','Chờ giao':'Đã duyệt','Chờ hàng':'Đã duyệt','Về một phần':'Đang nhận'},
 receipt:{'Đã ghi sổ':'Đã nhập kho','Đã xác nhận':'Đã nhập kho'},
 voucher:{'Chờ ký':'Đang ký','Nháp / chờ ký':'Đang ký','Đã ghi sổ':'Đã chi','Đã trả':'Đã chi'},
}
export function purchaseState(kind,label){
 const text=String(label??'').trim()
 return LEGACY[kind]?.[text]||text
}

// Tones reuse the existing chip classes (buy-order-status--<tone>, pp-state is-<tone>).
const TONES={
 'Nháp':'draft','Đang ký':'pending','Chờ duyệt':'pending','Bị trả lại':'rejected',
 'Chờ mua':'approved','Đã duyệt':'approved','Đã gửi NCC':'approved','NCC đã xác nhận':'approved','Đã xác nhận':'approved','Đã chọn':'approved',
 'Đang mua':'partial','Đang nhận':'partial','Trả một phần':'partial','Có hóa đơn một phần':'partial',
 'Đã nhận đủ':'done','Đã xong':'done','Đã nhập kho':'done','Đã trả':'done','Đã chi':'done','Đã có hóa đơn':'done',
 'Chưa trả':'pending','Chưa có hóa đơn':'pending','Quá hạn':'late','Quá hẹn':'late',
 'Đã đóng':'closed','Đã đảo':'closed','Đã trả hết hàng':'closed','Đã hủy':'cancelled',
}
export function stateTone(label){return TONES[String(label??'').trim()]||'draft'}

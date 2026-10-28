// Display defaults for the shared DataTable: plain numeric columns get Vietnamese digit grouping,
// and quantity columns know which column holds their unit (so the sum row never adds kg to litres).
const NOT_GROUPED_FIELD=/(^|_)(year|code|no|idx|id|stt|phone|zip|tax_id|pin)(_|$)/i
const NOT_GROUPED_LABEL=/^(năm|mã|stt|số thứ tự|số điện thoại|điện thoại|mã số thuế)(\s|$)/i
const QTY_FIELD=/(^|_)(qty|quantity)(_|$)/i
const QTY_LABEL=/^(sl|số lượng|khối lượng|lượng)(\s|$)/i
const UNIT_FIELD=/(^|_)(uom|unit|dvt)$/i
const UNIT_LABEL=/^(đvt|đơn vị)(\s|$)/i
export const groupNumber=value=>value.toLocaleString('vi-VN',{maximumFractionDigits:3})
// Only columns that would otherwise print a raw JavaScript number (802.92, 3651163.508).
export function numberFormatter(col){
 if(col.valueFormatter||col.cellRenderer||col.cellRendererSelector||col.groupNumbers===false)return null
 if(NOT_GROUPED_FIELD.test(String(col.field||col.colId||''))||NOT_GROUPED_LABEL.test(String(col.headerName||'')))return null
 return p=>typeof p.value==='number'&&Number.isFinite(p.value)?groupNumber(p.value):p.value
}
// The column holding a quantity column's unit: col.unitField, else a ĐVT/uom column (stock_qty pairs with stock_uom).
export function unitColumn(col,columns=[]){
 const id=c=>c.colId||c.field||c.headerName
 if(col.unitField)return columns.find(c=>id(c)===col.unitField)||{field:col.unitField}
 const field=String(col.field||col.colId||'')
 if(!QTY_FIELD.test(field)&&!QTY_LABEL.test(String(col.headerName||'')))return null
 const units=columns.filter(c=>c!==col&&(UNIT_FIELD.test(String(c.field||''))||UNIT_LABEL.test(String(c.headerName||''))))
 const prefix=field.includes('_')?field.split('_')[0]+'_':null
 return (prefix&&units.find(c=>String(c.field||'').startsWith(prefix)))||units[0]||null
}
// A column with nothing in any row (not even 0) is hidden until the user turns it back on.
export function emptyColumn(col,rows,raw){
 if(!rows.length||col.autoHide===false||col.cellRenderer||col.cellRendererSelector)return false
 return rows.every(row=>{const v=raw(row,col);return v===null||v===undefined||v===''||v==='—'})
}

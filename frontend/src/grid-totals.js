// Sum row for the shared DataTable. A column is summed when it says sum:true, or when every filled value is a number
// and the column is not a price, rate, running balance, code or date-like figure.
const NOT_ADDITIVE=/đơn giá|giá thành|giá bán|giá mua|^giá(?! trị)|tỷ lệ|tỉ lệ|%|\/ ?(kg|ha|buồng|cây|tháng|ngày)|bình quân|trung bình|số dư|lũy kế|luỹ kế|sau giao dịch|tồn sau|mã|stt|số thứ tự|hệ số|định mức|điểm|hạng|thứ tự|tối thiểu|tối đa|mức|trạng thái|tình trạng|^(năm|tháng|kỳ|tuần|vụ|tuổi)(\s|$)|^ngày$|tuổi/i
const NOT_ADDITIVE_FIELD=/(^|_)(rate|price|percent|pct|ratio|idx|year|age|month|week|day|no|code|balance|after|avg|average|per|min|max|level|status|state)(_|$)|after_transaction|^(docstatus|disabled|enabled|is_|has_|must_)/i
import {unitColumn} from './grid-format.js'
// Quantities in different units (kg, lít, ml) have no meaningful total.
const mixedUnits=(col,rows,raw,columns)=>{const unit=unitColumn(col,columns);return Boolean(unit)&&new Set(rows.map(row=>raw(row,unit)??'')).size>1}
export function summableColumn(col,rows,raw,columns=[]){
 if(col.sum===false||col.hide)return false
 if(col.sum===true)return true
 if(mixedUnits(col,rows,raw,columns))return false
 const label=String(col.headerName||''),field=String(col.field||col.colId||'')
 if(NOT_ADDITIVE.test(label)||NOT_ADDITIVE_FIELD.test(field))return false
 const filled=rows.filter(row=>{const v=raw(row,col);return v!==null&&v!==undefined&&v!==''})
 if(!filled.length||!filled.every(row=>{const v=raw(row,col);return typeof v==='number'&&Number.isFinite(v)}))return false
 // Numbers shown as words (docstatus → "Đã ghi sổ", disabled → "Đang dùng") are codes, not amounts.
 const sample=filled.find(row=>raw(row,col)!==0)
 if(sample&&col.valueFormatter){try{const text=col.valueFormatter({value:raw(sample,col),data:sample});if(typeof text==='string'&&!/\d/.test(text))return false}catch{}}
 return true
}
export function totalsRow(columns,sumColumns,rows,raw,key,label){
 const total={__lotus_total:true}
 for(const col of sumColumns){let sum=0;for(const row of rows){const v=raw(row,col);if(typeof v==='number'&&Number.isFinite(v))sum+=v}total[key(col)]=Math.round(sum*1e6)/1e6}
 // A summed quantity keeps its (single) unit, so "1.250 kg" reads as kg on the total row too.
 for(const col of sumColumns){const unit=unitColumn(col,columns);if(unit?.field&&rows.length&&!(unit.field in total))total[unit.field]=raw(rows[0],unit)}
 const first=columns.find(col=>!col.hide&&!sumColumns.includes(col))
 if(first)total[key(first)]=label+' ('+rows.length+' dòng)'
 return total
}

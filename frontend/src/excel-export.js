import {strToU8,zipSync} from 'fflate'

// SpreadsheetML written as XLSX, without formulas or macros.
// Data is copied from the rows the user is authorised to read.
const xmlEscape=value=>String(value??'').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]/g,'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&apos;')
const letters=n=>{let out='';for(let i=n+1;i>0;i=Math.floor((i-1)/26))out=String.fromCharCode(65+(i-1)%26)+out;return out}
const key=column=>column.field||column.colId||column.headerName
function display(row,column){
 let value
 try{value=column.valueGetter?column.valueGetter({data:row}):row[column.field]}catch{return ''}
 if(value==null||value==='')return ''
 // Keep actual numbers numeric in Excel, not the Vietnamese formatted string.
 if(typeof value==='number'&&Number.isFinite(value))return value
 if(column.valueFormatter){
  try{value=column.valueFormatter({value,data:row})}catch{/* use raw value */}
 }
 if(value==null||value==='—')return ''
 if(typeof value==='number'&&Number.isFinite(value))return value
 if(typeof value==='boolean')return value?'Có':'Không'
 if(typeof value==='object')return JSON.stringify(value)
 return String(value).slice(0,32767)
}
const cell=(column,rowNumber,value,header=false)=>{
 const reference=letters(column)+rowNumber
 if(typeof value==='number'&&Number.isFinite(value))return '<c r="'+reference+'"><v>'+value+'</v></c>'
 return '<c r="'+reference+'" t="inlineStr"'+(header?' s="1"':'')+'><is><t xml:space="preserve">'+xmlEscape(value)+'</t></is></c>'
}

export function buildXlsx(columns,rows){
 const fields=columns.filter(column=>!column.hide&&!column.suppressExport&&(column.field||column.valueGetter))
 if(!fields.length)throw new Error('Không có cột dữ liệu để xuất.')
 const maxRows=20000
 if(rows.length>maxRows)throw new Error('Bảng quá 20.000 dòng. Hãy lọc bớt trước khi xuất Excel.')
 const sheetRows=['<row r="1">'+fields.map((field,i)=>cell(i,1,field.headerName||key(field),true)).join('')+'</row>']
 rows.forEach((row,index)=>{
  const number=index+2
  sheetRows.push('<row r="'+number+'">'+fields.map((column,i)=>cell(i,number,display(row,column))).join('')+'</row>')
 })
 const last=letters(fields.length-1)
 const worksheet='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
  '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+
  '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+
  '<sheetFormatPr defaultRowHeight="16"/><cols>'+fields.map((column,i)=>'<col min="'+(i+1)+'" max="'+(i+1)+'" width="'+Math.min(50,Math.max(14,Math.round((column.minWidth||160)/8)))+'" customWidth="1"/>').join('')+'</cols>'+
  '<sheetData>'+sheetRows.join('')+'</sheetData><autoFilter ref="A1:'+last+(rows.length+1)+'"/></worksheet>'
 const entries={
  '[Content_Types].xml':'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
  '_rels/.rels':'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
  'xl/workbook.xml':'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Dữ liệu" sheetId="1" r:id="rId1"/></sheets></workbook>',
  'xl/_rels/workbook.xml.rels':'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
  'xl/styles.xml':'<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Arial"/></font><font><b/><sz val="11"/><name val="Arial"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs></styleSheet>',
  'xl/worksheets/sheet1.xml':worksheet
 }
 return zipSync(Object.fromEntries(Object.entries(entries).map(([name,xml])=>[name,strToU8(xml)])),{level:5})
}

export function exportExcelFile(bytes,filename='Bang-du-lieu'){
 const url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}))
 const link=document.createElement('a')
 link.href=url
 link.download=String(filename||'Bang-du-lieu').replace(/[\\/:*?"<>|]/g,'-')+'.xlsx'
 document.body.append(link)
 link.click()
 link.remove()
 setTimeout(()=>URL.revokeObjectURL(url),1000)
}

/** Pure mobile form helpers; backend independently validates every input. */
export function placeOptions(catalog){
 const blocks=(catalog.blocks||[]).map(b=>({
  value:'block:'+b.name,label:'Lô '+(b.block_code||b.block_name||b.name),
  subtitle:'Tự chia chỉ tiêu theo diện tích thửa'
 }))
 const plots=(catalog.plots||[]).map(p=>{
  const parent=(catalog.blocks||[]).find(b=>b.name===p.farm_block)
  return {value:'plot:'+p.name,label:'Thửa '+(p.plot_code||p.plot_name||p.name),
          subtitle:'Thuộc lô '+(parent?.block_code||parent?.block_name||p.farm_block)}
 })
 return [...blocks,...plots]
}
export function cleanItems(items){
 if(!Array.isArray(items)||!items.length)throw Error('Thêm ít nhất một công việc.')
 return items.map((item,i)=>{
  if(!item.location)throw Error('Việc '+(i+1)+': chưa chọn lô hoặc thửa.')
  if(!item.work_type)throw Error('Việc '+(i+1)+': chưa chọn công việc.')
  const qty=Number(item.qty)
  if(!Number.isFinite(qty)||qty<=0||qty>1000000)throw Error('Việc '+(i+1)+': số lượng không hợp lệ.')
  return {location:item.location,work_type:item.work_type,qty}
 })
}

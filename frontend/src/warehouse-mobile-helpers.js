// Các phép kiểm tra thuần, dùng chung cho giao diện và bài kiểm tra Kho Lotus.
export function foldVietnamese(value){
 return String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase()
}

export function validateReceiptInputs(lines,values){
 const quantities={}
 for(const line of lines||[]){
  const raw=String(values?.[line.line]??'').trim()
  if(!raw)continue
  const qty=Number(raw)
  const remaining=Number(line.remaining_qty)
  const factor=Number(line.conversion_factor)||1
  if(!Number.isFinite(qty)||qty<0||!Number.isFinite(remaining)||remaining<0||qty>remaining+0.000001){
   return {valid:false,reason:'Số thực nhận phải từ 0 đến số còn chờ của từng mặt hàng.',quantities:{}}
  }
  if(qty>0)quantities[line.line]=qty*factor
 }
 return {valid:true,reason:'',quantities}
}

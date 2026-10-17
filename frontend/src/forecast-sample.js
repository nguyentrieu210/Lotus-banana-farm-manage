/* Dự thu mẫu độc lập với dữ liệu Frappe.
   Chỉ để kiểm thử giao diện. KHÔNG ghi database, không chốt sản lượng,
   không thay thế việc đo đạc và phê duyệt hệ số thực tế. */
export function sampleForecastCalendar(fromDate='2026-10-01'){
 const base=/^\d{4}-\d{2}-\d{2}$/.test(String(fromDate))?new Date(fromDate+'T00:00:00Z'):new Date('2026-10-01T00:00:00Z')
 if(!Number.isFinite(base.getTime()))return sampleForecastCalendar('2026-10-01')
 const start=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth(),1))
 const iso=d=>d.toISOString().slice(0,10)
 const months=Array.from({length:36},(_,i)=>{const d=new Date(Date.UTC(start.getUTCFullYear(),start.getUTCMonth()+i,1));return {month:iso(d).slice(0,7),bunches:0,gross_kg:0,packed_kg:0,actual_gross_kg:0}})
 const lots=[
  {id:'MAU-LO-A01',block_name:'[MẪU] Lô A01',startMonth:1,bunches:1300,step:9},
  {id:'MAU-LO-B02',block_name:'[MẪU] Lô B02',startMonth:4,bunches:1900,step:9},
  {id:'MAU-LO-C03',block_name:'[MẪU] Lô C03',startMonth:7,bunches:950,step:10},
  {id:'MAU-LO-D04',block_name:'[MẪU] Lô D04',startMonth:9,bunches:1600,step:8},
 ]
 const source={
  cut:['Đã cắt bắp','Cao'],shoot:['Đã trổ buồng','Khá'],
  sucker:['Đã chọn chồi','Trung bình'],plant:['Ngày trồng','Thấp'],
  future:['Vụ chồi dự phóng','Dự phóng'],
 }
 const rows=[]
 for(const lot of lots)for(let step=0;step<4;step++){
  const idx=lot.startMonth+step*lot.step
  if(idx>=36)break
  const month=months[idx]
  const kind=step===0?['cut','shoot','sucker','plant'][lots.indexOf(lot)]:step===1?'sucker':'future'
  const net=lot.bunches*(step===0?1:step===1?.94:.88)
  const gross=Math.round(net*20*0.9*100)/100
  const packed=Math.round(gross*0.76*100)/100
  const r={farm:'[MẪU] Vườn minh họa',farm_block:lot.id,block_name:lot.block_name,
    cycle:'[MẪU] Vụ '+(step+1),cycle_no:step+1,source:kind,source_label:source[kind][0],
    confidence:source[kind][1],expected_date:month.month+'-15',month:month.month,
    bunches:Math.round(net),gross_kg:gross,packed_kg:packed,projected:['plant','future'].includes(kind),
    commit_ready:false,profile:'[MẪU] Hệ số minh họa'}
  rows.push(r);month.bunches+=r.bunches;month.gross_kg+=gross;month.packed_kg+=packed
 }
 return {from_date:iso(start),to_date:iso(new Date(Date.UTC(start.getUTCFullYear(),start.getUTCMonth()+36,0))),
  rows,months,issues:[],
  summary:{blocks:lots.length,ready_blocks:lots.length,missing_blocks:0,
   bunches:rows.reduce((a,b)=>a+b.bunches,0),
   gross_kg:rows.reduce((a,b)=>a+b.gross_kg,0),
   packed_kg:rows.reduce((a,b)=>a+b.packed_kg,0),
   projected_kg:rows.filter(r=>r.projected).reduce((a,b)=>a+b.gross_kg,0)},
  demo:true,note:'DỮ LIỆU MẪU MINH HỌA. Không phải số liệu sản xuất của Lotus, không ghi sổ hoặc cam kết bán hàng.'}
}

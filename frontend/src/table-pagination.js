// A zero page size means all rows. Read every server page through its existing
// bounded API, preserving the caller's filters and permissions on each request.
export async function tablePage(request,args,{pageSize=50,rowsKey='rows',sizeKey='length',isCurrent=()=>true}={}){
 const check=()=>{if(!isCurrent())throw Object.assign(new Error('Danh sách đã thay đổi.'),{stale:true})}
 if(pageSize!==0)return request({...args,[sizeKey]:pageSize})
 let first,offset=0
 const rows=[]
 for(;;){
  check()
  const page=await request({...args,start:offset,[sizeKey]:100})
  check()
  const batch=page[rowsKey]
  if(!Array.isArray(batch))throw new Error('Không đọc được đầy đủ dữ liệu của bảng.')
  first??=page
  rows.push(...batch)
  if(!page.has_more)return {...first,[rowsKey]:rows,start:0,has_more:false}
  if(!batch.length)throw new Error('Không tải đủ dữ liệu để hiện toàn bộ. Hãy tải lại bảng.')
  offset+=batch.length
 }
}

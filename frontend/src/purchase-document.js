// Authenticated ERPNext Purchase Order PDF; a share-sheet result is not proof a supplier received it.
export function purchasePdfUrl(name) {
 if(!name || typeof name!=='string') throw Error('Chưa chọn đơn mua.')
 const query=new URLSearchParams({name})
 return '/api/method/lotus_farm.digital_signature.download_purchase_pdf?'+query.toString()
}
export async function sharePurchasePdf(name,{fetchPdf=fetch,shareApi=navigator,download}={}) {
 const response=await fetchPdf(purchasePdfUrl(name),{credentials:'same-origin',cache:'no-store'})
 if(!response.ok)throw Error('Không tải được phiếu PDF. Kiểm tra quyền in đơn mua.')
 const blob=await response.blob()
 if(blob.type&&!blob.type.includes('pdf'))throw Error('Máy chủ không trả về PDF. Hãy đăng nhập lại.')
 const file=new File([blob],name.replace(/[^a-zA-Z0-9_-]/g,'_')+'.pdf',{type:'application/pdf'})
 if(typeof shareApi.share==='function'&&typeof shareApi.canShare==='function'&&shareApi.canShare({files:[file]})){
  try{await shareApi.share({files:[file],title:'Đơn mua '+name});return 'shared'}
  catch(error){if(error?.name==='AbortError')return 'cancelled';throw error}
 }
 if(download){download(file);return 'downloaded'}
 const url=URL.createObjectURL(file)
 const a=document.createElement('a')
 a.href=url;a.download=file.name;document.body.appendChild(a);a.click();a.remove()
 setTimeout(()=>URL.revokeObjectURL(url),60000)
 return 'downloaded'
}
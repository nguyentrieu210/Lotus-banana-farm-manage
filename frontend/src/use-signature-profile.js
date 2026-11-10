// Chữ ký của tôi (spec 003, FR-018): one set of rules for the phone settings (Vant) and the desktop modal.
// The server (lotus_farm.digital_signature) re-checks the image, strips metadata and only ever edits the
// signature of the logged-in user.
async function call(method,args,write){const api=await import('./api');return api.call(method,args,write)}
const endpoint='lotus_farm.digital_signature.'

export const MAX_IMAGE_BYTES=10000000
// PNG or JPG only; HEIC from iPhones must be converted first. Returns an error message or ''.
export function imageFileProblem(file){
 if(!file)return 'Chưa chọn ảnh.'
 const typed=['image/png','image/jpeg'].includes(file.type)
 const named=/\.(png|jpe?g)$/i.test(file.name||'')&&(!file.type||file.type==='application/octet-stream')
 if(!typed&&!named)return 'Chỉ nhận ảnh PNG hoặc JPG. Nếu là HEIC, hãy đổi sang JPG.'
 if(file.size>MAX_IMAGE_BYTES)return 'Ảnh phải nhỏ hơn 10 MB.'
 return ''
}

export const loadProfile=(callFn=call)=>callFn(endpoint+'my_signature_profile',{},false)
export function saveImage(kind,dataUrl,callFn=call){
 if(!String(dataUrl||'').startsWith('data:image/'))throw Error('Ảnh chữ ký không hợp lệ.')
 return callFn(endpoint+(kind==='initials'?'save_my_initials_image':'save_my_signature_image'),{image_data:dataUrl},true)
}
export const removeImage=(kind,callFn=call)=>callFn(endpoint+(kind==='initials'?'remove_my_initials_image':'remove_my_signature_image'),{},true)
export const saveDateFormat=(format,callFn=call)=>callFn(endpoint+'save_my_signature_date_format',{date_format:format},true)

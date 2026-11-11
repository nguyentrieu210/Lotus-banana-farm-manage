import {activeUser,setActiveUser,cachedMethod,saveRead,cachedRead} from './offline-cache'
let csrf=''
export function setCSRF(value){csrf=value||''}
function failure(data){let message=data.message||data.exc_type||'Không kết nối được máy chủ';try{message=JSON.parse(data._server_messages).map(s=>JSON.parse(s).message.replace(/<[^>]*>/g,'')).join('; ')}catch{}return new Error(typeof message==='string'?message:JSON.stringify(message))}
export async function call(method,args={},write=false){
 const options={credentials:'same-origin',headers:{Accept:'application/json'}}
 let url='/api/method/'+method
 if(write){options.method='POST';options.headers['Content-Type']='application/json';options.headers['X-Frappe-CSRF-Token']=csrf;options.body=JSON.stringify(args)}
 else url+='?'+new URLSearchParams(Object.fromEntries(Object.entries(args).filter(([,v])=>v!=null&&v!=='')))
 let response
 try{response=await fetch(url,options)}catch(error){
  if(!write&&cachedMethod(method)){const value=await cachedRead(activeUser(),method,args);if(value!==null){window.dispatchEvent(new Event('lotus-cached-read'));return method==='lotus_farm.console.bootstrap'?{...value,offline:true}:value}}
  throw new Error(write?'Chưa gửi được vì mất mạng; chưa rõ máy chủ đã lưu hay chưa. Kiểm tra kết nối và xem dữ liệu đã lưu chưa trước khi gửi lại.':'Không có dữ liệu đã lưu cho phạm vi này; cần mở phạm vi khi có mạng trước.')
 }
 const data=await response.json()
 if(!response.ok||data.exc_type){if(response.status===401||data.exc_type==='AuthenticationError')setActiveUser('');const error=failure(data);error.status=response.status;error.code=data.exc_type;throw error}
 const value=data.message
 if(method==='lotus_farm.console.bootstrap'&&value?.user)setActiveUser(value.user)
 if(!write&&cachedMethod(method))try{await saveRead(activeUser(),method,args,value)}catch{}
 return value
}
export const consoleAPI=(name,args={},write=false)=>call('lotus_farm.console.'+name,args,write)
export async function upload(file,doctype,name){const form=new FormData();form.append('file',file);form.append('is_private','1');if(name){form.append('doctype',doctype);form.append('docname',name)}const response=await fetch('/api/method/upload_file',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':csrf},body:form});let result={};try{result=await response.json()}catch{}if(!response.ok||result.exc_type)throw uploadFailure(result,file,response.status);return result.message}
// A failed upload often comes back as a bare exception name. Say what happened in Vietnamese (found in the walk-through
// on the live-site copy, 10/11/2026): a file the server cannot read asks for another file; an expired session or a
// refused right asks to log in again; anything else is the server's own failure, to retry.
const FILE_ERRORS=/^(PdfReadError|PdfStreamError|EmptyFileError|UnidentifiedImageError|DecompressionBombError|BadZipFile|InvalidFileError)$/
const SESSION_ERRORS=/^(PermissionError|AuthenticationError|SessionExpired|CSRFTokenError)$/
export function uploadFailure(result,file,status){
 const error=failure(result||{}),name=String(result?.exc_type||'').trim()||error.message.trim(),label=file?.name||''
 if(status===401||status===403||SESSION_ERRORS.test(name))error.message='Phiên đăng nhập đã hết hoặc bạn không có quyền tải tệp. Đăng nhập lại rồi tải lại tệp '+label+'.'
 else if(FILE_ERRORS.test(name))error.message='Không đọc được tệp '+label+' (tệp hỏng hoặc không đúng định dạng). Chọn hoặc chụp lại tệp khác.'
 else if(/^[A-Za-z]+(Error|Exception)$/.test(error.message.trim()))error.message='Máy chủ chưa nhận được tệp '+label+' ('+error.message.trim()+'). Thử lại sau ít phút.'
 return error
}

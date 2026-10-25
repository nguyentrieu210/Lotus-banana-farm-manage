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
  throw new Error(write?'Chưa gửi được. Giữ bản ghi trong hàng chờ rồi thử lại khi có mạng.':'Không có dữ liệu đã lưu cho phạm vi này; cần mở phạm vi khi có mạng trước.')
 }
 const data=await response.json()
 if(!response.ok||data.exc_type){if(response.status===401||data.exc_type==='AuthenticationError')setActiveUser('');const error=failure(data);error.status=response.status;error.code=data.exc_type;throw error}
 const value=data.message
 if(method==='lotus_farm.console.bootstrap'&&value?.user)setActiveUser(value.user)
 if(!write&&cachedMethod(method))try{await saveRead(activeUser(),method,args,value)}catch{}
 return value
}
export const consoleAPI=(name,args={},write=false)=>call('lotus_farm.console.'+name,args,write)
export async function upload(file,doctype,name,expectedUser){const form=new FormData();form.append('file',file);form.append('is_private','1');if(name){form.append('doctype',doctype);form.append('docname',name)}if(expectedUser){form.append('method','lotus_farm.field.save_uploaded_photo');form.append('expected_user',expectedUser)}const response=await fetch('/api/method/upload_file',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':csrf},body:form});const result=await response.json();if(!response.ok||result.exc_type)throw failure(result);return result.message}

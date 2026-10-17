// This entry installs ONLY the Work PWA's Service Worker.
const isWorkPage=window.location.pathname.replace(/\/$/,'')==='/work';
if(isWorkPage && 'serviceWorker' in navigator && window.isSecureContext){
 const register=()=>navigator.serviceWorker.register(
  '/api/method/lotus_farm.web.work_service_worker',
  {scope:'/work',updateViaCache:'none'}
 ).catch(error=>console.warn('Không đăng ký được PWA Công việc ngoài Vườn:',error));
 if(document.readyState==='complete')register();
 else window.addEventListener('load',register,{once:true});
}

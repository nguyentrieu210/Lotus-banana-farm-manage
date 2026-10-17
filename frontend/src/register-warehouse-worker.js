// This registration belongs only to the independently installable Kho Lotus PWA.
const isWarehousePage=window.location.pathname.replace(/\/$/,'')==='/warehouse';
if(isWarehousePage && 'serviceWorker' in navigator && window.isSecureContext){
 const register=()=>navigator.serviceWorker.register(
  '/api/method/lotus_farm.web.warehouse_service_worker',
  {scope:'/warehouse',updateViaCache:'none'}
 ).catch(error=>console.warn('Không đăng ký được PWA Kho Lotus:',error));
 if(document.readyState==='complete')register();
 else window.addEventListener('load',register,{once:true});
}

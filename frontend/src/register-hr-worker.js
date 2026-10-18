const isHrPage=window.location.pathname.replace(/\/$/,'')==='/hr-mobile'
if(isHrPage&&'serviceWorker' in navigator&&window.isSecureContext){
 const register=()=>navigator.serviceWorker.register('/api/method/lotus_farm.web.hr_mobile_service_worker',
  {scope:'/hr-mobile',updateViaCache:'none'}).catch(()=>{})
 if(document.readyState==='complete')register()
 else window.addEventListener('load',register,{once:true})
}

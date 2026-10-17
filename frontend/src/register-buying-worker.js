const onBuying=location.pathname.replace(/\/$/,'')==='/buying'
if(onBuying&&'serviceWorker' in navigator&&window.isSecureContext){
 const register=()=>navigator.serviceWorker.register('/api/method/lotus_farm.web.buying_service_worker',{scope:'/buying',updateViaCache:'none'}).catch(console.warn)
 if(document.readyState==='complete')register()
 else window.addEventListener('load',register,{once:true})
}

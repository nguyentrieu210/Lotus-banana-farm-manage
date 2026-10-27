if('serviceWorker' in navigator){
 window.addEventListener('load',()=>{
  navigator.serviceWorker.register('/api/method/lotus_farm.web.field_proposal_service_worker',
   {scope:'/field-proposals',updateViaCache:'none'}).catch(()=>{})
 })
}

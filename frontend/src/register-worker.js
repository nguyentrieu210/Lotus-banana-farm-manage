// Dev server: tránh service worker cache giao diện cũ, làm HMR không cập nhật.
if(!import.meta.env.DEV && 'serviceWorker' in navigator)navigator.serviceWorker.register('/api/method/lotus_farm.web.service_worker',{scope:'/lotus/'}).catch(()=>{})

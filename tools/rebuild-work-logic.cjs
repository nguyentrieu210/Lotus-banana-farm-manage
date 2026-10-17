const fs=require('fs');
const path='frontend/src/WorkMobile.vue';
let src=fs.readFileSync(path,'utf8');
function replace(oldText,newText,label){
 const n=src.split(oldText).length-1;
 if(n!==1)throw new Error((label||'replace')+' expected 1 occurrence, got '+n);
 src=src.replace(oldText,newText);
 console.log('changed',label||oldText.slice(0,30));
}
replace("import {useMobileViewport} from './use-mobile-viewport'","import {useMobileViewport} from './use-mobile-viewport'\nimport {swipeStep} from './mobile-swipe'","swipe import");
replace("const rejection=ref(''),rejectReason=ref(''),installPrompt=ref(null),installHelp=ref(false)","const rejection=ref(''),rejectReason=ref(''),installPrompt=ref(null),installHelp=ref(false)\nconst installed=ref(false),leaveDialog=ref(null),leaveMessage=ref(''),discardDialog=ref(null),discardReason=ref(''),discardEntry=ref(null)\nlet leaveResolver=null,swipe=null","dialog refs");
replace("const tabs=['home','tasks','history','profile']","const tabs=['home','history','tasks','profile']\nconst screenTitle=computed(()=>({home:'Trang chủ',tasks:'Công việc',history:'Lịch sử',profile:'Tôi',detail:'Chi tiết công việc',result:'Ghi kết quả',block:'Báo vướng mắc',assign:'Lập kế hoạch / Giao việc','assign-preview':'Xem lại kế hoạch',queue:'Hàng chờ',done:'Hoàn tất'})[screen.value]||'Công việc Lotus')\nconst shortDate=value=>{const s=String(value||'').slice(0,10);return /^\\d{4}-\\d{2}-\\d{2}$/.test(s)?s.split('-').reverse().join('/'):s||'—'}","title and date");
replace("function back(){\n if(saving.value)return\n if(['result','block'].includes(screen.value)){go('detail');return}\n if(screen.value==='detail'){go('tasks');return}\n if(screen.value==='assign-preview'){go('assign');return}\n if(screen.value==='assign'){go('home');return}\n if(screen.value==='queue'){go('profile');return}\n go('home')\n}\nasync function changeTab(tab){\n if(saving.value||!tabs.includes(tab))return\n go(tab)\n if(tab==='history')await loadHistory()\n if(tab==='profile')await refreshQueue()\n}",
`function appBack(){
 if(saving.value)return
 if(document.querySelector('.mobile-floating-options')){
  document.dispatchEvent(new Event('warehouse-dismiss-picker'));return
 }
 if(screen.value!=='home')window.history.back()
}
function isDirty(){
 if(screen.value==='result')
  return !!resultForm.value&&(Object.values(resultForm.value).some(v=>String(v||'').trim()!=='')||!!photo.value)
 if(screen.value==='block')return !!blockReason.value.trim()
 if(['assign','assign-preview'].includes(screen.value))
  return !!assignTeam.value||assignLines.value.some(row=>Object.values(row).some(v=>String(v||'').trim()!==''))
 return false
}
function askLeave(text){
 if(leaveResolver)return Promise.resolve(false)
 leaveMessage.value=text
 return new Promise(resolve=>{
  leaveResolver=resolve
  leaveDialog.value?.showModal()
 })
}
function finishLeave(yes){
 leaveDialog.value?.close()
 const cb=leaveResolver;leaveResolver=null;cb?.(yes)
}
function confirmLeave(){
 if(!isDirty())return Promise.resolve(true)
 return askLeave('Bạn đang nhập dữ liệu chưa lưu. Rời màn hình sẽ mất phần đang nhập.')
}
async function changeTab(tab){
 if(saving.value||!tabs.includes(tab)||screen.value===tab||!await confirmLeave())return
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 go(tab)
 if(tab==='history')await loadHistory()
 if(tab==='profile')await refreshQueue()
}
function swipeStart(e){
 swipe=null
 if(!tabs.includes(screen.value)||saving.value||e.touches.length!==1||e.target.closest('input,textarea,select,a,button,.mobile-link-field,.mobile-live-search,.mobile-bottom,.mobile-leave-dialog'))return
 const t=e.touches[0]
 if(t.clientX<24||t.clientX>window.innerWidth-24)return
 swipe={x:t.clientX,y:t.clientY,time:performance.now(),screen:screen.value}
}
function swipeMove(e){
 if(!swipe||e.touches.length!==1){swipe=null;return}
 const t=e.touches[0],dx=t.clientX-swipe.x,dy=t.clientY-swipe.y
 if(Math.abs(dy)>16&&Math.abs(dy)>Math.abs(dx)){swipe=null;return}
 if(Math.abs(dx)>16&&Math.abs(dx)>Math.abs(dy)*2&&e.cancelable)e.preventDefault()
}
function swipeEnd(e){
 const from=swipe;swipe=null
 if(!from||from.screen!==screen.value||!e.changedTouches?.length)return
 const t=e.changedTouches[0]
 const step=swipeStep({dx:t.clientX-from.x,dy:t.clientY-from.y,elapsed:performance.now()-from.time,startX:from.x,width:window.innerWidth})
 const target=tabs[tabs.indexOf(screen.value)+step]
 if(step&&target)changeTab(target)
}
function beforeUnload(e){
 if(saving.value||isDirty()){e.preventDefault();e.returnValue=''}
}`,"navigation and gestures");
replace("async function discardQueue(entry){\n const reason=prompt('Lý do bỏ bản báo cáo chưa nhận trên máy chủ:')\n if(!reason?.trim())return\n saving.value=true;clear()\n try{await reconcileCapture(session.value.user,entry.key,{call},reason);await refreshQueue()}\n catch(e){error.value=messageFor(e)}\n finally{saving.value=false}\n}",
`function startDiscard(entry){
 discardEntry.value=entry;discardReason.value=''
 discardDialog.value?.showModal()
}
function closeDiscard(){discardDialog.value?.close();discardEntry.value=null;discardReason.value=''}
async function confirmDiscard(){
 if(!discardEntry.value||!discardReason.value.trim()||saving.value||!online.value)return
 saving.value=true;clear()
 try{
  const result=await reconcileCapture(session.value.user,discardEntry.value.key,{call},discardReason.value.trim())
  message.value=result.received?'Máy chủ đã nhận báo cáo, không thể bỏ.':'Đã bỏ bản nháp chưa gửi.'
  closeDiscard();await refreshQueue()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function logout(){
 if(saving.value||!await confirmLeave()||!await askLeave('Đăng xuất khỏi Công việc Lotus?'))return
 saving.value=true;error.value=''
 try{
  const r=await fetch('/api/method/logout',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':session.value?.csrf_token||''}})
  if(!r.ok)throw Error('Máy chủ chưa xử lý đăng xuất.')
  window.location.replace('/login?redirect-to=/work')
 }catch(e){error.value='Không đăng xuất được: '+messageFor(e)}
 finally{saving.value=false}
}`,"replace prompt discard and logout");
const start=src.indexOf("function onPopstate(e){");
const end=src.indexOf("function onInstall(e){");
if(start<0||end<=start)throw Error('missing history section');
const hist=`async function onPopstate(e){
 if(!navigationReady)return
 if(leaveResolver){
  finishLeave(false)
  history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 if(saving.value||document.querySelector('.mobile-floating-options')){
  document.dispatchEvent(new Event('warehouse-dismiss-picker'))
  history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 if(!await confirmLeave()){
  history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 const wanted=e.state?.lotusWork?.screen
 let next=['home','tasks','history','profile','detail','result','block','assign','assign-preview','queue','done'].includes(wanted)?wanted:'home'
 if(next==='result'&&!resultForm.value)next='tasks'
 if(next==='detail'&&!selected.value)next='tasks'
 if(next==='assign-preview'&&!preview.value)next='assign'
 if(next==='assign'&&!assignOptions.value)next='home'
 restoring=true
 screen.value=next
 restoring=false
 if(next==='history')loadHistory()
 if(next==='profile'||next==='queue')refreshQueue()
 // Hardware Back must navigate within this app, never to the previous browser site.
 if(!e.state?.lotusWork||next==='home'&&e.state?.lotusWorkRoot){
  history.pushState({lotusWork:{screen:'home'}},'',location.href)
 }
}
watch(screen,(next,prev)=>{
 if(!navigationReady||restoring)return
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 window.history.replaceState({...window.history.state,scroll:window.scrollY},'',location.href)
 window.history.pushState({lotusWork:{screen:next}},'',location.href)
 window.scrollTo(0,0)
},{flush:'sync'})
watch(error,value=>{
 if(value)requestAnimationFrame(()=>document.querySelector('.mobile-message.danger')?.scrollIntoView({block:'nearest',behavior:'smooth'}))
})
`;
src=src.slice(0,start)+hist+src.slice(end);
const mounted=src.indexOf("onMounted(async()=>{");
const stop=src.indexOf("\n</script>",mounted);
if(mounted<0||stop<0)throw Error('onMounted section missing');
const startup=`onMounted(async()=>{
 window.history.replaceState({...window.history.state,lotusWorkRoot:true},'',location.href)
 window.history.pushState({lotusWork:{screen:'home'}},'',location.href)
 window.addEventListener('popstate',onPopstate)
 window.addEventListener('online',connection);window.addEventListener('offline',connection)
 window.addEventListener('beforeunload',beforeUnload)
 window.addEventListener('beforeinstallprompt',onInstall)
 installed.value=window.matchMedia('(display-mode:standalone)').matches||navigator.standalone===true
 navigationReady=true
 await bootstrap()
})
onBeforeUnmount(()=>{
 finishLeave(false);navigationReady=false
 window.removeEventListener('popstate',onPopstate)
 window.removeEventListener('online',connection);window.removeEventListener('offline',connection)
 window.removeEventListener('beforeunload',beforeUnload)
 window.removeEventListener('beforeinstallprompt',onInstall)
})
`;
src=src.slice(0,mounted)+startup+src.slice(stop);
fs.writeFileSync(path,src,'utf8');
console.log('work logic patched',src.length);

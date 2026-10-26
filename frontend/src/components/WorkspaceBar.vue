<script setup>
import UiSelect from './ui/select/Select.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import LotusIcon from './LotusIcon.vue'
import {Button as UiButton} from './ui/button'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuLabel,DropdownMenuSeparator} from './ui/dropdown-menu'
import {Tooltip} from './ui/tooltip'
import {useWorkspace} from '../workspace'
import {dismissOnBackdrop} from '../dialogs'
import {call,consoleAPI} from '../api'
import {loadWorkspaceDirectory,mergeWorkspaceActions} from '../workspace-directory'
const emit=defineEmits(['update:farm'])
const props=defineProps({farms:{type:Array,default:()=>[]},farm:{type:String,default:''},user:{type:String,default:''},title:{type:String,default:'Lotus'},actions:{type:Array,default:()=>[]},sidebar:{type:Boolean,default:true},branded:{type:Boolean,default:false},navigate:Function,recordSearch:Function})
const {dark,sidebarCollapsed,toggleTheme,toggleSidebar}=useWorkspace()
const palette=ref(null),input=ref(null),query=ref(''),selected=ref(0),loggingOut=ref(false),logoutError=ref('')
const normalized=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const directory=ref([])
const allActions=computed(()=>mergeWorkspaceActions(props.actions,directory.value))
const actionResults=computed(()=>allActions.value.filter(a=>normalized(a.label).includes(normalized(query.value))))
// Records come from the server (permission-checked), after a short pause in typing.
const records=ref([]),searching=ref(false)
let searchTimer,searchVersion=0
watch(query,text=>{
 clearTimeout(searchTimer);records.value=[]
 if(!props.recordSearch||text.trim().length<2){searching.value=false;return}
 searching.value=true;const version=++searchVersion
 searchTimer=setTimeout(async()=>{try{const rows=await props.recordSearch(text.trim());if(version===searchVersion)records.value=rows||[]}catch{if(version===searchVersion)records.value=[]}finally{if(version===searchVersion)searching.value=false}},250)
})
const results=computed(()=>[...actionResults.value,...records.value])
const initials=computed(()=>props.user.slice(0,2).toUpperCase()||'…')
watch(query,()=>selected.value=0)
async function logout(){loggingOut.value=true;logoutError.value='';try{await call('logout',{},true);location.assign('/login?redirect-to=/lotus/mobile')}catch(e){logoutError.value=e.message}finally{loggingOut.value=false}}
async function open(){if(document.querySelector('dialog[open]')||document.querySelector('.modal-backdrop'))return;query.value='';selected.value=0;palette.value.showModal();await nextTick();input.value.focus()}
function choose(action){if(!action)return;palette.value.close();if(action.run)action.run();else if(action.href){if(props.navigate)props.navigate(action.href);else location.assign(action.href)}}
function shortcut(event){if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(palette.value.open)palette.value.close();else open()}}
function keys(event){if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();selected.value=(selected.value+(event.key==='ArrowDown'?1:-1)+results.value.length)%Math.max(1,results.value.length)}if(event.key==='Enter'){event.preventDefault();choose(results.value[selected.value])}}
onMounted(()=>window.addEventListener('keydown',shortcut))
onMounted(async()=>{directory.value=await loadWorkspaceDirectory(()=>consoleAPI('bootstrap'))})
onUnmounted(()=>window.removeEventListener('keydown',shortcut))
</script>
<template>
 <div class="workspace-bar" aria-label="Thanh điều hướng">
  <div class="workspace-left">
   <Tooltip v-if="sidebar" :content="sidebarCollapsed?'Mở thanh bên':'Thu gọn thanh bên'"><UiButton class="workspace-sidebar-toggle" variant="ghost" size="icon" :aria-label="sidebarCollapsed?'Mở thanh bên':'Thu gọn thanh bên'" :aria-expanded="!sidebarCollapsed" @click="toggleSidebar"><LotusIcon name="menu"/></UiButton></Tooltip>
   <a v-if="branded" class="workspace-brand" href="/lotus/mobile" aria-label="Trang chủ Lotus"><img :src="'/assets/lotus_farm/images/lotus-agritech.jpg'" alt="Lotus Agritech" width="112" height="44"><span>Kho Lotus</span></a>
   <Tooltip v-else content="Trang chủ"><a class="workspace-home" href="/lotus/mobile" aria-label="Trang chủ Lotus"><LotusIcon name="home"/></a></Tooltip>
   <DropdownMenu>
    <DropdownMenuTrigger as-child><button type="button" class="workspace-nav-trigger" aria-label="Chuyển phân hệ"><span class="workspace-nav-title">{{title}}</span><LotusIcon name="chevron-down"/></button></DropdownMenuTrigger>
    <DropdownMenuContent><DropdownMenuItem v-for="action in allActions.filter(a=>a.navigation)" :key="action.id" @select="choose(action)">{{action.label}}</DropdownMenuItem></DropdownMenuContent>
   </DropdownMenu>
   <label v-if="farms.length" class="workspace-farm" title="Vườn làm việc: chứng từ mới và bộ lọc vườn tự lấy vườn này"><LotusIcon name="sprout"/><span class="sr-only">Vườn làm việc</span><UiSelect :model-value="farm" aria-label="Vườn làm việc" @update:model-value="emit('update:farm',$event)"><option value="">Tất cả vườn</option><option v-for="f in farms" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></UiSelect></label>
  </div>
  <UiButton class="workspace-search" variant="outline" aria-label="Tìm nhanh (Ctrl K)" @click="open"><LotusIcon name="search" class="workspace-search-icon"/><span>Tìm nhanh…</span><kbd>Ctrl K</kbd></UiButton>
  <div class="workspace-right">
   <Tooltip :content="dark?'Giao diện sáng':'Giao diện tối'"><UiButton variant="ghost" size="icon" :aria-label="dark?'Chuyển giao diện sáng':'Chuyển giao diện tối'" @click="toggleTheme"><LotusIcon :name="dark?'sun':'moon'"/></UiButton></Tooltip>
   <DropdownMenu>
    <DropdownMenuTrigger as-child><button type="button" class="workspace-user-trigger" :aria-label="'Tài khoản '+user"><span class="workspace-avatar">{{initials}}</span><span class="workspace-username">{{user||'Đang kết nối…'}}</span></button></DropdownMenuTrigger>
    <DropdownMenuContent align="end">
     <DropdownMenuLabel class="lotus-menu__label">Tài khoản đang đăng nhập</DropdownMenuLabel>
     <DropdownMenuLabel class="lotus-menu__label lotus-menu__user">{{user||'Đang kết nối…'}}</DropdownMenuLabel>
     <DropdownMenuSeparator/>
     <DropdownMenuItem @select="open"><LotusIcon name="search"/>Tìm nhanh<kbd class="lotus-menu__kbd">Ctrl K</kbd></DropdownMenuItem>
     <DropdownMenuItem @select="toggleTheme"><LotusIcon :name="dark?'sun':'moon'"/>{{dark?'Giao diện sáng':'Giao diện tối'}}</DropdownMenuItem>
     <DropdownMenuSeparator/>
     <DropdownMenuItem :disabled="loggingOut" @select="logout"><LotusIcon name="logout"/>{{loggingOut?'Đang đăng xuất…':'Đăng xuất'}}</DropdownMenuItem>
    </DropdownMenuContent>
   </DropdownMenu>
   <p v-if="logoutError" class="error" role="alert">{{logoutError}}</p>
  </div>
 </div>
 <WorkspaceModal bare ref="palette" title="Tìm nhanh" class="command-dialog" aria-label="Tìm nhanh">
  <div class="command-input"><input ref="input" v-model="query" aria-label="Tìm màn hình, thao tác hoặc bản ghi" placeholder="Tìm màn hình, thao tác hoặc mã/tên bản ghi…" role="combobox" aria-autocomplete="list" :aria-expanded="true" aria-controls="lotus-command-results" :aria-activedescendant="results[selected]?'lotus-command-'+selected:undefined" @keydown="keys"><UiButton variant="ghost" size="sm" aria-label="Đóng tìm nhanh" @click="palette.close()">Esc</UiButton></div>
  <div id="lotus-command-results" role="listbox" class="command-results"><UiButton v-for="(action,index) in results" :id="'lotus-command-'+index" :key="action.id" variant="ghost" role="option" :aria-selected="index===selected" :class="{selected:index===selected}" @click="choose(action)">{{action.label}} <small>{{action.record?action.kind:action.navigation?'Đi đến':'Thao tác'}}</small></UiButton><p v-if="searching" role="status">Đang tìm bản ghi…</p><p v-else-if="!results.length" role="status">Không tìm thấy kết quả.</p></div>
  <footer>↑ ↓ chọn · Enter mở · Esc đóng</footer>
 </WorkspaceModal>
</template>

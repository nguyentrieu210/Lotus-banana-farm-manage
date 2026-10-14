<script setup>
import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import {useWorkspace} from '../workspace'
import {dismissOnBackdrop} from '../dialogs'
import {call} from '../api'
const props=defineProps({user:{type:String,default:''},title:{type:String,default:'Lotus'},actions:{type:Array,default:()=>[]},sidebar:{type:Boolean,default:true}})
const {dark,sidebarCollapsed,toggleTheme,toggleSidebar}=useWorkspace()
const palette=ref(null),input=ref(null),query=ref(''),selected=ref(0),menu=ref(null),userMenu=ref(null),loggingOut=ref(false),logoutError=ref('')
const normalized=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const results=computed(()=>props.actions.filter(a=>normalized(a.label).includes(normalized(query.value))))
const initials=computed(()=>props.user.slice(0,2).toUpperCase()||'…')
watch(query,()=>selected.value=0)
function closeMenus(){if(menu.value)menu.value.open=false;if(userMenu.value)userMenu.value.open=false}
function outside(event){for(const el of [menu.value,userMenu.value])if(el?.open&&!el.contains(event.target))el.open=false}
async function logout(){loggingOut.value=true;logoutError.value='';try{await call('logout',{},true);location.assign('/login?redirect-to=/lotus/mobile')}catch(e){logoutError.value=e.message}finally{loggingOut.value=false}}
async function open(){if(document.querySelector('dialog[open]')||document.querySelector('.modal-backdrop'))return;closeMenus();query.value='';selected.value=0;palette.value.showModal();await nextTick();input.value.focus()}
function choose(action){if(!action)return;palette.value.close();if(menu.value)menu.value.open=false;if(action.run)action.run();else if(action.href)location.assign(action.href)}
function shortcut(event){if(event.key==='Escape')closeMenus();if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(palette.value.open)palette.value.close();else open()}}
function keys(event){if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();selected.value=(selected.value+(event.key==='ArrowDown'?1:-1)+results.value.length)%Math.max(1,results.value.length)}if(event.key==='Enter'){event.preventDefault();choose(results.value[selected.value])}}
onMounted(()=>{window.addEventListener('keydown',shortcut);document.addEventListener('pointerdown',outside)})
onUnmounted(()=>{window.removeEventListener('keydown',shortcut);document.removeEventListener('pointerdown',outside)})
</script>
<template>
 <div class="workspace-bar" aria-label="Thanh điều hướng">
  <div class="workspace-left"><UiButton v-if="sidebar" variant="ghost" size="icon" :aria-label="sidebarCollapsed?'Mở thanh bên':'Thu gọn thanh bên'" :aria-expanded="!sidebarCollapsed" @click="toggleSidebar">☰</UiButton>
  <a class="workspace-home" href="/lotus/mobile" aria-label="Trang chủ Lotus" title="Trang chủ Lotus Agritech"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech.jpg'" alt="Lotus Agritech" width="707" height="411"></a>
  <details ref="menu" class="workspace-nav"><summary>{{title}} <span aria-hidden="true">⌄</span></summary><div class="workspace-menu"><UiButton v-for="action in actions.filter(a=>a.navigation)" :key="action.id" variant="ghost" @click="choose(action)">{{action.label}}</UiButton></div></details></div>
  <UiButton class="workspace-search" variant="outline" @click="open"><span>Tìm nhanh…</span><kbd>Ctrl K</kbd></UiButton>
  <div class="workspace-right"><UiButton variant="ghost" size="icon" :aria-label="dark?'Chuyển giao diện sáng':'Chuyển giao diện tối'" :title="dark?'Giao diện sáng':'Giao diện tối'" @click="toggleTheme">{{dark?'☀':'☾'}}</UiButton>
  <details ref="userMenu" class="workspace-user"><summary :aria-label="'Tài khoản '+user"><span class="workspace-avatar">{{initials}}</span><span class="workspace-username">{{user||'Đang kết nối…'}}</span></summary><div class="workspace-menu"><small>Tài khoản đang đăng nhập</small><strong>{{user||'Đang kết nối…'}}</strong><UiButton variant="ghost" @click="open">Tìm nhanh · Ctrl K</UiButton><UiButton variant="ghost" @click="toggleTheme">{{dark?'Giao diện sáng':'Giao diện tối'}}</UiButton><UiButton variant="ghost" :disabled="loggingOut" @click="logout">{{loggingOut?'Đang đăng xuất…':'Đăng xuất'}}</UiButton><p v-if="logoutError" role="alert">{{logoutError}}</p></div></details></div>
 </div>
 <dialog ref="palette" class="command-dialog" aria-label="Tìm nhanh" @click="dismissOnBackdrop($event)">
  <div class="command-input"><input ref="input" v-model="query" aria-label="Tìm màn hình hoặc thao tác" placeholder="Tìm màn hình hoặc thao tác…" role="combobox" aria-autocomplete="list" :aria-expanded="true" aria-controls="lotus-command-results" :aria-activedescendant="results[selected]?'lotus-command-'+selected:undefined" @keydown="keys"><UiButton variant="ghost" size="sm" aria-label="Đóng tìm nhanh" @click="palette.close()">Esc</UiButton></div>
  <div id="lotus-command-results" role="listbox" class="command-results"><UiButton v-for="(action,index) in results" :id="'lotus-command-'+index" :key="action.id" variant="ghost" role="option" :aria-selected="index===selected" :class="{selected:index===selected}" @click="choose(action)">{{action.label}} <small>{{action.navigation?'Đi đến':'Thao tác'}}</small></UiButton><p v-if="!results.length" role="status">Không tìm thấy kết quả.</p></div>
  <footer>↑ ↓ chọn · Enter mở · Esc đóng</footer>
 </dialog>
</template>

<script setup>
import {computed,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import LotusIcon from './LotusIcon.vue'
import {useSession,useScope} from '../store'
import {navGroups} from '../domain'
import {sidebarCollapsed} from '../workspace'
import {visibleHrNavigation,normalizeHrView,hrQuery} from '../hr-navigation.js'

// Preserve permissions from the app router. Menu grouping never grants page access.
const props=defineProps({nav:{type:Array,required:true},page:String,hrView:{type:String,default:'employees'}})
const emit=defineEmits(['go'])
const session=useSession(),scope=useScope()
const groups=computed(()=>{
 const allowed=new Map(props.nav)
 const placed=new Set()
 const result=navGroups.map((group,index)=>{
  if(group.kind==='hr'){
   for(const [path] of group.items)placed.add(path)
   const items=visibleHrNavigation(session).filter(item=>allowed.has(item.path)).map(item=>({...item,query:hrQuery(item.id)}))
   return {id:'group-'+index,kind:'hr',label:group.label,icon:group.icon,items,links:[],expandable:true}
  }
  const items=group.items.filter(([path])=>allowed.has(path)).map(([path,icon,label])=>{
   placed.add(path)
   return {path,icon,label:label||allowed.get(path)}
  })
  const links=(group.links||[]).filter(link=>!link.capability||!!session.capabilities?.[link.capability])
  return {id:'group-'+index,label:group.label,icon:group.icon,items,links,expandable:items.length+links.length>1}
 })
 // A new, permitted screen remains accessible even if the menu config misses it.
 const rest=props.nav.filter(([path])=>!placed.has(path)).map(([path,label])=>({path,icon:'list',label}))
 if(rest.length)result.push({id:'other',label:'Khác',icon:'list',items:rest,links:[],expandable:rest.length>1})
 return result.filter(group=>group.items.length)
})
const openGroup=ref(null)
watch([()=>props.page,()=>props.hrView,groups],([page,view,visibleGroups])=>{
 const active=visibleGroups.find(group=>group.items.some(item=>itemActive(item)))
 if(active)openGroup.value=active.label
},{immediate:true})
function openPrimary(group){
 if(group.kind==='hr'){
  if(sidebarCollapsed.value){sidebarCollapsed.value=false;localStorage.setItem('lotus-sidebar','open');openGroup.value=group.label}
  else toggleGroup(group)
  return
 }
 openGroup.value=group.label
 emit('go',group.items[0].path)
}
function toggleGroup(group){openGroup.value=openGroup.value===group.label?null:group.label}
const isOpen=group=>openGroup.value===group.label
function itemActive(item){return item.path===props.page&&(item.path!=='nhan-su'||item.id===normalizeHrView(props.hrView))}
const isActive=group=>group.items.some(item=>itemActive(item))
</script>
<template>
 <aside class="sidebar">
  <a class="brand" href="/lotus/reports"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech" width="641" height="213"></a>
  <nav aria-label="Điều hướng chính">
   <section v-for="group in groups" :key="group.id" class="nav-group" :class="{'nav-group-current':isActive(group)}" :aria-label="group.label">
    <div class="nav-group-row">
     <UiButton variant="outline" class="nav-parent" :title="group.label" :aria-label="group.label" :class="{active:group.kind!=='hr'&&props.page===group.items[0].path,'group-selected':isActive(group)}" :aria-current="group.kind!=='hr'&&props.page===group.items[0].path?'page':undefined" :aria-expanded="group.kind==='hr'?isOpen(group):undefined" @click="openPrimary(group)">
      <LotusIcon :name="group.icon" class="nav-icon"/>
      <span class="nav-label">{{group.label}}</span>
     </UiButton>
     <UiButton v-if="group.expandable" variant="outline" class="nav-toggle" :title="isOpen(group)?'Thu gọn '+group.label:'Mở rộng '+group.label" :aria-label="isOpen(group)?'Thu gọn '+group.label:'Mở rộng '+group.label" :aria-expanded="isOpen(group)" :aria-controls="group.id" @click="toggleGroup(group)">
      <LotusIcon name="chevron-down" class="nav-chevron" :class="{'nav-chevron-up':isOpen(group)}"/>
     </UiButton>
    </div>
    <div v-if="group.expandable" v-show="isOpen(group)&&!sidebarCollapsed" :id="group.id" class="nav-submenu">
     <template v-for="(item,index) in group.items" :key="item.id||item.path">
      <span v-if="group.kind==='hr'&&item.setup&&!group.items.slice(0,index).some(i=>i.setup)" class="nav-subsection">Thiết lập nhân sự</span>
      <UiButton v-if="group.kind==='hr'||group.items.length>1" variant="outline" class="nav-child" :title="item.label" :aria-label="item.label" :class="{active:itemActive(item)}" :aria-current="itemActive(item)?'page':undefined" @click="emit('go',item.path,group.kind==='hr'?item.query:undefined)">
       <LotusIcon :name="item.icon" class="nav-icon"/>
       <span class="nav-label">{{item.label}}</span>
      </UiButton>
     </template>
     <a v-for="link in group.links" :key="link.href" class="nav-sub-link" :href="link.href" :title="link.label">
      <LotusIcon :name="link.icon" class="nav-icon"/>
      <span class="nav-label">{{link.label}}</span>
     </a>
    </div>
   </section>
  </nav>
  <a v-if="session.commands.work&&session.modules.work?.length" class="field-link" :href="'/lotus/giao-viec'+(scope.farm?'?farm='+encodeURIComponent(scope.farm):'')">Giao việc nhanh trên điện thoại ↗</a>
  <a class="field-link" :href="'/assets/lotus_farm/field/index.html'">Giao diện hiện trường dự phòng ↗</a>
  <small>{{session.user}}</small>
 </aside>
</template>
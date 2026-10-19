<script setup>
import {computed,ref} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator,DropdownMenuLabel} from './ui/dropdown-menu'
import {Popover,PopoverTrigger,PopoverContent} from './ui/popover'
import LotusIcon from './LotusIcon.vue'
import {loadViews,saveView,deleteView} from '../grid-state'
// Active column filters as removable chips, plus named views (filters + sort) remembered per table.
// Only shown when something is filtered or a view exists, so plain tables stay uncluttered (AGENTS.md).
const props=defineProps({storageKey:{type:String,required:true},filters:{type:Object,default:()=>({})},sort:{type:Array,default:()=>[]},labels:{type:Object,default:()=>({})}})
const emit=defineEmits(['apply','clear'])
const views=ref(loadViews(props.storageKey)),name=ref(''),saving=ref(false)
const active=computed(()=>Object.entries(props.filters).map(([field,values])=>({field,label:props.labels[field]||field,count:values.length})))
const visible=computed(()=>active.value.length||views.value.length)
function clearOne(field){const next={...props.filters};delete next[field];emit('apply',{filters:next,sort:props.sort})}
function store(){const text=name.value.trim();if(!text)return;views.value=saveView(props.storageKey,{name:text,filters:props.filters,sort:props.sort});name.value='';saving.value=false}
function remove(view){views.value=deleteView(props.storageKey,view.name)}
</script>
<template>
 <div v-if="visible" class="lotus-table-views" role="toolbar" aria-label="Bộ lọc và chế độ xem của bảng">
  <div class="lotus-table-views__chips">
   <span v-for="item in active" :key="item.field" class="lotus-chip">{{item.label}}: {{item.count}} giá trị<button type="button" :aria-label="'Bỏ lọc '+item.label" @click="clearOne(item.field)"><LotusIcon name="x"/></button></span>
   <UiButton v-if="active.length>1" type="button" variant="ghost" size="sm" @click="emit('clear')">Xóa tất cả</UiButton>
  </div>
  <div class="lotus-table-views__actions">
   <Popover v-model:open="saving">
    <PopoverTrigger as-child><UiButton v-if="active.length||sort.length" type="button" variant="outline" size="sm">Lưu chế độ xem</UiButton></PopoverTrigger>
    <PopoverContent align="end"><form class="lotus-table-views__save" @submit.prevent="store"><label>Tên chế độ xem<UiInput v-model="name" maxlength="60" placeholder="VD: Hàng thiếu tuần này" required/></label><UiButton type="submit" size="sm">Lưu</UiButton></form></PopoverContent>
   </Popover>
   <DropdownMenu v-if="views.length">
    <DropdownMenuTrigger as-child><UiButton type="button" variant="outline" size="sm">Chế độ xem<LotusIcon name="chevron-down"/></UiButton></DropdownMenuTrigger>
    <DropdownMenuContent align="end">
     <DropdownMenuLabel class="lotus-menu__label">Đã lưu trên máy này</DropdownMenuLabel>
     <DropdownMenuItem v-for="view in views" :key="view.name" @select="emit('apply',{filters:view.filters,sort:view.sort})"><LotusIcon name="list"/>{{view.name}}</DropdownMenuItem>
     <DropdownMenuSeparator/>
     <DropdownMenuItem v-for="view in views" :key="'x'+view.name" @select="remove(view)"><LotusIcon name="x"/>Xóa “{{view.name}}”</DropdownMenuItem>
    </DropdownMenuContent>
   </DropdownMenu>
  </div>
 </div>
</template>
<style>
.lotus-table-views{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin:0 0 8px}
.lotus-table-views__chips,.lotus-table-views__actions{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.lotus-chip{display:inline-flex;align-items:center;gap:4px;min-height:28px;padding:0 4px 0 10px;border:1px solid var(--lotus-border);border-radius:999px;background:var(--lotus-primary-subtle);color:var(--lotus-primary-text);font-size:var(--lotus-text-sm)}
.lotus-chip button{display:grid;place-items:center;width:22px;height:22px;border:0;border-radius:50%;background:transparent;color:inherit;cursor:pointer}
.lotus-chip button:hover{background:color-mix(in srgb,currentColor 12%,transparent)}
.lotus-chip .lotus-icon{width:14px;height:14px}
.lotus-table-views__save{display:grid;gap:8px;min-width:240px}
.lotus-table-views__save label{display:grid;gap:4px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>

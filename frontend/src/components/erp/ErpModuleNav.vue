<script setup>
import {computed,ref,watch} from 'vue'
import {Input} from '../ui/input'
import {Button} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
import {erpFeature,erpModuleLabels} from '../../erpnext-navigation'
import {matchesOption} from '../../option-search.js'
const props=defineProps({module:String,rows:{type:Array,default:()=>[]},selected:Object})
const emit=defineEmits(['open'])
const search=ref(''),opened=ref(new Set())
const groups=computed(()=>{const map=new Map();for(const source of props.rows){const r=erpFeature(source);if(search.value&&!matchesOption({value:r.name,label:r.title+' '+r.group},search.value))continue;const key=r.group||'';if(!map.has(key))map.set(key,[]);map.get(key).push(r)}return [...map].sort((a,b)=>Number(!!a[0])-Number(!!b[0])).map(([label,items])=>({label,items}))})
function toggle(group){const next=new Set(opened.value);next.has(group)?next.delete(group):next.add(group);opened.value=next}
watch(()=>[props.selected,props.rows],([s])=>{const r=props.rows.find(r=>r.name===s?.name&&r.kind===s?.kind);if(r?.group)opened.value=new Set([...opened.value,r.group])},{immediate:true})
</script>
<template>
 <nav class="erp-module-nav" :aria-label="'Điều hướng '+(erpModuleLabels[module]||module)">
  <label class="erp-module-search"><span class="sr-only">Tìm chức năng</span><Input v-model="search" type="search" aria-label="Tìm chức năng" placeholder="Tìm chức năng…"/></label>
  <section v-for="group in groups" :key="group.label" class="erp-nav-group"><Button v-if="group.label" variant="ghost" class="erp-nav-group-toggle" :aria-expanded="opened.has(group.label)||!!search" @click="toggle(group.label)"><LotusIcon :name="group.label.toLowerCase().includes('report')?'chart':'list'"/><span>{{group.label}}</span><LotusIcon name="chevron-down"/></Button><div v-show="!group.label||opened.has(group.label)||search" class="erp-nav-items"><Button v-for="item in group.items" :key="item.id" variant="ghost" :class="{'is-active':selected?.name===item.name&&selected?.kind===item.kind}" :aria-current="selected?.name===item.name&&selected?.kind===item.kind?'page':undefined" @click="emit('open',item)"><LotusIcon :name="item.kind==='Report'?'chart':item.kind==='Workspace'?'home':item.kind==='Dashboard'?'trending':'file'"/><span>{{item.kind==='Workspace'?'Trang chủ':item.kind==='Dashboard'?'Bảng điều khiển':item.title}}</span></Button></div></section>
 </nav>
</template>

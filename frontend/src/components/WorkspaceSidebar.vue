<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
import LotusIcon from './LotusIcon.vue'
import {useSession,useScope} from '../store'
import {navGroups} from '../domain'
// Left navigation of the /lotus shell: permitted screens grouped by area, plus field app links.
const props=defineProps({nav:{type:Array,required:true},page:String})
defineEmits(['go'])
const session=useSession(),scope=useScope()
const groups=computed(()=>{
 const allowed=new Map(props.nav)
 const placed=new Set()
 const result=navGroups.map(group=>({label:group.label,items:group.items.filter(([path])=>allowed.has(path)).map(([path,icon,label])=>{placed.add(path);return {path,icon,label:label||allowed.get(path)}})}))
 // A permitted page missing from navGroups must still be reachable.
 const rest=props.nav.filter(([path])=>!placed.has(path)).map(([path,label])=>({path,icon:'list',label}))
 if(rest.length)result.push({label:'Khác',items:rest})
 return result.filter(group=>group.items.length)
})
</script>
<template><aside class="sidebar"><a class="brand" href="/lotus/mobile"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech" width="641" height="213"></a><nav aria-label="Điều hướng chính"><section v-for="group in groups" :key="group.label" class="nav-group" :aria-label="group.label"><h2 class="nav-group-title">{{group.label}}</h2><UiButton variant="outline" v-for="item in group.items" :aria-label="item.label" :title="item.label" :key="item.path" :class="{active:page===item.path}" :aria-current="page===item.path?'page':undefined" @click="$emit('go',item.path)"><LotusIcon :name="item.icon" class="nav-icon"/><span class="nav-label">{{item.label}}</span></UiButton></section></nav><a v-if="session.commands.work&&session.modules.work?.length" class="field-link" :href="'/lotus/giao-viec'+(scope.farm?'?farm='+encodeURIComponent(scope.farm):'')">Giao việc nhanh trên điện thoại ↗</a><a class="field-link" :href="'/assets/lotus_farm/field/index.html'">Giao diện hiện trường dự phòng ↗</a><small>{{session.user}}</small></aside></template>

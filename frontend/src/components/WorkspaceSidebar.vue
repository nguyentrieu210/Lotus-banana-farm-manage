<script setup>
import {Button as UiButton} from './ui/button'
import {useSession,useScope} from '../store'
// Left navigation of the /lotus shell (screens the user may open + field app links).
defineProps({nav:{type:Array,required:true},page:String})
defineEmits(['go'])
const session=useSession(),scope=useScope()
</script>
<template><aside class="sidebar"><a class="brand" href="/lotus/mobile"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech" width="641" height="213"></a><nav><UiButton variant="outline" v-for="[path,label] in nav"  :aria-label="label" :title="label" :key="path" :class="{active:page===path}" @click="$emit('go',path)"><span class="nav-short" aria-hidden="true">{{label.slice(0,1)}}</span><span class="nav-label">{{label}}</span></UiButton></nav><a v-if="session.commands.work&&session.modules.work?.length" class="field-link" :href="'/lotus/giao-viec'+(scope.farm?'?farm='+encodeURIComponent(scope.farm):'')">Giao việc nhanh trên điện thoại ↗</a><a v-if="session.capabilities.stock" class="field-link" href="/lotus/kho">Quản lý kho ↗</a><a class="field-link" :href="'/assets/lotus_farm/field/index.html'">Giao diện hiện trường dự phòng ↗</a><small>{{session.user}}</small></aside></template>

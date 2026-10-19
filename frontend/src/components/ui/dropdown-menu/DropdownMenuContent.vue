<script setup>
import {DropdownMenuPortal,DropdownMenuContent} from 'reka-ui'
defineProps({align:{type:String,default:'start'},sideOffset:{type:Number,default:6}})
</script>
<template><DropdownMenuPortal><DropdownMenuContent class="lotus-menu" :align="align" :side-offset="sideOffset" :collision-padding="8"><slot/></DropdownMenuContent></DropdownMenuPortal></template>

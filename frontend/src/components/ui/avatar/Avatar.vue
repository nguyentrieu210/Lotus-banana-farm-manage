<script setup>
import {computed} from 'vue'
import {initials} from '../../../agri-format.js'
// Initials of a person (spec 004, table person cell, crew chip). The tint follows the name, so a person keeps
// the same colour everywhere; the name stays readable next to it — colour alone never identifies anyone.
const props=defineProps({name:{type:String,default:''},size:{type:String,default:'md'}})
const hue=computed(()=>{let h=0;for(const ch of props.name)h=(h*31+ch.codePointAt(0))>>>0;return h%6})
</script>
<template>
 <span class="lotus-avatar" :class="{'lotus-avatar--sm':size==='sm','lotus-avatar--lg':size==='lg'}" :data-hue="hue" role="img" :aria-label="name||'Người dùng'" :title="name||undefined">{{initials(name)}}</span>
</template>

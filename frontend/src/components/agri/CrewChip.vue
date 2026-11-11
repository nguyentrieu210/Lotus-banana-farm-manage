<script setup>
import {Avatar} from '../ui/avatar'
// A person or a crew with its team (FR-036): initials, name, and the tổ / đội under it.
defineProps({name:{type:String,required:true},team:String,size:{type:String,default:'md'}})
</script>
<template>
 <span class="lotus-crew"><Avatar :name="name" :size="size"/><span class="lotus-crew__text"><span class="lotus-crew__name">{{name}}</span><span v-if="team" class="lotus-crew__team">{{team}}</span></span></span>
</template>

<script setup>
import {DropdownMenuItem} from 'reka-ui'
defineProps({disabled:Boolean})
const emit=defineEmits(['select'])
</script>
<template><DropdownMenuItem class="lotus-menu__item" :disabled="disabled" @select="emit('select',$event)"><slot/></DropdownMenuItem></template>

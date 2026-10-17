<script setup>
import {Button} from 'vant'
defineProps({type:{type:String,default:'button'},variant:{type:String,default:'default'},disabled:Boolean,loading:Boolean})
</script>
<template><Button :native-type="type" :type="variant" :disabled="disabled" :loading="loading"><slot/></Button></template>

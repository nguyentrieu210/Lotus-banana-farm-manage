<script setup>
import {Button} from 'vant'
import {computed} from 'vue'
const props=defineProps({type:{type:String,default:'button'},variant:{type:String,default:'default'},disabled:Boolean,loading:Boolean})
const buttonType=computed(()=>({outline:'default',secondary:'default',ghost:'default',destructive:'danger'}[props.variant]||props.variant))
</script>
<template><Button :native-type="type" :type="buttonType" :plain="variant==='outline'" :disabled="disabled" :loading="loading"><slot/></Button></template>

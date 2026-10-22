<script setup>
import {FormField} from './ui/form-field'
defineProps({mobile:Boolean,label:String,error:String,required:Boolean})
</script>
<template><div v-if="mobile" class="mobile-field"><label>{{label}}{{required?' *':''}}</label><slot/><p v-if="error" role="alert" class="error">{{error}}</p></div><FormField v-else :label="label" :required="required" :error="error" v-slot="f"><slot v-bind="f"/></FormField></template>

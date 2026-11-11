<script setup>
import {useId} from 'vue'
import {SwitchRoot,SwitchThumb} from 'reka-ui'
// On/off setting (spec 004, User Story 3), e.g. "Chế độ ngoài trời". reka-ui gives role=switch and the keyboard.
defineProps({label:String,disabled:Boolean})
const model=defineModel({type:Boolean,default:false})
const id=useId()
</script>
<template>
 <span class="lotus-switch"><SwitchRoot :id="id" v-model="model" class="lotus-switch__root" :disabled="disabled"><SwitchThumb class="lotus-switch__thumb"/></SwitchRoot><label v-if="label||$slots.default" :for="id"><slot>{{label}}</slot></label></span>
</template>

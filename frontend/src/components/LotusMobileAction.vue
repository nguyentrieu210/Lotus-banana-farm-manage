<script setup>
import {Button,Icon} from 'vant'
import {computed} from 'vue'
const props=defineProps({title:{type:String,required:true},icon:{type:String,default:'apps-o'},symbol:String,primary:Boolean,disabled:Boolean})
const emoji=computed(()=>props.symbol||(!/^[a-z0-9-]+$/i.test(props.icon)?props.icon:''))
const emit=defineEmits(['select','click'])
function choose(event){if(!props.disabled){emit('select',event);emit('click',event)}}
</script>
<template>
 <Button class="lotus-pwa-action" :class="{'is-primary':primary,'is-disabled':disabled}" :disabled="disabled" :aria-label="title" @click="choose">
  <span class="lotus-pwa-action-icon" aria-hidden="true"><span v-if="emoji">{{emoji}}</span><Icon v-else :name="icon"/></span>
  <strong class="lotus-pwa-action-name">{{title}}</strong>
  <Icon v-if="primary" name="arrow" class="lotus-pwa-action-arrow" aria-hidden="true"/>
 </Button>
</template>
<script setup>
import {ref} from 'vue'
import {Button} from '../button'
// A button that opens the file chooser — or the phone camera with capture="environment" — and emits the picked files.
// `as` swaps the visible button (e.g. LotusMobileButton on phone screens).
const props=defineProps({accept:String,multiple:Boolean,capture:String,disabled:Boolean,label:{type:String,required:true},variant:{type:String,default:'outline'},size:String,as:{type:[Object,String],default:()=>Button}})
const emit=defineEmits(['files'])
const input=ref(null)
function changed(event){const files=[...(event.target.files||[])];event.target.value='';if(files.length)emit('files',files)}
</script>
<template>
 <input ref="input" class="sr-only" hidden type="file" :accept="accept" :multiple="multiple" :capture="capture||undefined" :disabled="disabled" :aria-label="label" @change="changed">
 <component :is="as" type="button" :variant="variant" :size="size" :disabled="disabled" @click="input?.click()"><slot/></component>
</template>

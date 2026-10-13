<script setup>
import {cn} from '@/lib/utils'
import {normalizeInputValue} from './model.js'

defineOptions({inheritAttrs:false})
const props=defineProps({
  modelValue:{type:[String,Number],default:''},
  modelModifiers:{type:Object,default:()=>({})},
  type:{type:String,default:'text'},
  disabled:{type:Boolean,default:false},
})
const emit=defineEmits(['update:modelValue'])

function onInput(event){
  const raw=event.target.value
  // Preserve Vue's v-model.number behavior for quantities and unit prices.
  emit('update:modelValue',normalizeInputValue(raw,props.modelModifiers.number))
}
</script>
<template>
  <input
    v-bind="$attrs"
    :type="type"
    :value="modelValue??''"
    :disabled="disabled"
    :class="cn('flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',$attrs.class)"
    @input="onInput"
  />
</template>

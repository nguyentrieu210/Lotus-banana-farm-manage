<script setup>
import {computed} from 'vue'
import {cn} from '@/lib/utils'

defineOptions({inheritAttrs:false})
const props=defineProps({
  modelValue:{type:[String,Number],default:''},
  type:{type:String,default:'text'},
  disabled:{type:Boolean,default:false},
})
const emit=defineEmits(['update:modelValue'])
const value=computed(()=>props.modelValue??'')
</script>

<template>
  <input
    v-bind="$attrs"
    :type="type"
    :value="value"
    :disabled="disabled"
    :class="cn('flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50', $attrs.class)"
    @input="emit('update:modelValue',$event.target.value)"
  />
</template>

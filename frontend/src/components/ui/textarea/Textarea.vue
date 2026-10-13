<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
defineProps({modelValue:{type:String,default:''},disabled:{type:Boolean,default:false}})
const emit=defineEmits(['update:modelValue'])
</script>
<template>
  <textarea
    v-bind="$attrs"
    :value="modelValue"
    :disabled="disabled"
    :class="cn('flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50', $attrs.class)"
    @input="emit('update:modelValue',$event.target.value)"
  />
</template>

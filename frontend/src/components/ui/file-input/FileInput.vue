<script setup>
// File chooser. v-model is a File (or File[] with `multiple`); the native change event is re-emitted for callers that read event.target.files.
defineOptions({inheritAttrs:false})
const props=defineProps({accept:String,multiple:Boolean,disabled:Boolean,required:Boolean})
const emit=defineEmits(['update:modelValue','change'])
function changed(event){const files=[...(event.target.files||[])];emit('update:modelValue',props.multiple?files:files[0]||null);emit('change',event)}
</script>
<template><input v-bind="$attrs" type="file" class="lotus-file-input" :accept="accept" :multiple="multiple" :disabled="disabled" :required="required" @change="changed"></template>
<style>
.lotus-file-input{width:100%;min-height:36px;padding:6px 8px;border:1px dashed var(--lotus-border-strong);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;font-size:var(--lotus-text-sm)}
.lotus-file-input::file-selector-button{margin-right:10px;padding:4px 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;cursor:pointer}
.lotus-file-input:disabled{opacity:.5}
</style>

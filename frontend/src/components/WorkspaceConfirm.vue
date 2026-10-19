<script setup>
import WorkspaceModal from './WorkspaceModal.vue'
import {Button as UiButton} from './ui/button'
defineProps({open:Boolean,title:{type:String,default:'Xác nhận'},message:String,alertOnly:Boolean,confirmLabel:{type:String,default:'Đồng ý'}})
const emit=defineEmits(['answer'])
</script>
<template><WorkspaceModal :model-value="open" :title="title" width="480px" @update:model-value="value=>!value&&emit('answer',false)">
 <p class="workspace-confirm__message">{{message}}</p>
 <div class="workspace-confirm__actions"><UiButton v-if="!alertOnly" type="button" variant="outline" @click="emit('answer',false)">Hủy</UiButton><UiButton type="button" autofocus @click="emit('answer',true)">{{alertOnly?'Đã hiểu':confirmLabel}}</UiButton></div>
</WorkspaceModal></template>

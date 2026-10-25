<script setup>
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button as UiButton} from '../ui/button'
// The standard data-entry dialog: WorkspaceModal header, error banner, form body and a "Hủy · Lưu" footer.
// Extra buttons: #secondary (left, e.g. Xóa) and #actions (before the submit button). `readonly` shows only "Đóng".
// <ModalForm v-model="open" title="Thêm kho" :busy="saving" :error="error" @submit="save"><FormGrid>…</FormGrid></ModalForm>
const props=defineProps({modelValue:Boolean,title:{type:String,required:true},busy:Boolean,width:{type:String,default:'960px'},error:String,description:String,submitLabel:{type:String,default:'Lưu'},busyLabel:{type:String,default:'Đang lưu…'},cancelLabel:{type:String,default:'Hủy'},submitDisabled:Boolean,readonly:Boolean})
const emit=defineEmits(['update:modelValue','submit','cancel'])
function close(){if(!props.busy)emit('update:modelValue',false)}
function submit(){if(!props.busy&&!props.readonly&&!props.submitDisabled)emit('submit')}
</script>
<template>
 <WorkspaceModal :model-value="modelValue" :title="title" :busy="busy" :width="width" @update:model-value="value=>emit('update:modelValue',value)" @cancel="emit('cancel',$event)">
  <form class="lotus-modal-form" @submit.prevent="submit">
   <p v-if="description" class="lotus-modal-form__description">{{description}}</p>
   <p v-if="error" class="lotus-modal-form__error" role="alert">{{error}}</p>
   <slot/>
   <footer class="lotus-modal-form__footer">
    <div class="lotus-modal-form__secondary"><slot name="secondary"/></div>
    <UiButton type="button" variant="outline" :disabled="busy" @click="close">{{readonly?'Đóng':cancelLabel}}</UiButton>
    <slot name="actions"/>
    <UiButton v-if="!readonly" type="submit" :disabled="busy||submitDisabled">{{busy?busyLabel:submitLabel}}</UiButton>
   </footer>
  </form>
 </WorkspaceModal>
</template>
<style>
.lotus-modal-form{display:grid;gap:16px;min-width:0}
.lotus-modal-form__description{margin:0;color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-modal-form__error{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-danger-soft);color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.lotus-modal-form__footer{position:sticky;bottom:-18px;display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin:0 -20px -18px;padding:12px 20px;border-top:1px solid var(--lotus-border);background:var(--lotus-surface)}
.lotus-modal-form__secondary{display:flex;gap:8px;margin-right:auto}
@media(max-width:620px){.lotus-modal-form__footer{margin:0 -14px -14px;padding:10px 14px;bottom:-14px}}
.lotus-delete-confirm{display:grid;gap:10px;padding:12px;border:1px solid var(--lotus-danger);border-radius:var(--lotus-radius-md);background:var(--lotus-danger-soft)}
.lotus-delete-confirm p{margin:0;color:var(--lotus-danger)}
.lotus-delete-confirm__actions{display:flex;gap:8px;justify-content:flex-end}
</style>

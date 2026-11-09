<script setup>
import {onBeforeUnmount,ref,watch} from 'vue'
import ModalForm from './form/ModalForm.vue'
import {RELEASE_NOTES,latestId,unseenNotes} from '../release-notes.js'
// Tells each person what changed since they last looked. It opens by itself once per update and waits for any other dialog to finish.
const props=defineProps({user:{type:String,default:''}})
const show=ref(false),notes=ref([])
let timer
const key=()=>'lotus-release-notes-seen:'+props.user
function seen(){try{return localStorage.getItem(key())||''}catch{return ''}}
function remember(){try{localStorage.setItem(key(),latestId())}catch{/* private browsing: it simply shows again */}}
const anotherDialogOpen=()=>[...document.querySelectorAll('dialog[open],.van-popup')].some(el=>el.getClientRects().length>0)
function offer(){
 clearTimeout(timer)
 if(!props.user||props.user==='Guest')return
 const unseen=unseenNotes(RELEASE_NOTES,seen())
 if(!unseen.length)return
 if(anotherDialogOpen()){timer=setTimeout(offer,2000);return}
 notes.value=unseen;show.value=true
}
function close(value){if(!value){show.value=false;remember()}}
function open(){clearTimeout(timer);notes.value=RELEASE_NOTES;show.value=true}
watch(()=>props.user,()=>{clearTimeout(timer);timer=setTimeout(offer,1200)},{immediate:true})
onBeforeUnmount(()=>clearTimeout(timer))
defineExpose({open})
</script>

<template>
 <ModalForm :model-value="show" title="Có gì mới" width="560px" readonly @update:model-value="close">
  <section v-for="note in notes" :key="note.id" class="grid gap-3">
   <h3 class="m-0 text-base font-semibold">{{note.title}}</h3>
   <ul class="m-0 grid list-none gap-3 p-0">
    <li v-for="item in note.items" :key="item.title" class="grid gap-0.5">
     <strong class="text-sm font-semibold">{{item.title}}</strong>
     <span class="text-sm text-muted-foreground">{{item.text}}</span>
    </li>
   </ul>
  </section>
 </ModalForm>
</template>

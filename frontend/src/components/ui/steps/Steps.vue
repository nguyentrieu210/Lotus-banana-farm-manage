<script setup>
import LotusIcon from '../../LotusIcon.vue'
// Steps of an approval or signing chain (spec 004, User Story 3, scenario 6): who, when, and the state of each step.
// steps: [{label, meta?, state: 'done' | 'current' | 'waiting' | 'returned'}]
defineProps({steps:{type:Array,required:true},label:{type:String,default:'Các bước duyệt'},vertical:Boolean})
const STATE_TEXT={done:'đã xong',current:'đang chờ ở bước này',waiting:'chưa đến',returned:'trả lại'}
</script>
<template>
 <ol class="lotus-steps" :class="{'lotus-steps--vertical':vertical}" :aria-label="label">
  <li v-for="(step,index) in steps" :key="index" class="lotus-steps__item" :data-state="step.state||'waiting'" :aria-current="step.state==='current'?'step':undefined">
   <span class="lotus-steps__dot" aria-hidden="true"><LotusIcon v-if="step.state==='done'" name="tick"/><LotusIcon v-else-if="step.state==='returned'" name="undo"/><template v-else>{{index+1}}</template></span>
   <span class="lotus-steps__label">{{step.label}}<span class="lotus-sr-only">: {{STATE_TEXT[step.state||'waiting']}}</span></span>
   <span v-if="step.meta" class="lotus-steps__meta">{{step.meta}}</span>
  </li>
 </ol>
</template>

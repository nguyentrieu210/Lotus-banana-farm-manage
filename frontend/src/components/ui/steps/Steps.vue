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

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-steps{display:flex;margin:0;padding:0;list-style:none}
.lotus-steps__item{position:relative;flex:1;display:grid;grid-template-columns:26px minmax(0,1fr);grid-template-areas:"dot line" "label label" "meta meta";row-gap:4px;column-gap:8px;min-width:0;padding-right:14px}
.lotus-steps__item:not(:last-child)::after{content:"";position:absolute;top:12px;left:32px;right:8px;height:2px;border-radius:2px;background:var(--lotus-border)}
.lotus-steps__dot{grid-area:dot;z-index:1;display:grid;place-items:center;width:26px;height:26px;border:2px solid var(--lotus-border-strong);border-radius:50%;background:var(--lotus-surface);color:var(--lotus-muted);font-size:var(--lotus-text-xs);font-weight:var(--lotus-weight-bold)}
.lotus-steps__dot .lotus-icon{width:14px;height:14px;stroke-width:2.4}
.lotus-steps__label{grid-area:label;align-self:center;overflow:hidden;color:var(--lotus-text-strong);font-size:var(--lotus-text-md);font-weight:var(--lotus-weight-semibold);text-overflow:ellipsis;white-space:nowrap}
.lotus-steps__meta{grid-area:meta;color:var(--lotus-muted);font-size:var(--lotus-text-xs);line-height:var(--lotus-leading-snug)}
.lotus-steps__item[data-state="done"] .lotus-steps__dot{border-color:var(--lotus-tone-success-solid);background:var(--lotus-tone-success-solid);color:var(--lotus-tone-success-on)}
.lotus-steps__item[data-state="done"]::after{background:var(--lotus-tone-success-solid)}
.lotus-steps__item[data-state="current"] .lotus-steps__dot{border-color:var(--lotus-primary);color:var(--lotus-primary-text);box-shadow:0 0 0 3px var(--lotus-tone-primary-soft)}
.lotus-steps__item[data-state="returned"] .lotus-steps__dot{border-color:var(--lotus-tone-danger-solid);background:var(--lotus-tone-danger-soft);color:var(--lotus-tone-danger-text)}
.lotus-steps__item[data-state="waiting"] .lotus-steps__label{color:var(--lotus-muted);font-weight:var(--lotus-weight-medium)}
.lotus-steps--vertical{flex-direction:column;gap:14px}
.lotus-steps--vertical .lotus-steps__item{grid-template-areas:"dot label" "dot meta";row-gap:0;padding-right:0}
.lotus-steps--vertical .lotus-steps__item:not(:last-child)::after{top:30px;bottom:-12px;left:12px;right:auto;width:2px;height:auto}
</style>

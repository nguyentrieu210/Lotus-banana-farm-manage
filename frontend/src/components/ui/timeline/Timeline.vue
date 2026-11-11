<script setup>
import LotusIcon from '../../LotusIcon.vue'
// Events in time order (spec 004, FR-036): the life of a lot, the history of a document.
// items: [{title, time?, text?, tone?: 'success'|'warning'|'danger'|'info'|'primary', icon?}]
defineProps({items:{type:Array,required:true},label:{type:String,default:'Dòng thời gian'}})
</script>
<template>
 <ol class="lotus-timeline" :aria-label="label">
  <li v-for="(item,index) in items" :key="index" class="lotus-timeline__item" :class="item.tone?'lotus-timeline__item--'+item.tone:''">
   <span class="lotus-timeline__dot" aria-hidden="true"><LotusIcon :name="item.icon||'dot'"/></span>
   <div><div class="lotus-timeline__head"><span class="lotus-timeline__title">{{item.title}}</span><time v-if="item.time" class="lotus-timeline__time">{{item.time}}</time></div><p v-if="item.text" class="lotus-timeline__text">{{item.text}}</p><slot name="item" :item="item"/></div>
  </li>
 </ol>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-timeline{display:grid;margin:0;padding:0;list-style:none}
.lotus-timeline__item{--tl-bg:var(--lotus-tone-neutral-soft);--tl-fg:var(--lotus-tone-neutral-text);position:relative;display:grid;grid-template-columns:22px minmax(0,1fr);column-gap:10px;padding-bottom:14px}
.lotus-timeline__item:not(:last-child)::before{content:"";position:absolute;top:24px;bottom:2px;left:10px;width:2px;border-radius:2px;background:var(--lotus-border)}
.lotus-timeline__dot{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--tl-bg);color:var(--tl-fg)}
.lotus-timeline__dot .lotus-icon{width:13px;height:13px;stroke-width:2.2}
.lotus-timeline__head{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;min-width:0}
.lotus-timeline__title{color:var(--lotus-text-strong);font-weight:var(--lotus-weight-semibold)}
.lotus-timeline__time{color:var(--lotus-muted);font-size:var(--lotus-text-xs);font-variant-numeric:tabular-nums}
.lotus-timeline__text{margin:2px 0 0;color:var(--lotus-text-secondary);font-size:var(--lotus-text-md);line-height:var(--lotus-leading)}
.lotus-timeline__item--success{--tl-bg:var(--lotus-tone-success-soft);--tl-fg:var(--lotus-tone-success-text)}
.lotus-timeline__item--warning{--tl-bg:var(--lotus-tone-warning-soft);--tl-fg:var(--lotus-tone-warning-text)}
.lotus-timeline__item--danger{--tl-bg:var(--lotus-tone-danger-soft);--tl-fg:var(--lotus-tone-danger-text)}
.lotus-timeline__item--info{--tl-bg:var(--lotus-tone-info-soft);--tl-fg:var(--lotus-tone-info-text)}
.lotus-timeline__item--primary{--tl-bg:var(--lotus-tone-primary-soft);--tl-fg:var(--lotus-tone-primary-text)}
</style>

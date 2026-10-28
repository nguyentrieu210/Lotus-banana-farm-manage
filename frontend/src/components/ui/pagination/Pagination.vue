<script setup>
import {computed} from 'vue'
import {PaginationRoot,PaginationList,PaginationListItem,PaginationEllipsis,PaginationPrev,PaginationNext} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
// Offset pagination for lists. With `total` it shows numbered pages; Frappe listings usually only know
// `hasMore`, so then it shows the visible range with Trước/Tiếp. v-model:start is the row offset.
const props=defineProps({start:{type:Number,default:0},count:{type:Number,default:0},pageSize:{type:Number,default:50},total:Number,hasMore:Boolean,disabled:Boolean})
const emit=defineEmits(['update:start'])
const page=computed(()=>Math.floor(props.start/props.pageSize)+1)
const range=computed(()=>props.count?`${props.start+1}–${props.start+props.count}`:'0 bản ghi')
const go=nextPage=>emit('update:start',(nextPage-1)*props.pageSize)
</script>
<template>
 <nav class="lotus-pagination" aria-label="Phân trang">
  <span class="lotus-pagination__range" aria-live="polite">{{range}}<template v-if="total"> / {{total.toLocaleString('vi-VN')}}</template></span>
  <PaginationRoot v-if="total" :page="page" :total="total" :items-per-page="pageSize" :sibling-count="1" show-edges :disabled="disabled" @update:page="go">
   <PaginationList v-slot="{items}" class="lotus-pagination__list">
    <PaginationPrev class="lotus-pagination__button" aria-label="Trang trước"><LotusIcon name="chevron-left"/></PaginationPrev>
    <template v-for="(item,index) in items" :key="index">
     <PaginationListItem v-if="item.type==='page'" :value="item.value" :aria-label="'Trang '+item.value" class="lotus-pagination__button lotus-pagination__page">{{item.value}}</PaginationListItem>
     <PaginationEllipsis v-else :index="index" class="lotus-pagination__ellipsis">…</PaginationEllipsis>
    </template>
    <PaginationNext class="lotus-pagination__button" aria-label="Trang sau"><LotusIcon name="chevron"/></PaginationNext>
   </PaginationList>
  </PaginationRoot>
  <div v-else class="lotus-pagination__list">
   <button type="button" class="lotus-pagination__button" :disabled="disabled||!start" aria-label="Trang trước" @click="emit('update:start',Math.max(0,start-pageSize))"><LotusIcon name="chevron-left"/>Trước</button>
   <button type="button" class="lotus-pagination__button" :disabled="disabled||!hasMore" aria-label="Trang sau" @click="emit('update:start',start+pageSize)">Tiếp<LotusIcon name="chevron"/></button>
  </div>
 </nav>
</template>
<style>
.lotus-pagination{display:flex;align-items:center;justify-content:flex-end;gap:12px;flex-wrap:wrap;margin-top:12px;font-size:var(--lotus-text-md)}
.lotus-pagination__range{color:var(--lotus-muted);font-variant-numeric:tabular-nums}
.lotus-pagination__list{display:flex;align-items:center;gap:4px}
.lotus-pagination__button{display:inline-flex;align-items:center;justify-content:center;gap:4px;min-width:32px;height:32px;padding:0 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;cursor:pointer}
.lotus-pagination__button:hover:not(:disabled){background:var(--lotus-hover)}
.lotus-pagination__button:disabled{opacity:.45;cursor:default}
.lotus-pagination__button .lotus-icon{width:16px;height:16px}
.lotus-pagination__page[data-selected]{border-color:var(--lotus-primary);background:var(--lotus-primary);color:var(--lotus-on-primary)}
.lotus-pagination__ellipsis{min-width:24px;text-align:center;color:var(--lotus-muted)}
@media(min-width:721px){
 /* The desktop chat launcher sits outside App's root; keep table actions clear of its corner. */
 body:has(.ai-chat) .app-shell .lotus-pagination{padding-inline-end:calc(var(--lotus-space-6) * 6)}
}
</style>

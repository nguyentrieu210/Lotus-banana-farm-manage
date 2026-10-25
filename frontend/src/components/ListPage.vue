<script setup>
import WorkspaceListToolbar from './WorkspaceListToolbar.vue'
import WorkspaceSummaryStrip from './WorkspaceSummaryStrip.vue'
import DataTable from './DataTable.vue'
import {Pagination} from './ui/pagination'
// The standard list screen: toolbar (#filters · search · Làm mới · #actions), optional summary strip, DataTable and server pager.
// Every other attribute/listener goes to DataTable (storage-key, server-sort, filter-values, server-filters, interactive, empty, @open, @sort, @filter).
defineOptions({inheritAttrs:false})
defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,title:String,search:{type:String,default:''},searchable:{type:Boolean,default:true},searchPlaceholder:{type:String,default:'Tìm kiếm…'},summary:Array,error:String,paged:Boolean,start:{type:Number,default:0},total:Number,hasMore:Boolean,pageSize:{type:Number,default:50}})
const emit=defineEmits(['update:search','update:start','refresh'])
</script>
<template>
 <section class="lotus-list-page" :aria-label="title">
  <WorkspaceListToolbar :model-value="search" :searchable="searchable" :placeholder="searchPlaceholder" :busy="loading" @update:model-value="emit('update:search',$event)" @refresh="emit('refresh')">
   <template v-if="$slots.filters" #filters><slot name="filters"/></template>
   <slot name="actions"/>
  </WorkspaceListToolbar>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <WorkspaceSummaryStrip v-if="summary?.length" :items="summary"/>
  <slot name="before"/>
  <DataTable v-bind="$attrs" :rows="rows" :columns="columns" :loading="loading"/>
  <Pagination v-if="paged" :start="start" :count="rows.length" :total="total" :has-more="hasMore" :page-size="pageSize" :disabled="loading" @update:start="emit('update:start',$event)"/>
  <slot/>
 </section>
</template>
<style>
.lotus-list-page{display:grid;gap:10px;min-width:0}
.lotus-list-page__error{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-danger-soft);color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
</style>

<script setup>
import {computed,useSlots} from 'vue'
import WorkspaceListToolbar from './WorkspaceListToolbar.vue'
import WorkspaceSummaryStrip from './WorkspaceSummaryStrip.vue'
import DataTable from './DataTable.vue'
import {Pagination} from './ui/pagination'
// The standard list screen: toolbar (#filters · search · Làm mới · #actions), optional summary strip, DataTable and server pager.
// Every other attribute/listener goes to DataTable (storage-key, server-sort, filter-values, server-filters, interactive, empty, @open, @sort, @filter).
defineOptions({inheritAttrs:false})
defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,title:String,search:{type:String,default:''},searchable:{type:Boolean,default:true},searchPlaceholder:{type:String,default:'Tìm kiếm…'},summary:Array,error:String,paged:Boolean,start:{type:Number,default:0},total:Number,hasMore:Boolean,pageSize:{type:Number,default:50}})
const emit=defineEmits(['update:search','update:start','refresh'])
// Custom cells (#cell-<field>) pass straight through to DataTable.
const slots=useSlots()
const cellSlots=computed(()=>Object.keys(slots).filter(name=>name.startsWith('cell-')))
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
  <DataTable :fill="paged?76:24" :paginate="!paged" :page-size="pageSize" :row-index-offset="paged?start:0" v-bind="$attrs" :rows="rows" :columns="columns" :loading="loading" :totals-label="paged&&(hasMore||(total||0)>rows.length)?'Tổng trang này':'Tổng'"><template v-for="name in cellSlots" :key="name" #[name]="scope"><slot :name="name" v-bind="scope"/></template></DataTable>
  <Pagination v-if="paged" :start="start" :count="rows.length" :total="total" :has-more="hasMore" :page-size="pageSize" :disabled="loading" @update:start="emit('update:start',$event)"/>
  <slot/>
 </section>
</template>
<style>
.lotus-list-page{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;min-width:0}
/* Narrow screens: filters and actions wrap onto new lines instead of widening the page. */
.lotus-list-page__error{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-danger-soft);color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
</style>

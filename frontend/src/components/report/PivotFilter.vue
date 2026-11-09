<script setup>
import {computed,ref} from 'vue'
import {Popover,PopoverTrigger,PopoverContent} from '../ui/popover'
import {Checkbox} from '../ui/checkbox'
import {Button as UiButton} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
import {allTicked,buttonLabel,isFiltered,isTicked,matches,toggle,toggleAll} from '../../pivot-filter.js'
import './report.css'
// One button per field, each a tick list like an Excel pivot filter. Lists come from the server and narrow as other fields are chosen.
const props=defineProps({fields:{type:Array,required:true},options:{type:Object,default:()=>({})}})
const selection=defineModel({type:Object,required:true})
const search=ref({})
const active=computed(()=>Object.keys(selection.value).length>0)
const shown=field=>(props.options[field]||[]).filter(o=>matches(o,search.value[field]))
</script>

<template>
 <div class="pivot-filter" role="group" aria-label="Bộ lọc báo cáo">
  <Popover v-for="f in fields" :key="f.id">
   <PopoverTrigger as-child>
    <UiButton type="button" variant="outline" size="sm" class="pivot-filter__button" :class="{'is-on':isFiltered(selection,f.id)}">{{buttonLabel(f.label,selection,f.id)}}<LotusIcon name="chevron-down"/></UiButton>
   </PopoverTrigger>
   <PopoverContent align="start" :side-offset="6" class="pivot-filter__panel">
    <input v-if="(options[f.id]||[]).length>8" v-model="search[f.id]" class="pivot-filter__search" type="search" placeholder="Tìm…" :aria-label="'Tìm trong '+f.label">
    <label class="pivot-filter__row is-all"><Checkbox :model-value="allTicked(selection,f.id)" @update:model-value="selection=toggleAll(selection,f.id)"/><span>(Chọn tất cả)</span></label>
    <div class="pivot-filter__list">
     <label v-for="o in shown(f.id)" :key="o.value" class="pivot-filter__row"><Checkbox :model-value="isTicked(selection,f.id,o.value)" @update:model-value="selection=toggle(selection,f.id,o.value,options[f.id])"/><span>{{o.label}}</span></label>
     <p v-if="!shown(f.id).length" class="pivot-filter__empty">Không có giá trị nào.</p>
    </div>
   </PopoverContent>
  </Popover>
  <UiButton v-if="active" type="button" variant="ghost" size="sm" @click="selection={}">Bỏ lọc</UiButton>
  <div class="pivot-filter__tools"><slot/></div>
 </div>
</template>

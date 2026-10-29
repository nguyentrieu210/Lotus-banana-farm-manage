<script setup>
import {computed} from 'vue'
import LotusField from './LotusField.vue'
import {Button as UiButton} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
// Editable document lines for every form (phiếu kho, đơn mua, hóa đơn, bút toán…). v-model is the row array; rows are edited in place.
// columns: [{field,label,type,options,fetchOptions,searchable,required,readonly,disabled,hint,displayValue,visible,props,width,onSelect}]
// Keys may be functions of the row (options, required, readonly, disabled, hint, displayValue, visible, props).
// Custom cell: <template #cell-area="{row,index}">…</template>. Desktop shows a grid with one header row; `mobile` shows one card per row.
const props=defineProps({
 modelValue:{type:Array,required:true},columns:{type:Array,required:true},newRow:{type:Function,default:()=>({})},
 title:{type:String,default:'Chi tiết'},addLabel:{type:String,default:'Thêm dòng'},max:{type:Number,default:100},min:{type:Number,default:1},
 readonly:Boolean,fixed:Boolean,mobile:Boolean,emptyText:{type:String,default:'Chưa có dòng nào.'}
})
const emit=defineEmits(['update:modelValue','select','remove'])
const at=(value,row)=>typeof value==='function'?value(row):value
const editable=computed(()=>!props.readonly&&!props.fixed)
const template=computed(()=>props.columns.map(c=>c.width||'minmax(120px,1fr)').join(' ')+(editable.value?' 36px':''))
function add(){emit('update:modelValue',[...props.modelValue,props.newRow()])}
function remove(index){const rows=props.modelValue.slice();const [row]=rows.splice(index,1);emit('update:modelValue',rows);emit('remove',row)}
function select(column,row,option){column.onSelect?.(row,option);emit('select',{row,field:column.field,option})}
</script>

<template>
 <section class="lotus-lines" :class="{'lotus-lines--mobile':mobile}" :aria-label="title">
  <header class="lotus-lines__header"><h3>{{title}}</h3><span>{{modelValue.length}} dòng</span></header>
  <p v-if="!modelValue.length" class="lotus-lines__empty">{{emptyText}}</p>
  <div v-else class="lotus-lines__grid" :style="{'--lotus-lines-template':template}">
   <div v-if="!mobile" class="lotus-lines__head" aria-hidden="true"><span v-for="c in columns" :key="c.field">{{c.label}}<span v-if="c.required===true" class="lotus-field__required">*</span></span><span v-if="editable"/></div>
   <div v-for="(row,index) in modelValue" :key="row._key||row.name||index" class="lotus-lines__row">
    <span v-if="mobile" class="lotus-lines__number">Dòng {{index+1}}</span>
    <div v-for="c in columns" :key="c.field" class="lotus-lines__cell" :class="'lotus-lines__cell--'+c.field">
     <template v-if="at(c.visible??true,row)">
      <slot :name="'cell-'+c.field" :row="row" :index="index" :column="c">
       <LotusField :label="mobile?c.label:undefined" :aria-label="c.label+' dòng '+(index+1)" :type="c.type||'text'" :options="at(c.options,row)" :fetch-options="c.fetchOptions" :searchable="c.searchable" :display-value="at(c.displayValue,row)" :required="!!at(c.required,row)" :readonly="readonly||!!at(c.readonly,row)" :disabled="!!at(c.disabled,row)" :hint="at(c.hint,row)" :mobile="mobile" v-bind="at(c.props,row)||{}" :model-value="row[c.field]" @update:model-value="value=>{row[c.field]=value}" @select="option=>select(c,row,option)"/>
      </slot>
     </template>
    </div>
    <UiButton v-if="editable" type="button" variant="ghost" class="lotus-lines__remove" :disabled="modelValue.length<=min" :aria-label="'Xóa dòng '+(index+1)" @click="remove(index)"><LotusIcon name="trash"/></UiButton>
   </div>
  </div>
  <div v-if="editable||$slots.footer" class="lotus-lines__footer"><UiButton v-if="editable" type="button" variant="outline" size="sm" :disabled="modelValue.length>=max" @click="add"><LotusIcon name="plus"/>{{addLabel}}</UiButton><slot name="footer"/></div>
 </section>
</template>

<style>
.lotus-lines{display:grid;gap:10px;min-width:0}
.lotus-lines__header{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.lotus-lines__header h3{margin:0;font-size:var(--lotus-text-md);font-weight:600;color:var(--lotus-text-strong)}
.lotus-lines__header span,.lotus-lines__empty{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-lines__empty{margin:0}
.lotus-lines__grid{display:grid;gap:8px;min-width:0;overflow-x:auto}
.lotus-lines__head,.lotus-lines__row{display:grid;grid-template-columns:var(--lotus-lines-template);gap:8px;align-items:start;min-width:min-content}
.lotus-lines__head{padding:0 0 2px;font-size:var(--lotus-text-sm);font-weight:550;color:var(--lotus-muted)}
.lotus-lines__cell{min-width:0}
/* Controls fill their column; the legacy stock.css `select{min-width:210px}` must not push them over the next cell. */
.lotus-lines__cell :is(select,input,textarea){min-width:0;max-width:100%}
.lotus-lines__remove{align-self:start;width:36px;height:36px;padding:0}
.lotus-lines__footer{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.lotus-lines__total{margin-left:auto}
.lotus-lines--mobile .lotus-lines__grid{gap:12px;overflow:visible}
.lotus-lines--mobile .lotus-lines__row{grid-template-columns:minmax(0,1fr);position:relative;padding:12px 0;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);min-width:0}
.lotus-lines--mobile .lotus-lines__number{padding:0 var(--lotus-space-4);font-weight:600;font-size:var(--lotus-text-sm)}
.lotus-lines--mobile .lotus-lines__remove{position:absolute;top:4px;right:4px}
.lotus-lines--mobile .lotus-lines__cell:empty{display:none}
</style>

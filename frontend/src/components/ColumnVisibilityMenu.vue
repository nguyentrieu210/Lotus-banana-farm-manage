<script setup>
import {computed,ref} from 'vue'
import {Button as UiButton} from './ui/button'
import {Popover,PopoverTrigger,PopoverContent} from './ui/popover'
import LotusIcon from './LotusIcon.vue'
import {columnId,selectableColumns,normalizeColumnLayout} from '../grid-visibility'

const props=defineProps({columns:{type:Array,required:true},layout:{type:Object,default:()=>({})},presets:{type:Array,default:()=>[]}})
const emit=defineEmits(['toggle','reset','all','move','pin','preset'])
const query=ref('')
const normalized=computed(()=>normalizeColumnLayout(props.columns,props.layout))
const choices=computed(()=>{
 const map=new Map(selectableColumns(props.columns).map(col=>[columnId(col),col]))
 return normalized.value.order.map(id=>map.get(id)).filter(Boolean)
})
const results=computed(()=>choices.value.filter(c=>String(c.headerName||columnId(c)).toLocaleLowerCase('vi').includes(query.value.trim().toLocaleLowerCase('vi'))))
const visibleCount=computed(()=>choices.value.length-normalized.value.hidden.length)
const isVisible=id=>!normalized.value.hidden.includes(id)
const isPinned=id=>normalized.value.pinned.includes(id)
</script>
<template>
 <Popover>
  <PopoverTrigger as-child>
   <UiButton type="button" variant="outline" size="sm" aria-label="Tùy chỉnh cột của bảng" class="lotus-column-picker-trigger"><LotusIcon name="sliders"/>Cột hiển thị<span v-if="normalized.hidden.length" class="lotus-column-picker-trigger__count">{{normalized.hidden.length}} ẩn</span></UiButton>
  </PopoverTrigger>
  <PopoverContent align="end" side-offset="8" class="lotus-column-picker">
   <div class="lotus-column-picker__header">
    <div><strong>Tùy chỉnh cột</strong><small>{{visibleCount}} / {{choices.length}} cột đang hiện</small></div>
    <button type="button" class="lotus-column-picker__reset" @click="emit('reset')">Mặc định</button>
   </div>
   <div class="lotus-column-picker__searchbox">
    <LotusIcon name="search"/>
    <input v-model="query" type="search" aria-label="Tìm tên cột" placeholder="Tìm tên cột..." autocomplete="off"/>
   </div>
   <div v-if="presets.length" class="lotus-column-picker__presets" aria-label="Kiểu xem nhanh">
    <button v-for="preset in presets" :key="preset.id" type="button" @click="emit('preset',preset.id)">{{preset.label}}</button>
   </div>
   <div class="lotus-column-picker__actions">
    <button type="button" @click="emit('all')">Hiện tất cả</button>
    <span>Ghim tối đa 2 cột</span>
   </div>
   <div class="lotus-column-picker__items" role="group" aria-label="Danh sách cột có thể tùy chỉnh">
    <div v-for="(col,index) in results" :key="columnId(col)" class="lotus-column-picker__item">
     <button type="button" class="lotus-column-picker__toggle" :aria-pressed="isVisible(columnId(col))" :aria-label="(isVisible(columnId(col))?'Ẩn ':'Hiện ')+(col.headerName||columnId(col))" :disabled="isVisible(columnId(col))&&visibleCount===1" @click="emit('toggle',columnId(col))">
      <span class="lotus-column-picker__check" :class="{'is-on':isVisible(columnId(col))}"><LotusIcon v-if="isVisible(columnId(col))" name="tick"/></span>
      <span class="lotus-column-picker__label">{{col.headerName||columnId(col)}}</span>
     </button>
     <button type="button" class="lotus-column-picker__mini" :class="{'is-on':isPinned(columnId(col))}" :disabled="!isVisible(columnId(col))||(!isPinned(columnId(col))&&normalized.pinned.length>=2)" :aria-label="(isPinned(columnId(col))?'Bỏ ghim ':'Ghim ')+(col.headerName||columnId(col))" :title="isPinned(columnId(col))?'Bỏ ghim':'Ghim bên trái'" @click="emit('pin',columnId(col))"><LotusIcon name="flag"/></button>
     <button type="button" class="lotus-column-picker__mini" :disabled="normalized.order.indexOf(columnId(col))===0" :aria-label="'Đưa '+(col.headerName||columnId(col))+' lên trên'" title="Đưa lên" @click="emit('move',columnId(col),-1)"><LotusIcon name="chevron-down" class="is-up"/></button>
     <button type="button" class="lotus-column-picker__mini" :disabled="normalized.order.indexOf(columnId(col))===normalized.order.length-1" :aria-label="'Đưa '+(col.headerName||columnId(col))+' xuống dưới'" title="Đưa xuống" @click="emit('move',columnId(col),1)"><LotusIcon name="chevron-down"/></button>
    </div>
    <p v-if="!results.length" class="lotus-column-picker__empty">Không tìm thấy tên cột phù hợp.</p>
   </div>
   <div class="lotus-column-picker__footer">Thay đổi áp dụng ngay và được ghi nhớ trên trình duyệt.</div>
  </PopoverContent>
 </Popover>
</template>
<style>
/* Portal-rendered panel: keep every row horizontal, even under farm/form global CSS. */
.lotus-column-picker.lotus-popover{box-sizing:border-box;width:min(390px,calc(100vw - 24px));min-width:0;padding:0!important;overflow:hidden}
.lotus-column-picker *{box-sizing:border-box}
.lotus-column-picker__header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 14px 8px}
.lotus-column-picker__header>div{display:flex;flex-direction:column;gap:2px;min-width:0}
.lotus-column-picker__header strong{font-weight:650;font-size:14px}
.lotus-column-picker__header small{font-size:12px;color:var(--lotus-muted)}
.lotus-column-picker button{font:inherit;color:inherit;cursor:pointer}
.lotus-column-picker button:disabled{cursor:not-allowed;opacity:.38}
.lotus-column-picker__reset{background:transparent;border:0;padding:6px;color:var(--lotus-primary)!important;font-size:12px!important}
.lotus-column-picker__searchbox{display:flex!important;align-items:center!important;flex-direction:row!important;gap:8px;margin:6px 12px 8px;padding:0 10px;height:38px;border:1px solid var(--lotus-border);border-radius:8px;background:var(--lotus-surface)}
.lotus-column-picker__searchbox>.lotus-icon{width:16px;height:16px;flex:none;color:var(--lotus-muted)}
.lotus-column-picker__searchbox input{flex:1 1 auto!important;display:block!important;min-width:0!important;width:100%!important;height:34px!important;max-height:34px!important;padding:0!important;margin:0!important;border:0!important;outline:0!important;box-shadow:none!important;background:transparent!important;font:inherit!important;font-size:13px!important;line-height:34px!important;color:var(--lotus-text)!important}
.lotus-column-picker__searchbox:focus-within{border-color:var(--lotus-primary)}
.lotus-column-picker__presets{display:flex;gap:6px;flex-wrap:wrap;padding:0 12px 9px}
.lotus-column-picker__presets>button{border:1px solid var(--lotus-border);border-radius:7px;background:var(--lotus-soft);padding:5px 9px;font-size:12px!important}
.lotus-column-picker__actions{display:flex;align-items:center;justify-content:space-between;padding:3px 14px 8px;font-size:12px;color:var(--lotus-muted)}
.lotus-column-picker__actions button{background:transparent;border:0;padding:4px 0;color:var(--lotus-primary);font-size:12px}
.lotus-column-picker__items{display:block!important;max-height:min(365px,49vh);min-height:44px;overflow-y:auto;overscroll-behavior:contain;padding:0 8px 5px;scrollbar-width:thin}
.lotus-column-picker__item{display:grid!important;grid-template-columns:minmax(0,1fr) 28px 28px 28px!important;align-items:center!important;gap:3px!important;min-height:40px!important;width:100%!important;max-width:100%!important;margin:0!important;padding:0 3px!important;border-radius:7px}
.lotus-column-picker__item:hover{background:var(--lotus-soft)}
.lotus-column-picker__toggle{display:flex!important;flex-direction:row!important;align-items:center!important;justify-content:flex-start!important;gap:9px!important;min-width:0!important;min-height:36px!important;width:100%!important;padding:4px 5px!important;border:0!important;background:transparent!important;text-align:left!important}
.lotus-column-picker__check{display:inline-flex!important;align-items:center!important;justify-content:center!important;width:17px!important;height:17px!important;min-width:17px!important;min-height:17px!important;border:1px solid var(--lotus-border);border-radius:4px;flex:none;background:var(--lotus-surface)}
.lotus-column-picker__check.is-on{border-color:var(--lotus-primary);background:var(--lotus-primary);color:white}
.lotus-column-picker__check .lotus-icon{width:13px!important;height:13px!important}
.lotus-column-picker__label{display:block!important;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px!important;font-weight:400!important}
.lotus-column-picker__mini{display:inline-flex!important;align-items:center!important;justify-content:center!important;width:27px!important;height:29px!important;min-width:27px!important;min-height:29px!important;margin:0!important;padding:0!important;border:0!important;border-radius:6px;background:transparent!important}
.lotus-column-picker__mini:hover:not(:disabled){background:var(--lotus-hover)!important}
.lotus-column-picker__mini.is-on{color:var(--lotus-primary)!important}
.lotus-column-picker__mini .lotus-icon{width:15px!important;height:15px!important}
.lotus-column-picker__mini .is-up{transform:rotate(180deg)}
.lotus-column-picker__empty{padding:12px;text-align:center;color:var(--lotus-muted);font-size:12px}
.lotus-column-picker__footer{padding:9px 13px 12px;border-top:1px solid var(--lotus-border);font-size:11px;color:var(--lotus-muted)}
.lotus-column-picker-trigger__count{font-size:11px;color:var(--lotus-muted)}
</style>

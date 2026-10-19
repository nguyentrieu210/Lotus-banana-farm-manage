<script setup>
import {computed,ref} from 'vue'
import {DateRangePickerRoot,DateRangePickerField,DateRangePickerInput,DateRangePickerTrigger,DateRangePickerContent,DateRangePickerCalendar,DateRangePickerHeader,DateRangePickerPrev,DateRangePickerHeading,DateRangePickerNext,DateRangePickerGrid,DateRangePickerGridHead,DateRangePickerGridBody,DateRangePickerGridRow,DateRangePickerHeadCell,DateRangePickerCell,DateRangePickerCellTrigger} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
import {useDialogPortal} from '../portal-target'
import {toCalendarDate,fromCalendarDate,todayValue} from './date-value'
import {rangePresets} from './range-presets'
// One control for "Từ ngày – Đến ngày": type either end or pick both on a two-month calendar, with quick ranges.
// v-model:from / v-model:to are Frappe 'YYYY-MM-DD' strings ('' = open-ended).
defineOptions({inheritAttrs:false})
const props=defineProps({from:{type:String,default:''},to:{type:String,default:''},disabled:Boolean,label:{type:String,default:'Khoảng ngày'},presets:{type:Boolean,default:true}})
const emit=defineEmits(['update:from','update:to','change'])
const root=ref(null),open=ref(false),portal=ref({to:'body'})
const target=useDialogPortal()
const value=computed(()=>({start:toCalendarDate(props.from),end:toCalendarDate(props.to)}))
function apply(start,end){
 if(start===props.from&&end===props.to)return
 emit('update:from',start);emit('update:to',end);emit('change',{from:start,to:end})
}
function set(range){
 const start=fromCalendarDate(range?.start),end=fromCalendarDate(range?.end)
 // only commit once both ends are chosen, or when the range was cleared
 if((start&&end)||(!start&&!end))apply(start,end)
}
function setOpen(next){if(next)portal.value={to:target(root.value)};open.value=next}
function choose(preset){const [start,end]=preset.range(todayValue());apply(start,end);open.value=false}
</script>
<template>
 <div ref="root" class="lotus-date lotus-date--range" :class="$attrs.class">
  <DateRangePickerRoot :model-value="value" :open="open" locale="vi-VN" :week-starts-on="1" fixed-weeks :number-of-months="2" :disabled="disabled" @update:model-value="set" @update:open="setOpen">
   <DateRangePickerField v-slot="{segments}" class="lotus-date__field" :aria-label="$attrs['aria-label']||label">
    <template v-for="item in segments.start" :key="'s'+item.part">
     <DateRangePickerInput type="start" :part="item.part" :class="item.part==='literal'?'lotus-date__literal':'lotus-date__segment'">{{item.value}}</DateRangePickerInput>
    </template>
    <span class="lotus-date__dash" aria-hidden="true">–</span>
    <template v-for="item in segments.end" :key="'e'+item.part">
     <DateRangePickerInput type="end" :part="item.part" :class="item.part==='literal'?'lotus-date__literal':'lotus-date__segment'">{{item.value}}</DateRangePickerInput>
    </template>
    <DateRangePickerTrigger class="lotus-date__trigger" aria-label="Mở lịch chọn khoảng ngày"><LotusIcon name="calendar"/></DateRangePickerTrigger>
   </DateRangePickerField>
   <DateRangePickerContent class="lotus-date__content lotus-date__content--range" :side-offset="4" align="start" :portal="portal">
    <nav v-if="presets" class="lotus-date__presets" aria-label="Khoảng nhanh"><button v-for="preset in rangePresets" :key="preset.id" type="button" @click="choose(preset)">{{preset.label}}</button><button type="button" @click="apply('','');open=false">Bỏ chọn</button></nav>
    <DateRangePickerCalendar v-slot="{weekDays,grid}" class="lotus-calendar">
     <DateRangePickerHeader class="lotus-calendar__header">
      <DateRangePickerPrev class="lotus-calendar__nav" aria-label="Tháng trước"><LotusIcon name="chevron-left"/></DateRangePickerPrev>
      <DateRangePickerHeading class="lotus-calendar__heading"/>
      <DateRangePickerNext class="lotus-calendar__nav" aria-label="Tháng sau"><LotusIcon name="chevron"/></DateRangePickerNext>
     </DateRangePickerHeader>
     <div class="lotus-calendar__months">
      <DateRangePickerGrid v-for="month in grid" :key="month.value.toString()" class="lotus-calendar__grid">
       <DateRangePickerGridHead><DateRangePickerGridRow class="lotus-calendar__row"><DateRangePickerHeadCell v-for="day in weekDays" :key="day" class="lotus-calendar__weekday">{{day}}</DateRangePickerHeadCell></DateRangePickerGridRow></DateRangePickerGridHead>
       <DateRangePickerGridBody>
        <DateRangePickerGridRow v-for="(week,index) in month.rows" :key="index" class="lotus-calendar__row">
         <DateRangePickerCell v-for="day in week" :key="day.toString()" :date="day"><DateRangePickerCellTrigger :day="day" :month="month.value" class="lotus-calendar__day"/></DateRangePickerCell>
        </DateRangePickerGridRow>
       </DateRangePickerGridBody>
      </DateRangePickerGrid>
     </div>
    </DateRangePickerCalendar>
   </DateRangePickerContent>
  </DateRangePickerRoot>
 </div>
</template>

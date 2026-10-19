<script setup>
import {computed,ref} from 'vue'
import {DatePickerRoot,DatePickerField,DatePickerInput,DatePickerTrigger,DatePickerContent,DatePickerCalendar,DatePickerHeader,DatePickerPrev,DatePickerHeading,DatePickerNext,DatePickerGrid,DatePickerGridHead,DatePickerGridBody,DatePickerGridRow,DatePickerHeadCell,DatePickerCell,DatePickerCellTrigger} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
import {useDialogPortal} from '../portal-target'
import {toCalendarDate,fromCalendarDate,todayValue} from './date-value'
// Date field you can type into (dd/mm/yyyy segments) or pick from a calendar. v-model is Frappe 'YYYY-MM-DD'.
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:String,default:''},min:String,max:String,disabled:Boolean,readonly:Boolean,required:Boolean,label:String,clearable:{type:Boolean,default:true}})
const emit=defineEmits(['update:modelValue','change'])
const root=ref(null),open=ref(false),portal=ref({to:'body'})
const target=useDialogPortal()
const value=computed(()=>toCalendarDate(props.modelValue))
function set(date){const next=fromCalendarDate(date);if(next===props.modelValue)return;emit('update:modelValue',next);emit('change',next)}
function setOpen(next){if(next)portal.value={to:target(root.value)};open.value=next}
function pick(text){set(toCalendarDate(text));open.value=false}
</script>
<template>
 <div ref="root" class="lotus-date" :class="$attrs.class">
  <DatePickerRoot :model-value="value" :open="open" locale="vi-VN" :week-starts-on="1" fixed-weeks :min-value="toCalendarDate(min)" :max-value="toCalendarDate(max)" :disabled="disabled" :readonly="readonly" :required="required" @update:model-value="set" @update:open="setOpen">
   <DatePickerField v-slot="{segments}" class="lotus-date__field" :aria-label="$attrs['aria-label']||label" :aria-describedby="$attrs['aria-describedby']" :aria-invalid="$attrs['aria-invalid']" :id="$attrs.id">
    <template v-for="item in segments" :key="item.part">
     <DatePickerInput v-if="item.part==='literal'" :part="item.part" class="lotus-date__literal">{{item.value}}</DatePickerInput>
     <DatePickerInput v-else :part="item.part" class="lotus-date__segment">{{item.value}}</DatePickerInput>
    </template>
    <DatePickerTrigger class="lotus-date__trigger" aria-label="Mở lịch"><LotusIcon name="calendar"/></DatePickerTrigger>
   </DatePickerField>
   <DatePickerContent class="lotus-date__content" :side-offset="4" align="start" :portal="portal">
    <DatePickerCalendar v-slot="{weekDays,grid}" class="lotus-calendar">
     <DatePickerHeader class="lotus-calendar__header">
      <DatePickerPrev class="lotus-calendar__nav" aria-label="Tháng trước"><LotusIcon name="chevron-left"/></DatePickerPrev>
      <DatePickerHeading class="lotus-calendar__heading"/>
      <DatePickerNext class="lotus-calendar__nav" aria-label="Tháng sau"><LotusIcon name="chevron"/></DatePickerNext>
     </DatePickerHeader>
     <DatePickerGrid v-for="month in grid" :key="month.value.toString()" class="lotus-calendar__grid">
      <DatePickerGridHead><DatePickerGridRow class="lotus-calendar__row"><DatePickerHeadCell v-for="day in weekDays" :key="day" class="lotus-calendar__weekday">{{day}}</DatePickerHeadCell></DatePickerGridRow></DatePickerGridHead>
      <DatePickerGridBody>
       <DatePickerGridRow v-for="(week,index) in month.rows" :key="index" class="lotus-calendar__row">
        <DatePickerCell v-for="day in week" :key="day.toString()" :date="day"><DatePickerCellTrigger :day="day" :month="month.value" class="lotus-calendar__day"/></DatePickerCell>
       </DatePickerGridRow>
      </DatePickerGridBody>
     </DatePickerGrid>
    </DatePickerCalendar>
    <footer class="lotus-calendar__footer"><button type="button" @click="pick(todayValue())">Hôm nay</button><button v-if="clearable&&!required" type="button" @click="pick('')">Xóa</button></footer>
   </DatePickerContent>
  </DatePickerRoot>
 </div>
</template>

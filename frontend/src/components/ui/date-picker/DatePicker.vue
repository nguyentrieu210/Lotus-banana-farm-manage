<script setup>
import {computed,ref,watch} from 'vue'
import {DatePickerRoot,DatePickerTrigger,DatePickerContent,DatePickerCalendar,DatePickerHeader,DatePickerPrev,DatePickerHeading,DatePickerNext,DatePickerGrid,DatePickerGridHead,DatePickerGridBody,DatePickerGridRow,DatePickerHeadCell,DatePickerCell,DatePickerCellTrigger} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
import {useDialogPortal} from '../portal-target'
import {toCalendarDate,fromCalendarDate,todayValue,formatDateInput,parseDateInput} from './date-value'
// One text field accepts typing/paste in dd/mm/yyyy; the shared Reka calendar keeps ISO v-model.
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:String,default:''},min:String,max:String,disabled:Boolean,readonly:Boolean,required:Boolean,label:String,clearable:{type:Boolean,default:true}})
const emit=defineEmits(['update:modelValue','change'])
const root=ref(null),open=ref(false),portal=ref({to:'body'})
const input=ref(null),draft=ref(formatDateInput(props.modelValue))
const target=useDialogPortal()
const value=computed(()=>toCalendarDate(props.modelValue))
const error=computed(()=>{
 if(!draft.value.trim())return ''
 const iso=parseDateInput(draft.value)
 if(!iso)return 'Nhập ngày hợp lệ theo dd/mm/yyyy.'
 if(props.min&&iso<props.min)return 'Ngày phải từ '+formatDateInput(props.min)+'.'
 if(props.max&&iso>props.max)return 'Ngày không được sau '+formatDateInput(props.max)+'.'
 return ''
})
watch([error,input],()=>input.value?.setCustomValidity(error.value),{flush:'post'})
watch(()=>props.modelValue,next=>{
 if(next===lastEmitted){lastEmitted=undefined;return}
 draft.value=formatDateInput(next)
})
let lastEmitted
function emitValue(next){if(next===props.modelValue)return;lastEmitted=next;emit('update:modelValue',next);emit('change',next)}
function type(event){
 draft.value=event.target.value
 // A partial/invalid replacement must never leave the previous date in the save payload.
 emitValue(error.value?'':parseDateInput(draft.value))
}
function normalize(){if(!error.value)draft.value=formatDateInput(parseDateInput(draft.value))}
function set(date){draft.value=formatDateInput(fromCalendarDate(date));emitValue(fromCalendarDate(date));open.value=false}
function setOpen(next){if(next)portal.value={to:target(root.value)};open.value=next}
function pick(text){set(toCalendarDate(text));open.value=false}
</script>
<template>
 <div ref="root" class="lotus-date" :class="$attrs.class">
  <DatePickerRoot :model-value="value" :open="open" locale="vi-VN" :week-starts-on="1" fixed-weeks :min-value="toCalendarDate(min)" :max-value="toCalendarDate(max)" :disabled="disabled" :readonly="readonly" :required="required" @update:model-value="set" @update:open="setOpen">
   <div class="lotus-date__field" :aria-invalid="!!error||$attrs['aria-invalid']" :data-disabled="disabled?'':undefined">
    <input ref="input" class="lotus-date__input" type="text" :value="draft" placeholder="dd/mm/yyyy" inputmode="numeric" autocomplete="off" :disabled="disabled" :readonly="readonly" :required="required" :aria-label="$attrs['aria-label']||label" :aria-describedby="$attrs['aria-describedby']" :aria-invalid="!!error||$attrs['aria-invalid']" :id="$attrs.id" :name="$attrs.name" @input="type" @blur="normalize"/>
    <DatePickerTrigger class="lotus-date__trigger" aria-label="Mở lịch" :disabled="disabled||readonly"><LotusIcon name="calendar"/></DatePickerTrigger>
   </div>
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
    <footer class="lotus-calendar__footer"><button type="button" :disabled="!!min&&todayValue()<min||!!max&&todayValue()>max" @click="pick(todayValue())">Hôm nay</button><button v-if="clearable&&!required" type="button" @click="pick('')">Xóa</button></footer>
   </DatePickerContent>
  </DatePickerRoot>
 </div>
</template>

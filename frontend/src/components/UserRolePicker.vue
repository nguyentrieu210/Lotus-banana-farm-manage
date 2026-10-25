<script setup>
import {Checkbox} from './ui/checkbox'
import LotusField from './form/LotusField.vue'
import {computed,ref} from 'vue'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import FormField from './ui/form-field/FormField.vue'
import {filterRoles} from '../user-access'
const props=defineProps({roles:{type:Array,default:()=>[]},modelValue:{type:Array,default:()=>[]},effectiveRoles:{type:Array,default:()=>[]},disabled:Boolean})
const emit=defineEmits(['update:modelValue'])
const query=ref(''),group=ref(''),onlySelected=ref(false)
const visible=computed(()=>filterRoles(props.roles,query.value,group.value,props.modelValue,onlySelected.value))
const chosen=role=>props.modelValue.includes(role.name)||(role.automatic&&props.effectiveRoles.includes(role.name))
function toggle(role,checked){if(props.disabled||!role.assignable)return;const next=new Set(props.modelValue);checked?next.add(role.name):next.delete(role.name);emit('update:modelValue',[...next])}
</script>
<template><section aria-label="Danh sách vai trò">
 <div class="hr-form-grid">
  <FormField label="Tìm vai trò" v-slot="f"><UiInput v-bind="f" v-model="query" type="search" placeholder="Tên tiếng Việt hoặc mã vai trò…"/></FormField>
  <FormField label="Nhóm vai trò" v-slot="f"><UiSelect v-bind="f" v-model="group" :searchable="false"><option value="">Tất cả nhóm</option><option value="Lotus">Lotus</option><option value="ERPNext">ERPNext</option></UiSelect></FormField>
 </div>
 <LotusField type="checkbox" label="Chỉ vai trò đã gán" v-model="onlySelected"/>
 <p class="user-hint" role="status">Hiển thị {{visible.length}} / {{roles.length}} vai trò · {{modelValue.length}} vai trò đã gán</p>
 <p v-if="roles.some(r=>r.disabled&&modelValue.includes(r.name))" class="user-hint">ERPNext sẽ gỡ các vai trò đã khóa khỏi hồ sơ khi lưu; các vai trò này không còn cấp quyền.</p>
 <div class="user-choice-grid"><label v-for="role in visible" :key="role.name" class="user-choice"><Checkbox :model-value="chosen(role)" :disabled="disabled||!role.assignable" @update:model-value="value=>toggle(role,value)"/><span>{{role.label}}<small>{{role.name}} · {{role.group}}{{role.automatic?' · Tự động theo hệ thống':role.disabled?' · Đã khóa':''}}</small></span></label></div>
 <p v-if="!visible.length" class="stock-empty">Không có vai trò phù hợp.</p>
</section></template>

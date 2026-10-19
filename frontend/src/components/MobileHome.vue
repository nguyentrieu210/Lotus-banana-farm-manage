<script setup>
import {Button as UiButton} from './ui/button'
import {computed,ref} from 'vue'
import {Input as UiInput} from './ui/input'
import {Card as UiCard} from './ui/card'
import {mobileGroups} from '../mobile-menu'
const props=defineProps({session:{type:Object,required:true},farm:{type:String,default:''},online:{type:Boolean,default:true},queued:{type:Number,default:0}})
const emit=defineEmits(['select','outbox'])
const groups=computed(()=>mobileGroups(props.session))
const search=ref('')
const normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const filteredGroups=computed(()=>groups.value.map(group=>({...group,actions:group.actions.filter(action=>normalize(action.label+' '+action.detail).includes(normalize(search.value)))})).filter(group=>group.actions.length))
const farmName=computed(()=>props.session.farms?.find(f=>f.name===props.farm)?.farm_name||props.farm||'Tất cả vườn được phân quyền')
</script>

<template>
 <section class="mobile-home" aria-label="Công việc của bạn">
  <UiCard class="mobile-welcome">
   <div><h2>Không gian làm việc</h2><p>{{farmName}}</p></div>
   <UiInput v-model="search" type="search" aria-label="Tìm chức năng" placeholder="Tìm chức năng…"/>
  </UiCard>
  <section v-for="group in filteredGroups" :key="group.title" class="mobile-action-section">
   <h3>{{group.title}} <span>{{group.actions.length}}</span></h3>
   <div class="mobile-action-grid">
    <UiButton variant="outline" v-for="action in group.actions" :key="action.id" class="mobile-action" type="button" @click="emit('select',action)">
     <span class="mobile-action-icon" aria-hidden="true">{{action.symbol}}</span>
     <span class="mobile-action-text"><strong>{{action.label}}</strong><small>{{action.detail}}</small></span>
     <span aria-hidden="true" class="mobile-action-chevron">›</span>
    </UiButton>
   </div>
  </section>
  <p v-if="!groups.length" class="notice">Tài khoản chưa có quyền sử dụng nghiệp vụ Lotus. Nhờ quản trị viên kiểm tra quyền và vườn.</p>
  <p v-if="groups.length&&!filteredGroups.length" class="empty" role="status">Không tìm thấy chức năng phù hợp.</p>
 </section>
</template>

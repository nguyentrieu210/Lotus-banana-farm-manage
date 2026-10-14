<script setup>
import {Button as UiButton} from './ui/button'
import {computed} from 'vue'
import {Card as UiCard} from './ui/card'
import {mobileGroups} from '../mobile-menu'
const props=defineProps({session:{type:Object,required:true},farm:{type:String,default:''},online:{type:Boolean,default:true},queued:{type:Number,default:0}})
const emit=defineEmits(['select','outbox'])
const groups=computed(()=>mobileGroups(props.session))
const farmName=computed(()=>props.session.farms?.find(f=>f.name===props.farm)?.farm_name||props.farm||'Tất cả nông trường được phân quyền')
</script>

<template>
 <section class="mobile-home" aria-label="Công việc của bạn">
  <UiCard class="mobile-welcome">
   <p class="eyebrow">LOTUS AGRITECH · HÔM NAY</p>
   <h2>Bạn cần làm gì?</h2>
   <p>{{farmName}}</p>
  </UiCard>
  <section v-for="group in groups" :key="group.title" class="mobile-action-section">
   <h3>{{group.title}}</h3>
   <div class="mobile-action-grid">
    <UiButton variant="outline" v-for="action in group.actions" :key="action.id" class="mobile-action" type="button" @click="emit('select',action)">
     <span class="mobile-action-icon" aria-hidden="true">{{action.symbol}}</span>
     <span class="mobile-action-text"><strong>{{action.label}}</strong><small>{{action.detail}}</small></span>
     <span aria-hidden="true" class="mobile-action-chevron">›</span>
    </UiButton>
   </div>
  </section>
  <p v-if="!groups.length" class="notice">Tài khoản chưa có quyền sử dụng nghiệp vụ Lotus. Nhờ quản trị viên kiểm tra quyền và nông trường.</p>
  <p class="mobile-help">Các mục hiện theo quyền tài khoản. Nếu kiêm nhiều công việc, bạn sẽ thấy tất cả mục được cấp. Việc ghi dữ liệu vẫn phải được máy chủ cho phép.</p>
 </section>
</template>

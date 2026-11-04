<script setup>
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
// One ERP area: its documents, catalogues and reports (only what this user may open), plus the Lotus screen it complements.
defineProps({module:{type:Object,required:true}})
const emit=defineEmits(['open','new'])
const icon=item=>item.kind==='report'?'chart':item.tree?'list':'document'
</script>

<template>
 <section class="erp-home" :aria-label="module.label">
  <p v-if="module.lotus" class="erp-home__lotus">Thao tác hằng ngày của phân hệ này có màn riêng: <a :href="module.lotus">mở màn {{module.label}} của Lotus</a>. Các mục dưới đây là nghiệp vụ ERP đầy đủ.</p>
  <div class="erp-home__groups">
   <section v-for="group in module.groups" :key="group.label" class="erp-home__group" :aria-label="group.label">
    <h2>{{group.label}}</h2>
    <ul>
     <li v-for="item in group.items" :key="item.kind+item.name">
      <button type="button" class="erp-home__link" @click="emit('open',item)"><LotusIcon :name="icon(item)"/><span>{{item.label}}</span></button>
      <UiButton v-if="item.kind==='doctype'&&item.create&&!item.single" variant="ghost" size="sm" class="erp-home__new" :aria-label="'Tạo '+item.label" :title="'Tạo '+item.label" @click="emit('new',item)"><LotusIcon name="plus"/></UiButton>
     </li>
    </ul>
   </section>
  </div>
 </section>
</template>

<style>
.erp-home{display:grid;gap:14px}
.erp-home__lotus{margin:0;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-soft);color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.erp-home__lotus a{color:var(--lotus-primary);font-weight:600}
.erp-home__groups{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;align-items:start}
.erp-home__group{border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);padding:12px}
.erp-home__group h2{margin:0 0 8px;font-size:var(--lotus-text-sm);text-transform:uppercase;letter-spacing:.04em;color:var(--lotus-muted)}
.erp-home__group ul{list-style:none;margin:0;padding:0;display:grid;gap:2px}
.erp-home__group li{display:flex;align-items:center;gap:4px}
.erp-home__link{flex:1;display:flex;align-items:center;gap:8px;padding:7px 8px;border:0;border-radius:var(--lotus-radius-sm);background:transparent;color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.erp-home__link:hover,.erp-home__link:focus-visible{background:var(--lotus-soft)}
.erp-home__link svg{width:16px;height:16px;color:var(--lotus-muted);flex-shrink:0}
.erp-home__new svg{width:15px;height:15px}
</style>

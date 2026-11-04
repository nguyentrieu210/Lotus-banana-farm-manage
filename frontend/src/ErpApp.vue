<script setup>
import {computed,inject,onMounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {erp} from './erp-api'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import LotusField from './components/form/LotusField.vue'
import LotusIcon from './components/LotusIcon.vue'
import ErpHome from './components/erp/ErpHome.vue'
import ErpList from './components/erp/ErpList.vue'
import ErpForm from './components/erp/ErpForm.vue'
import ErpReport from './components/erp/ErpReport.vue'
// "Nghiệp vụ ERP": the rest of ERPNext/HRMS beside the Lotus screens, one area per sidebar entry (?erp_view=).
// URL: ?erp_view=<area>&dt=<DocType>[&name=<doc>|&new=1] or &report=<Report>; &company= keeps the scope.
const props=defineProps({embedded:Boolean,erpView:String,company:String})
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const confirm=useWorkspaceConfirm()
const catalog=ref(null),error=ref(''),company=ref(props.company||''),formRef=ref(null)
onMounted(async()=>{
 try{catalog.value=await erp('catalog');if(!company.value)company.value=catalog.value.companies?.[0]?.name||''}
 catch(e){error.value='Không tải được danh mục nghiệp vụ: '+e.message}
})
const query=computed(()=>route?.query||{})
const module=computed(()=>catalog.value?.modules.find(m=>m.id===(props.erpView||query.value.erp_view))||catalog.value?.modules[0]||null)
const items=computed(()=>(catalog.value?.modules||[]).flatMap(m=>m.groups.flatMap(g=>g.items)))
const current=computed(()=>{
 const q=query.value
 if(q.report)return {view:'report',item:items.value.find(i=>i.kind==='report'&&i.name===q.report)||{name:q.report,label:q.report}}
 if(q.dt){const item=items.value.find(i=>i.kind==='doctype'&&i.name===q.dt)||{name:q.dt,label:q.dt};return {view:q.name||q.new?'form':'list',item}}
 return {view:'home'}
})
const currency=computed(()=>catalog.value?.companies?.find(c=>c.name===company.value)?.default_currency||'VND')
const companyOptions=computed(()=>(catalog.value?.companies||[]).map(c=>({value:c.name,label:c.name})))
async function go(next,replace=false){
 if(current.value.view==='form'&&formRef.value?.hasChanges()&&!await confirm.ask('Có thay đổi chưa lưu. Rời chứng từ và bỏ thay đổi?','Rời chứng từ'))return
 const q={erp_view:module.value?.id,company:company.value||undefined,...next}
 if(router)await router[replace?'replace':'push']({path:'/erp',query:Object.fromEntries(Object.entries(q).filter(([,v])=>v!==undefined&&v!==''))})
}
function open(item){go(item.kind==='report'?{report:item.name}:{dt:item.name})}
function create(item){go({dt:item.name,new:1})}
watch(company,(value,old)=>{if(old&&value!==old&&router)router.replace({path:'/erp',query:{...query.value,company:value,name:undefined,new:undefined}})})
watch(()=>props.company,value=>{if(value&&value!==company.value)company.value=value})
defineExpose({hasChanges:()=>current.value.view==='form'&&!!formRef.value?.hasChanges(),discardChanges:()=>{},scopeParams:()=>({company:company.value||undefined})})
</script>

<template>
 <div class="erp-app lotus-ui" :class="{'embedded-workspace':embedded}">
  <p v-if="error" class="erp-form__error" role="alert">{{error}}</p>
  <p v-else-if="!catalog" class="erp-form__loading" role="status">Đang tải nghiệp vụ…</p>
  <template v-else-if="module">
   <div class="erp-app__bar">
    <nav class="erp-app__crumbs" aria-label="Vị trí">
     <button type="button" @click="go({})">{{module.label}}</button>
     <template v-if="current.item"><LotusIcon name="chevron" class="erp-app__sep" aria-hidden="true"/><button v-if="current.view==='form'" type="button" @click="go({dt:current.item.name})">{{current.item.label}}</button><span v-else>{{current.item.label}}</span></template>
     <template v-if="current.view==='form'"><LotusIcon name="chevron" class="erp-app__sep" aria-hidden="true"/><span>{{query.name||'Mới'}}</span></template>
    </nav>
    <LotusField v-if="companyOptions.length>1" class="erp-app__company" type="select" label="Công ty" :model-value="company" :options="companyOptions" :searchable="false" :empty-option="null" @update:model-value="v=>company=v"/>
   </div>
   <ErpHome v-if="current.view==='home'" :module="module" @open="open" @new="create"/>
   <ErpList v-else-if="current.view==='list'" :key="current.item.name" :doctype="current.item.name" :label="current.item.label" :company="company" :currency="currency" :can-create="!!current.item.create"
     @open="name=>go({dt:current.item.name,name})" @new="go({dt:current.item.name,new:1})"/>
   <ErpForm v-else-if="current.view==='form'" ref="formRef" :key="current.item.name+':'+(query.name||'new:'+(query.new||''))" :doctype="current.item.name" :name="query.name" :label="current.item.label" :company="company" :currency="currency" :confirm="confirm.ask"
     @back="go({dt:current.item.name})" @saved="({name,created})=>created&&go({dt:current.item.name,name},true)" @open-new="doctype=>go({dt:doctype,new:Date.now()})"/>
   <ErpReport v-else-if="current.view==='report'" :key="current.item.name" :name="current.item.name" :label="current.item.label" :company="company" :currency="currency" @back="go({})"/>
  </template>
  <p v-else class="erp-form__loading">Tài khoản chưa có quyền xem nghiệp vụ ERP nào.</p>
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" :alert-only="confirm.alertOnly.value" @answer="confirm.finish"/>
 </div>
</template>

<style>
.erp-app{display:grid;gap:12px;min-width:0}
.erp-app__bar{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:8px 16px}
.erp-app__crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.erp-app__crumbs button{border:0;background:transparent;padding:2px 4px;border-radius:var(--lotus-radius-sm);color:var(--lotus-primary);font:inherit;cursor:pointer}
.erp-app__crumbs button:hover{background:var(--lotus-soft)}
.erp-app__sep{width:12px;height:12px}
.erp-app__company{min-width:220px;max-width:320px}
</style>

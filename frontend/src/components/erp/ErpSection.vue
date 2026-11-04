<script setup>
import {computed,inject,ref} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import WorkspaceTabs from '../WorkspaceTabs.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import ErpList from './ErpList.vue'
import ErpForm from './ErpForm.vue'
import ErpReport from './ErpReport.vue'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import {systemLabel} from '../../system-translations.js'
// An ERPNext/HRMS section opened inside a Lotus module (Kho, Mua hàng, Tài chính, Nhân sự): one tab per document list or
// report. The module keeps its own view parameter (stock_view, hr_view, buying_view, tab); the section adds
// &erp_tab=<DocType|Report>, and &name=<doc> or &new=1 for a form; &erp_doctype= when "Tạo tiếp" made a document of
// another type (invoice → phiếu thu), so the follow-up opens right here too.
const props=defineProps({section:{type:Object,required:true},viewParam:{type:String,required:true},company:String,currency:{type:String,default:'VND'}})
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const confirm=useWorkspaceConfirm()
const formRef=ref(null),listRef=ref(null),formTitle=ref(''),formSize=ref(null)
// A 3-field catalogue gets a narrow dialog; documents with item grids or many fields get the wide one.
const modalWidth=computed(()=>!formSize.value?'1040px':formSize.value.tables||formSize.value.fields>24?'1280px':formSize.value.fields>8?'1040px':'720px')
const query=computed(()=>route?.query||{})
const tab=computed(()=>props.section.tabs.find(t=>t.name===query.value.erp_tab)||props.section.tabs[0])
const tabItems=computed(()=>props.section.tabs.map(t=>({id:t.name,label:t.label})))
const view=computed(()=>tab.value.kind==='report'?'report':query.value.name||query.value.new?'form':'list')
const formDoctype=computed(()=>query.value.erp_doctype||tab.value.name)
const formLabel=computed(()=>formDoctype.value===tab.value.name?tab.value.label:systemLabel(formDoctype.value))
async function go(next,replace=false){
 if(view.value==='form'&&formRef.value?.hasChanges()&&!await confirm.ask('Có thay đổi chưa lưu. Rời chứng từ và bỏ thay đổi?','Rời chứng từ'))return
 const base=Object.fromEntries(Object.entries(query.value).filter(([k])=>!['erp_tab','name','new','erp_doctype'].includes(k)))
 const q={...base,[props.viewParam]:'erp-'+props.section.id,erp_tab:tab.value.name,...next}
 if(router)await router[replace?'replace':'push']({path:route.path,query:Object.fromEntries(Object.entries(q).filter(([,v])=>v!==undefined&&v!==''))})
}
// Closing the dialog (Đóng, Esc, backdrop) asks first when the document has unsaved changes.
function closeForm(){go({})}
function saved({name,created}){listRef.value?.refresh();if(created)go({name,erp_doctype:query.value.erp_doctype},true)}
defineExpose({hasChanges:()=>view.value==='form'&&!!formRef.value?.hasChanges()})
</script>

<template>
 <section class="erp-section-host" :aria-label="section.label">
  <WorkspaceTabs v-if="tabItems.length>1" :items="tabItems" :model-value="tab.name" :label="section.label" @update:model-value="name=>go({erp_tab:name})"/>
  <ErpReport v-if="view==='report'" :key="tab.name" :name="tab.name" :label="tab.label" :company="company" :currency="currency" :show-back="false"/>
  <ErpList v-else ref="listRef" :key="tab.name" :doctype="tab.name" :label="tab.label" :company="company" :currency="currency" :can-create="!!tab.create"
    @open="name=>go({name})" @new="go({new:1})"/>
  <!-- The document opens in a dialog over its list, like every Lotus form. -->
  <WorkspaceModal v-if="view==='form'" :model-value="true" :title="formTitle||formLabel" :width="modalWidth" @update:model-value="open=>!open&&closeForm()">
   <ErpForm ref="formRef" modal :key="formDoctype+':'+(query.name||'new:'+query.new)" :doctype="formDoctype" :name="query.name" :label="formLabel" :company="company" :currency="currency" :confirm="confirm.ask"
     @title="value=>formTitle=value" @size="value=>formSize=value" @back="closeForm" @saved="saved"
     @open-new="doctype=>go(section.tabs.some(t=>t.name===doctype)?{erp_tab:doctype,new:Date.now()}:{erp_doctype:doctype,new:Date.now()})"/>
  </WorkspaceModal>
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" :alert-only="confirm.alertOnly.value" @answer="confirm.finish"/>
 </section>
</template>

<style>
.erp-section-host{display:grid;gap:12px;min-width:0}
</style>

<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import {erpFeature} from '../../erpnext-navigation'
import {Button} from '../ui/button'
const props=defineProps({module:String,company:String,rows:Array})
const emit=defineEmits(['open'])
const counts=ref({}),error=ref('')
const documents=computed(()=>props.rows.filter(r=>r.kind==='DocType').sort((a,b)=>Number(!!a.group)-Number(!!b.group)).slice(0,8).map(erpFeature))
const reports=computed(()=>props.rows.filter(r=>r.kind==='Report').slice(0,12).map(erpFeature))
let generation=0
async function load(){const id=++generation;counts.value={};error.value='';const values=await Promise.allSettled(documents.value.map(async d=>{const r=await call('lotus_farm.erp_workbench.listing',{doctype:d.name,company:props.company,length:1});return [d.name,r.single?null:r.total_count]}));if(id!==generation)return;counts.value=Object.fromEntries(values.filter(r=>r.status==='fulfilled').map(r=>r.value));if(values.some(r=>r.status==='rejected'))error.value='Một số số liệu chưa tải được.'}
watch(()=>[props.module,props.company,props.rows],load)
onMounted(load)
</script>
<template><section class="erp-overview"><p v-if="error" class="erp-error" role="status">{{error}}</p><div class="erp-overview-cards"><Button v-for="item in documents" :key="item.id" variant="outline" @click="emit('open',item)"><span>{{item.title}}</span><strong>{{counts[item.name]??'—'}}</strong></Button></div><h3>Báo cáo</h3><div class="erp-overview-reports"><Button v-for="item in reports" :key="item.id" variant="ghost" @click="emit('open',item)">{{item.title}}</Button></div></section></template>

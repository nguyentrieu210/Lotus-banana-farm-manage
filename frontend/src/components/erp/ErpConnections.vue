<script setup>
import {onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import {erpFeatureLabels} from '../../erpnext-navigation'
import {Button} from '../ui/button'
const props=defineProps({name:String,company:String})
const emit=defineEmits(['open-document','open-list','open-report'])
const rows=ref([]),error=ref('')
let generation=0
async function load(){const id=++generation;error.value='';try{const r=await call('lotus_farm.erp_workbench.supplier_connections',{name:props.name,company:props.company});if(id===generation)rows.value=r}catch(e){if(id===generation)error.value=e.message}}
watch(()=>[props.name,props.company],load)
onMounted(load)
</script>
<template><section class="erp-connections"><h3>Giao dịch liên quan</h3><p v-if="error" role="alert" class="erp-error">{{error}}</p><div class="erp-overview-reports"><div v-for="group in rows" :key="group.doctype"><Button variant="outline" @click="emit('open-list',{kind:'DocType',name:group.doctype,filters:group.filters})">{{erpFeatureLabels[group.doctype]||group.doctype}} · {{group.count}}</Button><div v-for="row in group.rows" :key="row.name"><Button variant="link" size="sm" @click="emit('open-document',{doctype:group.doctype,name:row.name})">{{row.name}}</Button></div></div></div><Button v-if="rows.some(r=>r.doctype==='Purchase Invoice')" variant="link" @click="emit('open-report',{name:'Accounts Payable',filters:{company,party_type:'Supplier',party:[name]}})">Công nợ và quá hạn theo ngày chốt</Button></section></template>

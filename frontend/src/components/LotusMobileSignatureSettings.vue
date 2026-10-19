<script setup>
import {ref,watch} from 'vue'
import {Icon} from 'vant'
import {call} from '../api'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileSelect from './LotusMobileSelect.vue'
import './lotus-mobile-signature.css'

const props=defineProps({user:{type:String,default:''}})
const expanded=ref(false),loading=ref(false),saving=ref(false),loaded=ref(false)
const profile=ref(null),provider=ref(''),error=ref(''),notice=ref('')
const endpoint='lotus_farm.digital_signature.'
watch(()=>props.user,()=>{expanded.value=false;loaded.value=false;profile.value=null;provider.value='';error.value='';notice.value=''})
async function load(){
 if(!props.user)return
 loading.value=true;error.value=''
 try{profile.value=await call(endpoint+'my_signature_profile');provider.value=profile.value.provider||'';loaded.value=true}
 catch(e){error.value=e.message||'Không tải được thông tin chữ ký số.'}
 finally{loading.value=false}
}
async function toggle(){expanded.value=!expanded.value;if(expanded.value&&!loaded.value)await load()}
async function save(){
 if(saving.value||loading.value||!profile.value?.configured)return
 saving.value=true;error.value='';notice.value=''
 try{
  profile.value=await call(endpoint+'set_signature_provider',{provider:provider.value},true)
  provider.value=profile.value.provider||''
  notice.value='Đã lưu nhà cung cấp dự kiến. Chữ ký số chưa được kích hoạt.'
 }catch(e){error.value=e.message||'Không lưu được thông tin chữ ký số.'}
 finally{saving.value=false}
}
</script>

<template>
 <section class="lotus-signature-settings">
  <LotusMobileButton class="lotus-signature-toggle" type="button" :aria-expanded="expanded" @click="toggle">
   <span class="lotus-signature-heading"><Icon name="shield-o" aria-hidden="true"/><span>Chữ ký số</span></span>
   <span class="lotus-signature-trailing">Thiết lập <Icon :name="expanded?'arrow-up':'arrow-down'" aria-hidden="true"/></span>
  </LotusMobileButton>
  <div v-if="expanded" class="lotus-signature-body">
   <p v-if="loading" role="status">Đang tải thông tin chữ ký số…</p>
   <p v-if="error" class="lotus-signature-error" role="alert">{{error}}</p>
   <template v-if="profile">
    <div class="lotus-signature-row"><span>Người ký</span><strong>{{profile.full_name}}</strong></div>
    <div class="lotus-signature-row"><span>Tài khoản</span><strong>{{profile.user}}</strong></div>
    <div class="lotus-signature-row"><span>Trạng thái</span><strong class="lotus-signature-pending">Chưa kết nối</strong></div>
    <LotusMobileSelect v-model="provider" label="Nhà cung cấp chữ ký số"
     :options="profile.providers" :disabled="saving||!profile.configured"/>
    <p class="lotus-signature-hint">Thông tin này lưu theo tài khoản và dùng chung cho Kho, Mua hàng, Nhân sự và Công việc ngoài vườn.</p>
    <LotusMobileButton type="button" variant="primary" block :loading="saving"
     :disabled="saving||!profile.configured||provider===profile.provider" @click="save">Lưu lựa chọn</LotusMobileButton>
    <p v-if="notice" class="lotus-signature-notice" role="status">{{notice}}</p>
    <p class="lotus-signature-warning">Chưa có chứng thư số được xác minh. Bấm Duyệt hiện chưa tự ký số vào PDF. Không tải khóa bí mật, mật khẩu hay mã PIN lên Lotus.</p>
   </template>
  </div>
 </section>
</template>

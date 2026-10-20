<script setup>
import {computed} from 'vue'

const props=defineProps({
 steps:{type:Array,default:()=>[]},
 current:{type:Number,default:-1},
 title:{type:String,default:'Các bước ký'},
 empty:{type:String,default:'Chưa gửi ký.'}
})
const rows=computed(()=>(props.steps||[]).map((step,index)=>{
 const signed=step.state==='Đã ký'||step.state==='SIGNED'||!!step.signed_at
 const returned=step.state==='Trả lại'||step.state==='RETURNED'
 const active=!signed&&!returned&&props.current===index
 const name=step.name||step.assignee||''
 const moment=step.signed_at?String(step.signed_at):''
 const when=moment.length>=10&&moment[4]==='-'?moment.slice(8,10)+'/'+moment.slice(5,7)+'/'+moment.slice(0,4)+(moment.length>=16?' '+moment.slice(11,16):''):moment
 return {...step,index,signed,returned,active,
  label:returned?(name?name+' · ':'')+'Đã trả lại'+(step.note?': '+step.note:''):
   signed?(name?name+' · ':'')+'Đã ký'+(when?' lúc '+when:''):
   (name||'Chưa chọn người ký')+(active?' · đang chờ ký':' · chưa đến lượt')}
}))
</script>

<template>
 <section class="lotus-signature-timeline" aria-label="Quy trình chữ ký">
  <h3 v-if="title">{{title}}</h3>
  <ol v-if="rows.length" class="lotus-signature-timeline__list">
   <li v-for="row in rows" :key="row.key||row.action||row.index"
    :class="{'is-signed':row.signed,'is-active':row.active,'is-returned':row.returned}">
    <span class="lotus-signature-timeline__mark" aria-hidden="true">{{row.signed?'✓':row.index+1}}</span>
    <div class="lotus-signature-timeline__body">
     <strong>{{row.title}}</strong>
     <small>{{row.label}}</small>
     <img v-if="row.signed&&row.image" :src="row.image" :alt="'Chữ ký '+(row.name||row.title)" loading="lazy"/>
    </div>
   </li>
  </ol>
  <p v-else class="lotus-signature-timeline__empty">{{empty}}</p>
  <p class="lotus-signature-timeline__note">Chữ ký bằng hình ảnh, không phải chữ ký số có chứng thư. Quyền ký được kiểm tra theo tài khoản.</p>
 </section>
</template>

<style scoped>
.lotus-signature-timeline{min-width:0;color:var(--lotus-text)}
.lotus-signature-timeline h3{font-size:var(--lotus-text-base);margin:0 0 10px;font-weight:700}
.lotus-signature-timeline__list{display:flex;flex-direction:column;gap:8px;margin:0;padding:0;list-style:none}
.lotus-signature-timeline__list li{display:flex;align-items:flex-start;gap:10px;padding:11px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.lotus-signature-timeline__list li.is-signed{border-color:var(--lotus-success-200);background:var(--lotus-success-soft)}
.lotus-signature-timeline__list li.is-active{border-color:var(--lotus-primary)}
.lotus-signature-timeline__list li.is-returned{border-color:var(--lotus-danger);background:var(--lotus-danger-soft)}
.lotus-signature-timeline__mark{display:grid;place-items:center;flex:none;width:25px;height:25px;border-radius:50%;border:1px solid var(--lotus-border-strong);font-size:12px;font-weight:700}
.is-signed .lotus-signature-timeline__mark{background:var(--lotus-success);color:#fff;border-color:transparent}
.is-active .lotus-signature-timeline__mark{background:var(--lotus-primary);color:#fff;border-color:transparent}
.lotus-signature-timeline__body{display:flex;flex-direction:column;align-items:flex-start;gap:4px;min-width:0;flex:1}
.lotus-signature-timeline__body strong{font-size:14px}
.lotus-signature-timeline__body small{font-size:12px;color:var(--lotus-muted);overflow-wrap:anywhere}
.lotus-signature-timeline__body img{max-width:150px;max-height:64px;object-fit:contain;background:#fff;border-radius:5px}
.lotus-signature-timeline__empty,.lotus-signature-timeline__note{margin:8px 0 0;color:var(--lotus-muted);font-size:12px}
</style>
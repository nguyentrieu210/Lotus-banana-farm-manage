<script setup>
import {computed,ref,watch} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {normalizeUnit} from '../../units'
// Cây danh mục (nhóm vật tư, kho): nodes come parents first; a node is {id,parent,label,isGroup,count,meta,muted}.
// Click a name to edit it, "+" on a group adds a child. Expanded groups are remembered per storage key.
const props=defineProps({nodes:{type:Array,default:()=>[]},search:{type:String,default:''},storageKey:String,countLabel:{type:String,default:'mục'},addLabel:{type:String,default:'Thêm mục con'},canAdd:Boolean,groupIcon:{type:String,default:'boxes'},leafIcon:{type:String,default:'package'}})
const emit=defineEmits(['open','add'])
const children=computed(()=>{const map=new Map();for(const n of props.nodes){const p=n.parent||'';if(!map.has(p))map.set(p,[]);map.get(p).push(n)}return map})
const ids=computed(()=>new Set(props.nodes.map(n=>n.id)))
const roots=computed(()=>props.nodes.filter(n=>!n.parent||!ids.value.has(n.parent)))
const saved=()=>{try{return JSON.parse(localStorage.getItem('lotus-tree-'+props.storageKey)||'null')}catch{return null}}
const expanded=ref(new Set(saved()||[]))
watch(()=>props.nodes,nodes=>{if(!saved()&&nodes.length)expanded.value=new Set(nodes.filter(n=>n.isGroup).map(n=>n.id))},{immediate:true})
watch(expanded,value=>{if(props.storageKey)localStorage.setItem('lotus-tree-'+props.storageKey,JSON.stringify([...value]))},{deep:true})
// Total under a group = its own count plus every descendant's.
const totals=computed(()=>{const memo=new Map();const total=n=>{if(memo.has(n.id))return memo.get(n.id);const sum=(n.count||0)+(children.value.get(n.id)||[]).reduce((s,c)=>s+total(c),0);memo.set(n.id,sum);return sum};props.nodes.forEach(total);return memo})
// Search keeps matching nodes and the path to them, all opened.
const matches=computed(()=>{const q=normalizeUnit(props.search);if(!q)return null;const keep=new Set();const byId=new Map(props.nodes.map(n=>[n.id,n]))
 for(const n of props.nodes)if(normalizeUnit(n.label+' '+(n.meta||'')+' '+n.id).includes(q)){let cur=n;while(cur&&!keep.has(cur.id)){keep.add(cur.id);cur=byId.get(cur.parent)}}
 return keep})
const rows=computed(()=>{const out=[];const walk=(list,depth)=>{for(const n of list){if(matches.value&&!matches.value.has(n.id))continue;const kids=children.value.get(n.id)||[];const open=matches.value?true:expanded.value.has(n.id)
  out.push({node:n,depth,hasKids:kids.length>0,open});if(open)walk(kids,depth+1)}};walk(roots.value,0);return out})
function toggle(id){const next=new Set(expanded.value);next.has(id)?next.delete(id):next.add(id);expanded.value=next}
function setAll(open){expanded.value=open?new Set(props.nodes.filter(n=>n.isGroup).map(n=>n.id)):new Set()}
defineExpose({expandAll:()=>setAll(true),collapseAll:()=>setAll(false)})
</script>

<template>
 <div class="master-tree">
  <ul v-if="rows.length" class="master-tree__list" role="tree">
   <li v-for="row in rows" :key="row.node.id" class="master-tree__row" :class="{'master-tree__row--group':row.node.isGroup,'master-tree__row--muted':row.node.muted}" role="treeitem" :aria-level="row.depth+1" :aria-expanded="row.hasKids?row.open:undefined" :style="{'--depth':row.depth}">
    <button v-if="row.hasKids" type="button" class="master-tree__toggle" :aria-label="(row.open?'Thu gọn ':'Mở ')+row.node.label" @click="toggle(row.node.id)"><LotusIcon name="chevron" :class="{'master-tree__chevron--open':row.open}"/></button>
    <span v-else class="master-tree__toggle master-tree__toggle--empty" aria-hidden="true"/>
    <button type="button" class="master-tree__name" @click="emit('open',row.node)">
     <LotusIcon :name="row.node.isGroup?groupIcon:leafIcon" class="master-tree__icon"/>
     <span class="master-tree__label">{{row.node.label}}</span>
     <span v-if="row.node.muted" class="master-tree__tag">Ngừng dùng</span>
    </button>
    <span v-if="row.node.meta" class="master-tree__meta">{{row.node.meta}}</span>
    <span class="master-tree__count" :title="row.node.isGroup&&row.hasKids?'Gồm cả các nhánh con':''">{{totals.get(row.node.id)||0}} {{countLabel}}</span>
    <button v-if="canAdd&&row.node.isGroup" type="button" class="master-tree__add" :aria-label="addLabel+' vào '+row.node.label" :title="addLabel" @click="emit('add',row.node)"><LotusIcon name="plus"/></button>
    <span v-else class="master-tree__add master-tree__add--empty" aria-hidden="true"/>
   </li>
  </ul>
  <p v-else class="master-tree__empty">{{search?'Không có mục khớp từ khóa.':'Chưa có dữ liệu.'}}</p>
 </div>
</template>

<style>
.master-tree{border:1px solid var(--lotus-border);border-radius:10px;background:var(--lotus-surface);overflow:auto}
.master-tree__list{list-style:none;margin:0;padding:4px 0}
.master-tree__row{display:grid;grid-template-columns:28px minmax(0,1fr) auto auto 32px;align-items:center;gap:8px;min-height:40px;padding:0 12px 0 calc(12px + var(--depth) * 24px);border-bottom:1px solid var(--lotus-border)}
.master-tree__row:last-child{border-bottom:0}
.master-tree__row:hover{background:var(--lotus-soft)}
.master-tree__row--group .master-tree__label{font-weight:600}
.master-tree__row--muted .master-tree__label{color:var(--lotus-muted)}
.master-tree__toggle{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border:0;border-radius:6px;background:transparent;color:var(--lotus-muted);cursor:pointer}
.master-tree__toggle:hover{background:var(--lotus-soft)}
.master-tree__toggle--empty{cursor:default}
.master-tree__toggle svg{transform:rotate(0);transition:transform .15s}
.master-tree__toggle .master-tree__chevron--open{transform:rotate(90deg)}
.master-tree__name{display:inline-flex;align-items:center;gap:8px;min-width:0;border:0;background:transparent;padding:6px 4px;text-align:left;cursor:pointer;color:inherit;font:inherit;border-radius:6px}
.master-tree__name:hover .master-tree__label{color:var(--lotus-primary);text-decoration:underline}
.master-tree__name:focus-visible,.master-tree__toggle:focus-visible,.master-tree__add:focus-visible{outline:2px solid var(--lotus-primary);outline-offset:1px}
.master-tree__icon{flex:none;color:var(--lotus-muted)}
.master-tree__label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.master-tree__tag{flex:none;font-size:12px;padding:1px 8px;border-radius:999px;background:var(--lotus-soft);color:var(--lotus-muted)}
.master-tree__meta{font-size:13px;color:var(--lotus-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:360px}
.master-tree__count{font-size:13px;color:var(--lotus-muted);white-space:nowrap;font-variant-numeric:tabular-nums;min-width:72px;text-align:right}
.master-tree__add{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid var(--lotus-border);border-radius:8px;background:transparent;color:inherit;cursor:pointer}
.master-tree__add:hover{border-color:var(--lotus-primary);color:var(--lotus-primary)}
.master-tree__add--empty{border:0;cursor:default}
.master-tree__empty{margin:0;padding:24px;text-align:center;color:var(--lotus-muted)}
@media (max-width:720px){.master-tree__row{grid-template-columns:28px minmax(0,1fr) auto 32px;padding-left:calc(8px + var(--depth) * 16px)}.master-tree__meta{display:none}}
</style>

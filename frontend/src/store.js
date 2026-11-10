import {setErpSections} from './erp-sections.js'
import {defineStore} from 'pinia'
import {consoleAPI,setCSRF} from './api'
import {activeUser} from './offline-cache'
import {safeLotusDate,isISODate} from './date-safe'
let loading=null
export const useSession=defineStore('session',{state:()=>({user:'',farms:[],modules:{},capabilities:{},today:'',ready:false,creatable:{},offline:false}),actions:{async load(force=false){if(this.ready&&!force)return this;if(loading)return loading;loading=(async()=>{Object.assign(this,{offline:false},await consoleAPI('bootstrap'));setErpSections(this.erp_sections);this.today=safeLotusDate(this.today);setCSRF(this.csrf_token);this.ready=true;return this})().finally(()=>loading=null);return loading}}})
export const useScope=defineStore('scope',{state:()=>({company:'',farm:'',zone:'',block:'',date:'',from_date:'',to_date:'',status:'',search:'',sort:'modified desc',group:''}),actions:{
 fromQuery(q,today,farms=[]){let saved={};try{saved=JSON.parse(localStorage.getItem('lotus-safe-scope|'+activeUser())||'{}')}catch{}const source={...saved,...q},defaults={date:safeLotusDate(today),sort:'modified desc'};for(const key of Object.keys(this.$state))this[key]=String(source[key]??defaults[key]??'');this.date=safeLotusDate(this.date,today);for(const field of ['from_date','to_date'])if(this[field]&&!isISODate(this[field]))this[field]='';if(this.farm&&!farms.some(f=>f.name===this.farm)){this.farm='';this.block=''}if(this.company&&!farms.some(f=>f.company===this.company)){this.company='';this.farm='';this.block=''}const companies=[...new Set(farms.map(f=>f.company).filter(Boolean))];if(companies.length===1)this.company=companies[0];this.persist()},
 clearBelow(level){const levels=['company','farm','zone','block'];for(const key of levels.slice(levels.indexOf(level)+1))this[key]='';this.persist()},
 persist(){try{if(activeUser())localStorage.setItem('lotus-safe-scope|'+activeUser(),JSON.stringify(this.$state))}catch{}},
 query(extra={}){this.persist();return Object.fromEntries(Object.entries({...this.$state,...extra}).filter(([,v])=>v!==''&&v!=null))}
}})
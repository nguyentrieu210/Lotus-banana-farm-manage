import {defineStore} from 'pinia'
import {consoleAPI,setCSRF} from './api'
export const useSession=defineStore('session',{state:()=>({user:'',farms:[],modules:{},capabilities:{},today:'',ready:false,creatable:{}}),actions:{async load(){Object.assign(this,await consoleAPI('bootstrap'));setCSRF(this.csrf_token);this.ready=true}}})
export const useScope=defineStore('scope',{state:()=>({company:'',farm:'',block:'',plot:'',cycle:'',date:'',from_date:'',to_date:'',status:'',search:'',sort:'modified desc',group:'',view:'list'}),actions:{
  fromQuery(q,today,farms=[]){let saved={};try{saved=JSON.parse(localStorage.getItem('lotus-safe-scope')||'{}')}catch{}const source={...saved,...q},defaults={date:today,view:'list',sort:'modified desc'};for(const key of Object.keys(this.$state))this[key]=String(source[key]??defaults[key]??'');if(this.farm&&!farms.some(f=>f.name===this.farm)){this.farm='';this.block='';this.plot='';this.cycle=''}this.persist()},
  persist(){try{localStorage.setItem('lotus-safe-scope',JSON.stringify(this.$state))}catch{}},
  query(extra={}){this.persist();return Object.fromEntries(Object.entries({...this.$state,...extra}).filter(([,v])=>v!==''&&v!=null))}
}})

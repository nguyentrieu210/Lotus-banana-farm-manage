import {defineStore} from 'pinia'
import {consoleAPI,setCSRF} from './api'
export const useSession=defineStore('session',{state:()=>({user:'',farms:[],modules:{},capabilities:{},today:'',ready:false}),actions:{async load(){Object.assign(this,await consoleAPI('bootstrap'));setCSRF(this.csrf_token);this.ready=true}}})
export const useScope=defineStore('scope',{state:()=>({company:'',farm:'',block:'',plot:'',date:'',from_date:'',to_date:'',view:'list'}),actions:{fromQuery(q,today){for(const key of Object.keys(this.$state))this[key]=String(q[key]||((key==='date')?today:(key==='view'?'list':'')))},query(extra={}){return Object.fromEntries(Object.entries({...this.$state,...extra}).filter(([,v])=>v!==''&&v!=null))}}})

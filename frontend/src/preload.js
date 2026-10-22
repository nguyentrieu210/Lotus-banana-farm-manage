import {call,consoleAPI} from './api'
import {safeLotusDate} from './date-safe'
const fields=['Daily Work Result','Bunch Cancellation','Disease Observation','Fruit Measurement','Planting Event','Harvest Actual','Bunch Operation']
const preloaded=new Set()
export async function preloadField(session,farm,date){
 if(!navigator.onLine||!farm||!session.commands.capture)return
 const postingDate=safeLotusDate(date,session.today)
 const key=session.user+'|'+farm+'|'+postingDate
 if(preloaded.has(key))return
 await call('lotus_farm.field.bootstrap',{farm,posting_date:postingDate})
 for(const type of fields.filter(t=>session.creatable[t])){
  const schema=await consoleAPI('schema',{doctype:type})
  const links=[...schema.fields,...Object.values(schema.tables).flat()].filter(f=>f.fieldtype==='Link')
  for(const doctype of new Set(links.map(f=>f.options)))try{await consoleAPI('link_options',{doctype,search:'',farm,company:session.farms.find(f=>f.name===farm)?.company})}catch{}
 }
 preloaded.add(key)
}
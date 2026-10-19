import {readdirSync,readFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {label,stateLabel,docLabel} from '../frontend/src/labels.js'
const root=fileURLToPath(new URL('../lotus_farm/lotus_farm/doctype/',import.meta.url))
const missingFields=new Map(), missingOptions=new Set(), missingDocuments=[]
for(const folder of readdirSync(root)){
 let schema
 try{schema=JSON.parse(readFileSync(root+folder+'/'+folder+'.json','utf8'))}catch{continue}
 if(docLabel(schema.name)===schema.name)missingDocuments.push(schema.name)
 for(const field of schema.fields||[]){
  if(['Section Break','Column Break','Tab Break','HTML','Button','Password'].includes(field.fieldtype)||field.hidden)continue
  if(label(field.fieldname,field.label)===field.label && /[A-Za-z]/.test(field.label||'') && !/[^\x00-\x7f]/.test(field.label||''))missingFields.set(field.fieldname,field.label)
  if(field.fieldtype==='Select')for(const value of (field.options||'').split('\n').filter(Boolean))if(stateLabel(value)===value && /[A-Za-z]/.test(value))missingOptions.add(value)
 }
}
console.log(JSON.stringify({missingFields:Object.fromEntries(missingFields),missingOptions:[...missingOptions].sort(),missingDocuments},null,2))

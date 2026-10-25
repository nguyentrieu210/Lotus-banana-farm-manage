// Extract declarative filter metadata from the installed, pinned ERPNext/HRMS
// sources. Parse syntax only: no report JavaScript is executed in Lotus.
import fs from 'node:fs'
import {parse} from '../frontend/node_modules/@babel/parser/lib/index.js'
const sourceFile=process.argv[2],outputFile=process.argv[3]
if(!sourceFile||!outputFile)throw Error('Usage: node tools/export_erpnext_report_fields.mjs sources.json output.json')
const sources=JSON.parse(fs.readFileSync(sourceFile,'utf8')).sort((a,b)=>Number(b.path.endsWith('/financial_statements.js'))-Number(a.path.endsWith('/financial_statements.js')))
const objects=new Map(),reports=new Map();let code='',locals=new Map(),functions=new Map()
function key(n){if(!n)return '';if(n.type==='Identifier')return n.name;if(['StringLiteral','NumericLiteral'].includes(n.type))return String(n.value);if(n.type==='MemberExpression'||n.type==='OptionalMemberExpression')return key(n.object)+'.'+key(n.property);return ''}
function value(n){
 if(!n)return undefined
 if(['StringLiteral','NumericLiteral','BooleanLiteral'].includes(n.type))return n.value
 if(n.type==='NullLiteral')return null
 if(n.type==='TemplateLiteral'&&!n.expressions.length)return n.quasis.map(q=>q.value.cooked).join('')
 if(n.type==='UnaryExpression'&&n.operator==='-'&&n.argument.type==='NumericLiteral')return -n.argument.value
 if(n.type==='ArrayExpression')return n.elements.flatMap(e=>e?.type==='SpreadElement'?(value(e.argument)||[]):[value(e)]).filter(v=>v!==undefined)
 if(n.type==='ObjectExpression'){const result={};for(const p of n.properties){if(p.type==='SpreadElement')Object.assign(result,value(p.argument));else if(p.type==='ObjectProperty'){const v=value(p.value);if(v!==undefined)result[key(p.key)]=v}}return result}
 if(['FunctionExpression','ArrowFunctionExpression','ObjectMethod'].includes(n.type))return undefined
 if(n.type==='CallExpression'&&['__','frappe._'].includes(key(n.callee)))return value(n.arguments[0])
 if(n.type==='CallExpression'&&['$.extend','Object.assign'].includes(key(n.callee)))return Object.assign({},...n.arguments.map(value).filter(v=>v&&typeof v==='object'))
 if(n.type==='CallExpression'&&functions.has(key(n.callee))){const fn=functions.get(key(n.callee));let returned;walk(fn.body,x=>{if(x.type==='ReturnStatement'&&x.argument&&x.argument.type!=='ObjectExpression')returned=x.argument});if(returned){if(returned.type==='Identifier'){let definition;walk(fn.body,x=>{if(x.type==='VariableDeclarator'&&key(x.id)===returned.name)definition=x.init});if(definition)return value(definition)}else return value(returned)}}
 const local=locals.get(key(n));if(local)return value(local)
 const known=objects.get(key(n));if(known)return structuredClone(known)
 return {$expr:code.slice(n.start,n.end)}
}
function walk(n,fn){if(!n||typeof n!=='object')return;fn(n);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(x=>walk(x,fn));else if(v&&typeof v==='object')walk(v,fn)}}
for(const source of sources){code=source.source;let ast;try{ast=parse(code,{sourceType:'unambiguous',errorRecovery:true})}catch{continue}
 locals=new Map();functions=new Map();walk(ast,n=>{if(n.type==='VariableDeclarator'&&n.init&&['StringLiteral','ArrayExpression','ObjectExpression'].includes(n.init.type))locals.set(key(n.id),n.init);if(n.type==='FunctionDeclaration')functions.set(key(n.id),n)})
 walk(ast,n=>{if(n.type==='AssignmentExpression'&&n.operator==='='&&n.right.type==='ObjectExpression')objects.set(key(n.left),value(n.right))})
 walk(ast,n=>{
  if(n.type==='AssignmentExpression'&&n.operator==='='&&n.left.type==='MemberExpression'&&key(n.left.object)==='frappe.query_reports'){
   const name=n.left.computed?(value(n.left.property)||key(n.left.property)):key(n.left.property),definition=value(n.right)
   if(definition&&typeof definition==='object')reports.set(name,{filters:Array.isArray(definition.filters)?definition.filters:[],tree:!!definition.tree,source:source.path.split('/apps/')[1]})
  }
  if(n.type==='CallExpression'&&['push','unshift'].includes(key(n.callee.property))){const path=key(n.callee.object),m=path.match(/^frappe\.query_reports\.(.+)\.filters$/);const report=m&&(locals.has(m[1])?value(locals.get(m[1])):m[1]);if(report&&reports.has(report))reports.get(report).filters.push(...n.arguments.map(value).filter(x=>x?.fieldname))}
 })
}
const allowed=new Set(['fieldname','label','fieldtype','options','default','reqd','hidden','depends_on','mandatory_depends_on','read_only','description','width','wildcard_filter'])
const rows=Object.fromEntries([...reports].map(([name,r])=>[name,{...r,filters:r.filters.filter(f=>f?.fieldname).map(f=>Object.fromEntries(Object.entries(f).filter(([k])=>allowed.has(k))))}]))
fs.writeFileSync(outputFile,JSON.stringify({source:'Installed ERPNext/HRMS sources; original license applies. Generated with a syntax parser, never eval.',reports:rows},null,2)+'\n')
console.log(JSON.stringify({reports:Object.keys(rows).length,with_filters:Object.values(rows).filter(r=>r.filters.length).length,consolidated:rows['Consolidated Financial Statement']?.filters.length}))

// A deliberately small expression interpreter for native metadata conditions.
// No eval, Function constructor, script tags or global object access.
const blocked=new Set(['constructor','prototype','__proto__','call','apply','bind'])
export function condition(expression,doc={},parent=doc,roles=[]){
 if(!expression)return true
 if(!expression.startsWith('eval:'))return truth(doc[expression])
 const source=expression.slice(5),tokens=[];let p=0,i=0
 const lexer=/\s*(===|!==|==|!=|>=|<=|&&|\|\||[!><()[\].,?:+\-*/%]|(?:\d+(?:\.\d+)?)|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][\w$]*)/y
 try{
  while(p<source.length){lexer.lastIndex=p;const m=lexer.exec(source);if(!m){if(!source.slice(p).trim())break;return false}tokens.push(m[1]);p=lexer.lastIndex;if(tokens.length>250)return false}
  const take=()=>tokens[i++],peek=()=>tokens[i],accept=t=>peek()===t&&(i++,true),need=t=>{if(!accept(t))throw Error('Unsupported condition')}
  const functions={in_list:(a,b)=>Array.isArray(a)&&a.includes(b),inList:(a,b)=>Array.isArray(a)&&a.includes(b),cint:v=>parseInt(v)||0,flt:v=>Number(v)||0,len:v=>v?.length||0,is_null:v=>v==null||v==='',has_common:(a,b)=>Array.isArray(a)&&a.some(v=>b?.includes(v))}
  const context={doc,parent,true:true,false:false,null:null,undefined:undefined,frappe:{session:{user:doc.__user},user_roles:roles,user:{has_role:r=>roles.includes(r)}}}
  const args=()=>{const a=[];if(!accept(')')){do{a.push(parse(0))}while(accept(','));need(')')}return a}
  function atom(){
   let t=take(),v
   if(t==='!')return !truth(atom())
   if(t==='-')return -Number(atom())
   if(t==='('){v=parse(0);need(')')}
   else if(t==='['){v=[];if(!accept(']')){do{v.push(parse(0))}while(accept(','));need(']')}}
   else if(t?.startsWith('"'))v=JSON.parse(t)
   else if(t?.startsWith("'"))v=t.slice(1,-1).replace(/\\'/g,"'").replace(/\\\\/g,'\\')
   else if(/^\d/.test(t||''))v=Number(t)
   else if(Object.hasOwn(functions,t)&&accept('('))v=functions[t](...args())
   else if(Object.hasOwn(context,t))v=context[t]
   else throw Error('Unknown condition symbol')
   while(peek()==='.'||peek()==='['){let k;if(accept('.'))k=take();else{need('[');k=parse(0);need(']')}if(blocked.has(k))throw Error('Invalid property');if(accept('(')){const a=args();if(['includes','startsWith','endsWith','indexOf'].includes(k)&&(typeof v==='string'||Array.isArray(v)))v=v[k](...a);else if(k==='has_role'&&typeof v?.[k]==='function')v=v[k](...a);else throw Error('Unsupported call')}else v=v?.[k]}
   return v
  }
  const precedence={'||':1,'&&':2,'==':3,'!=':3,'===':3,'!==':3,'>':4,'<':4,'>=':4,'<=':4,'+':5,'-':5,'*':6,'/':6,'%':6}
  function parse(min){let left=atom();while((precedence[peek()]||0)>min){const op=take(),right=parse(precedence[op]);left={'||':()=>truth(left)||truth(right),'&&':()=>truth(left)&&truth(right),'==':()=>left==right,'!=':()=>left!=right,'===':()=>left===right,'!==':()=>left!==right,'>':()=>left>right,'<':()=>left<right,'>=':()=>left>=right,'<=':()=>left<=right,'+':()=>Number(left)+Number(right),'-':()=>left-right,'*':()=>left*right,'/':()=>left/right,'%':()=>left%right}[op]()}if(min===0&&accept('?')){const a=parse(0);need(':');const b=parse(0);left=truth(left)?a:b}return left}
  const result=parse(0);return i===tokens.length&&truth(result)
 }catch{return false}
}
function truth(value){return Array.isArray(value)?value.length>0:!!value}
export const visibleField=(f,doc,parent,roles)=>!f.hidden&&(!f.depends_on||condition(f.depends_on,doc,parent,roles))
export const requiredField=(f,doc,parent,roles)=>!!f.reqd||!!f.mandatory_depends_on&&condition(f.mandatory_depends_on,doc,parent,roles)
export const readonlyField=(f,doc,parent,roles)=>!!f.read_only||!!f.read_only_depends_on&&condition(f.read_only_depends_on,doc,parent,roles)||Number(parent?.docstatus||doc?.docstatus)===2||Number(parent?.docstatus||doc?.docstatus)===1&&!f.allow_on_submit
export function formTabs(fields){
 const tabs=[];let tab,section,column
 function newTab(f={}){tab={id:f.fieldname||'general',label:f.label||'Thông tin',sections:[]};tabs.push(tab);newSection()}
 function newSection(f={}){section={id:f.fieldname||'section-'+tab.sections.length,label:f.label||'',field:f,columns:[[]]};tab.sections.push(section);column=section.columns[0]}
 newTab()
 for(const f of fields||[]){if(f.fieldtype==='Tab Break')newTab(f);else if(f.fieldtype==='Section Break')newSection(f);else if(f.fieldtype==='Column Break'){column=[];section.columns.push(column)}else column.push(f)}
 return tabs.filter(t=>t.sections.some(s=>s.columns.some(c=>c.length)))
}
export function cleanDocument(doc){return JSON.parse(JSON.stringify(doc,(key,value)=>key.startsWith('_')&&!['__islocal','__newname'].includes(key)?undefined:value))}
export const erpStatus=doc=>['Nháp','Đã duyệt','Đã hủy'][Number(doc.docstatus||0)]

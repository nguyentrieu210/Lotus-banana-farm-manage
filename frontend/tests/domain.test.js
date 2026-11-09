import {test} from 'node:test'
import assert from 'node:assert/strict'
import {cleanFields,pages} from '../src/domain.js'
test('editor never sends computed fields or child control flags',()=>{const schema={fields:[{fieldname:'farm'},{fieldname:'total',read_only:1},{fieldname:'rows',fieldtype:'Table',options:'Line'}],tables:{Line:[{fieldname:'item'},{fieldname:'computed',read_only:1}]}};assert.deepEqual(cleanFields(schema,{farm:'A',total:10,rows:[{item:'x',computed:9,flags:{ignore_permissions:true}}]}),{farm:'A',rows:[{item:'x'}]})})

test('BRD navigation exposes trace map and settings',()=>{const names=new Set(pages.map(([p])=>p));for(const p of ['forecast','trace','map','admin/settings'])assert.equal(names.has(p),true)})

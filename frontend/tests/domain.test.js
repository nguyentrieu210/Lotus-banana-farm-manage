import {test} from 'node:test'
import assert from 'node:assert/strict'
import {cleanFields,laborMatrix} from '../src/domain.js'
test('editor never sends computed fields or child control flags',()=>{const schema={fields:[{fieldname:'farm'},{fieldname:'total',read_only:1},{fieldname:'rows',fieldtype:'Table',options:'Line'}],tables:{Line:[{fieldname:'item'},{fieldname:'computed',read_only:1}]}};assert.deepEqual(cleanFields(schema,{farm:'A',total:10,rows:[{item:'x',computed:9,flags:{ignore_permissions:true}}]}),{farm:'A',rows:[{item:'x'}]})})
test('equal resources retain separate groups and unknown attendance remains unknown',()=>{const rows=laborMatrix([{work_type:'a',required_workdays:2,allocated_workdays:1},{work_type:'b',required_workdays:4,allocated_workdays:4}],[]);assert.equal(rows[0].gap,null);assert.equal(rows[0].allocation_gap,-1);assert.equal(rows[1].required,4)})

import test from 'node:test'
import assert from 'node:assert/strict'
import {condition,formTabs,cleanDocument,readonlyField} from '../src/erp-form.js'
test('native conditions support document links, boolean operators and list membership without executing scripts',()=>{
 assert.equal(condition("eval:in_list(['Material Receipt','Material Issue'], doc.purpose) && !doc.is_return",{purpose:'Material Receipt',is_return:0}),true)
 assert.equal(condition("eval:doc.filter_based_on == 'Fiscal Year'",{filter_based_on:'Date Range'}),false)
 assert.equal(condition("eval:doc.name.startsWith('new-') || doc.qty >= 2",{name:'SE',qty:2}),true)
 assert.equal(condition("eval:globalThis.fetch('/bad')"),false)
 assert.equal(condition("eval:doc.constructor.constructor('return process')()",{}),false)
 assert.equal(condition('eval:doc.x = 1',{}),false)
 assert.equal(readonlyField({allow_on_submit:0},{docstatus:1}),true)
})
test('native tabs, sections and columns retain their metadata order',()=>{
 const tabs=formTabs([{fieldname:'supplier',fieldtype:'Link'},{fieldname:'col',fieldtype:'Column Break'},{fieldname:'date',fieldtype:'Date'},{fieldname:'taxes',fieldtype:'Tab Break',label:'Taxes'},{fieldname:'rows',fieldtype:'Table'}]);assert.equal(tabs.length,2);assert.equal(tabs[0].sections[0].columns[1][0].fieldname,'date');assert.equal(tabs[1].label,'Taxes');assert.deepEqual(cleanDocument({_row:'x',doctype:'Item',__islocal:1}),{doctype:'Item',__islocal:1})
})

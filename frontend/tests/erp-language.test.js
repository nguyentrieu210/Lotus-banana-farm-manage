import test from 'node:test'
import assert from 'node:assert/strict'
import {erpText,erpOption,erpValue,erpLinkLabel} from '../src/erp-language.js'
import {erpNavigationText} from '../src/erpnext-navigation.js'

test('ERP display translations preserve identifiers and arbitrary business text',()=>{
 assert.equal(erpText('Employee'),'Nhân viên')
 assert.equal(erpText(' "Employee" '),'Nhân viên')
 assert.equal(erpNavigationText('Employee'),'Nhân viên')
 assert.equal(erpValue('Active',{fieldtype:'Select'}),'Đang hoạt động')
 assert.equal(erpValue('Active',{fieldtype:'Data',fieldname:'supplier_name'}),'Active')
 assert.equal(erpLinkLabel('Employee','DocType'),'Nhân viên')
 assert.equal(erpLinkLabel('Employee','Supplier'),'Employee')
 for(const key of ['constructor','toString','__proto__'])assert.equal(erpText(key),key)
 const option={value:'Active',label:'Active',extra:'retained'}
 assert.deepEqual(erpOption(option),{...option,label:'Đang hoạt động'})
 assert.equal(option.label,'Active')
})

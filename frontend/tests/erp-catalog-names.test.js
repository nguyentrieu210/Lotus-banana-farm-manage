import test from 'node:test'
import assert from 'node:assert/strict'
import {display} from '../src/erp-meta.js'

test('ERPNext default masters show in Vietnamese in every ERP list',()=>{
 assert.equal(display('All Supplier Groups',{fieldtype:'Link'}),'Tất cả nhóm nhà cung cấp')
 assert.equal(display('Raw Material',{fieldtype:'Data'}),'Nguyên vật liệu')
 assert.equal(display('Distributor',{}),'Nhà phân phối')
 assert.equal(display('Kim Ngoan',{fieldtype:'Data'}),'Kim Ngoan','names people typed stay as they are')
 assert.equal(display('Dịch vụ',{}),'Dịch vụ')
})

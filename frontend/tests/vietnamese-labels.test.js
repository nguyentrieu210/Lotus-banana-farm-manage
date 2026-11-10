import test from 'node:test'
import assert from 'node:assert/strict'
import {label,docLabel,stateLabel} from '../src/labels.js'
import {systemLabel} from '../src/system-translations.js'

test('Vietnamese system labels cover accounting, payroll and untranslated metadata fallbacks',()=>{
 assert.equal(systemLabel('Accounts'),'Kế toán')
 assert.equal(systemLabel('Account'),'Tài khoản kế toán')
 assert.equal(systemLabel('Bank Account'),'Tài khoản ngân hàng')
 assert.equal(systemLabel('Stock UOM'),'Đơn vị tính kho')
 assert.equal(systemLabel('Batch UOM'),'Đơn vị tính lô hàng')
 assert.equal(docLabel('Salary Slip'),'Phiếu lương')
 assert.equal(label('unmapped_custom_field','Accounting Period'),'Kỳ Kế toán')
 assert.equal(stateLabel('Supplier'),'Nhà cung cấp')
})

test('translation fallbacks retain document identifiers and existing Lotus terminology',()=>{
 assert.equal(docLabel('EMP-00001'),'EMP-00001')
 assert.equal(systemLabel(1250.5),1250.5)
 assert.equal(docLabel('Lotus Work Session'),'Buổi công theo phiếu')
})

test('kept fields show their own captions, not those of the removed alerts and forecast allocation',()=>{
 for(const caption of ['Loại','Loại giao','Loại mức','Nghiệp vụ'])assert.equal(label('kind',caption),caption)
 assert.equal(label('allocations','Phân bổ nguồn mua'),'Phân bổ nguồn mua')
})

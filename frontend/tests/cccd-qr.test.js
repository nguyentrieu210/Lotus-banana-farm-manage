import test from 'node:test'
import assert from 'node:assert/strict'
import {parseCccdQr} from '../src/cccd-qr.js'

test('QR with old CMND maps fields, no storage of old card number',()=>{
  const v=parseCccdQr('079203001234|123456789|NGUYỄN THỊ LAN|01011990|Nữ|Xã Thuận Lợi, Đồng Nai|15072024')
  assert.deepEqual(v,{
    cccd:'079203001234', employee_name:'NGUYỄN THỊ LAN',
    date_of_birth:'1990-01-01',gender:'Female',
    current_address:'Xã Thuận Lợi, Đồng Nai', lotus_id_issue_on:'2024-07-15'
  })
})
test('QR without old CMND works',()=>{
  const v=parseCccdQr('079203001234|LÊ VĂN AN|29/02/2000|Nam|Đồng Nai|2024-10-14')
  assert.equal(v.gender,'Male')
  assert.equal(v.date_of_birth,'2000-02-29')
})
test('QR with missing old number field works',()=>{
  const v=parseCccdQr('079203001234||TRẦN AN|01011990|Nam|Đồng Nai|')
  assert.equal(v.employee_name,'TRẦN AN')
  assert.equal(v.lotus_id_issue_on,'')
})
test('reject arbitrary QR, malformed identity, dates and unsafe fake genders',()=>{
  for (const input of [
    'https://example.com',
    '07920300123|NGUYỄN AN|01011990|Nam|Đồng Nai|15072024',
    '079203001234|NGUYỄN AN|31022000|Nam|Đồng Nai|15072024',
    '079203001234|NGUYỄN AN|01011990|abc|Đồng Nai|15072024',
    '079203001234|NGUYỄN AN|01011990|Nam||15072024',
    '079203001234|NGUYỄN AN|01011990|Nam|Đồng Nai|01011890',
    'a'.repeat(4097)
  ]) assert.throws(()=>parseCccdQr(input))
})

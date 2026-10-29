import test from 'node:test'
import assert from 'node:assert/strict'
import {applyPresence,presencePayload} from '../src/attendance-presence.js'

test('one session earns half, both sessions one day, preserving real stamps',()=>{
 const row={morning_present:1,afternoon_present:0,morning_time:'2026-10-29 06:46:00',afternoon_time:null}
 applyPresence(row);assert.equal(row.working_hours,4);assert.equal(row.workdays,.5)
 row.afternoon_present=1;row.afternoon_time='2026-10-29 13:01:00';applyPresence(row)
 assert.equal(row.working_hours,8);assert.equal(row.workdays,1)
 assert.equal(presencePayload(row).afternoon_time,'2026-10-29 13:01:00')
 row.morning_present=0;applyPresence(row);assert.equal(row.morning_time,null);assert.equal(row.workdays,.5)
})

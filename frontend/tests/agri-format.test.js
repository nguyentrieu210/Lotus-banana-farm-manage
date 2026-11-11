import test from 'node:test'
import assert from 'node:assert/strict'
import {isoWeek,isoWeekMonday,weeksInYear,addWeeks,weekLabel,weekRange,formatNumber,formatDelta,shortDate,initials} from '../src/agri-format.js'

test('ISO weeks: Monday start, week 1 holds the first Thursday, 2026 has 53 weeks',()=>{
 assert.deepEqual(isoWeek('2026-11-10'),{year:2026,week:46})
 assert.deepEqual(isoWeek('2026-11-09'),{year:2026,week:46})
 assert.deepEqual(isoWeek('2026-11-15'),{year:2026,week:46})
 assert.deepEqual(isoWeek('2026-11-16'),{year:2026,week:47})
 assert.deepEqual(isoWeek('2026-12-31'),{year:2026,week:53})
 assert.deepEqual(isoWeek('2027-01-03'),{year:2026,week:53})
 assert.deepEqual(isoWeek('2027-01-04'),{year:2027,week:1})
 assert.deepEqual(isoWeek(new Date(2026,10,10,23,30)),{year:2026,week:46})
 assert.equal(weeksInYear(2026),53);assert.equal(weeksInYear(2027),52)
 assert.equal(isoWeek('not a date'),null)
})

test('week arithmetic and labels',()=>{
 assert.equal(isoWeekMonday(2026,46),'2026-11-09')
 assert.deepEqual(addWeeks({year:2026,week:52},2),{year:2027,week:1})
 assert.deepEqual(addWeeks({year:2027,week:1},-1),{year:2026,week:53})
 assert.equal(weekLabel({year:2026,week:46}),'Tuần 46/2026')
 assert.equal(weekLabel({year:2026,week:46},{short:true}),'T46')
 assert.equal(weekRange({year:2026,week:46}),'09/11 – 15/11')
})

test('numbers: Vietnamese grouping, no invented zero',()=>{
 assert.equal(formatNumber(9328),'9.328')
 assert.equal(formatNumber(3.964,{digits:2}),'3,96')
 assert.equal(formatNumber(null),null);assert.equal(formatNumber(''),null);assert.equal(formatNumber('abc'),null)
 assert.equal(formatNumber(0),'0')
 assert.equal(formatDelta(12),'+12');assert.equal(formatDelta(-3.5,{digits:1}),'−3,5');assert.equal(formatDelta(0),'0')
 assert.equal(shortDate('2026-11-14'),'14/11')
 assert.equal(initials('Nguyễn Văn An'),'VA');assert.equal(initials('Hải'),'H');assert.equal(initials(''),'')
})

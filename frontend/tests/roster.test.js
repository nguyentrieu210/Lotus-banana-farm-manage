import test from 'node:test'
import assert from 'node:assert/strict'
import {addDays,changesFor,mondayOf,rotationChanges,shortShift} from '../src/roster.js'

test('dates step across months and find the Monday of a week',()=>{
 assert.equal(addDays('2026-10-31',1),'2026-11-01')
 assert.equal(mondayOf('2026-10-18'),'2026-10-12','Sunday belongs to the week starting Monday')
 assert.equal(mondayOf('2026-10-12'),'2026-10-12')
})

test('selected cells become one change per run of consecutive days',()=>{
 const cells=[{employee:'A',date:'2026-10-14'},{employee:'A',date:'2026-10-12'},{employee:'A',date:'2026-10-13'},{employee:'A',date:'2026-10-16'},{employee:'B',date:'2026-10-12'}]
 assert.deepEqual(changesFor(cells,'Ca 2'),[
  {employee:'A',from:'2026-10-12',to:'2026-10-14',shift:'Ca 2'},{employee:'A',from:'2026-10-16',to:'2026-10-16',shift:'Ca 2'},
  {employee:'B',from:'2026-10-12',to:'2026-10-12',shift:'Ca 2'}])
 assert.equal(changesFor([{employee:'A',date:'2026-10-12'}],null)[0].shift,'','no shift means a day off')
})

test('three shifts rotate weekly, optionally staggered between people',()=>{
 const plain=rotationChanges(['A'],'2026-10-12',3,['Ca 1','Ca 2','Ca 3'])
 assert.deepEqual(plain.map(c=>[c.from,c.to,c.shift]),[['2026-10-12','2026-10-18','Ca 1'],['2026-10-19','2026-10-25','Ca 2'],['2026-10-26','2026-11-01','Ca 3']])
 const staggered=rotationChanges(['A','B','C'],'2026-10-12',1,['Ca 1','Ca 2','Ca 3'],true)
 assert.deepEqual(staggered.map(c=>c.shift),['Ca 1','Ca 2','Ca 3'],'each shift is covered every week')
 assert.equal(shortShift('Ca 3'),'C3')
})

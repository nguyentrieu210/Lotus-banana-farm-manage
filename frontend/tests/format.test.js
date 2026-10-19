import test from 'node:test'
import assert from 'node:assert/strict'
import {formatDate,formatMonthShort} from '../src/format.js'

test('Vietnamese day/month display from Frappe ISO values',()=>{
 assert.equal(formatDate('2026-10-09'),'09/10/2026')
 assert.equal(formatDate('2026-10-09 23:59:59'),'09/10/2026','time part never shifts the day')
 assert.equal(formatDate(''),'—')
 assert.equal(formatDate(null,''),'')
 assert.equal(formatDate('Tháng sau'),'Tháng sau','non-dates pass through')
 assert.equal(formatMonthShort('2026-03'),'03/26')
})

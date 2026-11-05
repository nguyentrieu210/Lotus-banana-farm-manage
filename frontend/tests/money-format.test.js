import test from 'node:test'
import assert from 'node:assert/strict'
import {parseMoneyInput,formatMoneyInput} from '../src/money-format.js'

test('prices and quantities read the same whichever separator was typed or pasted', () => {
 const cases = {
  '531428,57': 531428.57, '531428.57': 531428.57, '531.428,57': 531428.57,
  '26.571.428,571': 26571428.571, '26,571,428.571': 26571428.571, '26571428,571': 26571428.571,
  '1.250.000': 1250000, '1,250,000': 1250000, '12300': 12300, '12.300': 12300,
  '996,4': 996.4, '996.4': 996.4, '0,5': 0.5, '45,': 45, '531.428.': 531428, '-1.500': -1500,
  '12.300 đ': 12300, '': '', ',': '', '-': ''
 }
 for (const [text, value] of Object.entries(cases)) assert.equal(parseMoneyInput(text), value, JSON.stringify(text))
})

test('typing 1.250.000 digit by digit ends at one million two hundred fifty thousand', () => {
 let text = '', last
 for (const ch of '1.250.000') { text += ch; last = parseMoneyInput(text) }
 assert.equal(last, 1250000)
})

test('the field shows the Vietnamese form', () => {
 assert.equal(formatMoneyInput(26571428.571), '26.571.428,571')
 assert.equal(formatMoneyInput(1500000), '1.500.000')
})

import test from 'node:test'
import assert from 'node:assert/strict'
import {renderMarkdown} from '../src/ai-markdown.js'

test('AI answers render tables, bold and lists, and never inject HTML',()=>{
 const html=renderMarkdown('**Tồn kho** KHO 2:\n\n| Vật tư | Số lượng |\n|---|---|\n| Bao cám | 500 |\n\n- một\n- hai\n> ghi chú')
 assert.match(html,/<strong>Tồn kho<\/strong>/)
 assert.match(html,/<table>.*<th>Vật tư<\/th>.*<td class="num">500<\/td>/s)
 assert.match(html,/<ul><li>một<\/li><li>hai<\/li><\/ul>/)
 assert.match(html,/<p>ghi chú<\/p>/)
 const evil=renderMarkdown('<img src=x onerror=alert(1)> **<script>x</script>**')
 assert.doesNotMatch(evil,/<img|<script/)
 assert.match(evil,/&lt;img/)
})

test('pipe text and incomplete tables always advance, including CRLF answers',()=>{
 assert.equal(renderMarkdown('| chưa đủ bảng\r\nTiếp theo'),'<p>| chưa đủ bảng<br>Tiếp theo</p>')
 assert.equal(renderMarkdown('|'),'<p>|</p>')
 assert.match(renderMarkdown('Nội dung\n| A | B |\n|---|---|\n| 1 | 2 |'),/<p>Nội dung<\/p><div class="ai-md-table">/)
 assert.doesNotMatch(renderMarkdown('| A |\n|---|\n| <svg onload=alert(1)> |'),/<svg/)
})

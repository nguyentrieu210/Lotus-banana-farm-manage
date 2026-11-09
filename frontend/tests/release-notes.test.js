import test from 'node:test'
import assert from 'node:assert/strict'
import {RELEASE_NOTES,latestId,unseenNotes} from '../src/release-notes.js'

const notes=[{id:'2026-12-01'},{id:'2026-11-20'},{id:'2026-11-09'}]

test('someone new sees only the latest update',()=>{
 assert.deepEqual(unseenNotes(notes,'').map(n=>n.id),['2026-12-01'])
})
test('someone who missed a few sees all they missed',()=>{
 assert.deepEqual(unseenNotes(notes,'2026-11-09').map(n=>n.id),['2026-12-01','2026-11-20'])
})
test('nothing opens once the latest has been seen',()=>{
 assert.deepEqual(unseenNotes(notes,'2026-12-01'),[])
 assert.equal(latestId(notes),'2026-12-01')
})
test('a second update on the same day still counts as new',()=>{
 assert.deepEqual(unseenNotes([{id:'2026-11-09b'},{id:'2026-11-09'}],'2026-11-09').map(n=>n.id),['2026-11-09b'])
})
test('the published list is newest first, with no repeated id',()=>{
 const ids=RELEASE_NOTES.map(n=>n.id)
 assert.deepEqual(ids,[...new Set(ids)].sort().reverse())
 for(const note of RELEASE_NOTES)assert.ok(note.title&&note.items.every(i=>i.title&&i.text),note.id)
})

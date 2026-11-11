import test from 'node:test'
import assert from 'node:assert/strict'
// api.js imports without file extensions (Vite style): load it through the test compiler.
import {loadModule} from './support/mount.mjs'

const {uploadFailure}=await loadModule('api.js')

test('a file the server cannot read is explained in Vietnamese, other upload errors keep their own message',()=>{
 assert.equal(uploadFailure({exc_type:'PdfReadError'},{name:'hoa-don.pdf'}).message,'Không đọc được tệp hoa-don.pdf (tệp hỏng hoặc không đúng định dạng). Chọn hoặc chụp lại tệp khác.')
 const own=uploadFailure({_server_messages:JSON.stringify([JSON.stringify({message:'Tệp quá lớn, tối đa 10 MB.'})])},{name:'a.jpg'})
 assert.equal(own.message,'Tệp quá lớn, tối đa 10 MB.')
})

test('an expired session or a refused right asks to log in again, not for another file',()=>{
 for(const [result,status] of [[{exc_type:'PermissionError'},403],[{},401],[{exc_type:'AuthenticationError'},200]])
  assert.match(uploadFailure(result,{name:'hoa-don.pdf'},status).message,/^Phiên đăng nhập đã hết .* Đăng nhập lại rồi tải lại tệp hoa-don\.pdf\.$/)
})

test('a server failure while saving the file is to retry, not a damaged file',()=>{
 const error=uploadFailure({exc_type:'QueryDeadlockError'},{name:'anh.jpg'},500)
 assert.equal(error.message,'Máy chủ chưa nhận được tệp anh.jpg (QueryDeadlockError). Thử lại sau ít phút.')
})

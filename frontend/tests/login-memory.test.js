import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import {window} from './support/mount.mjs'
test('login remembers only the account and lets the browser manage the password',()=>{
 const {document,localStorage}=window
 document.body.innerHTML='<form><input id="login_email"><div class="form-group"><input id="login_password" type="password"></div><p><a href="#forgot">Quên mật khẩu?</a></p></form>'
 localStorage.removeItem('lotus-login-username')
 vm.runInNewContext(fs.readFileSync(new URL('../../lotus_farm/public/js/lotus_login.js',import.meta.url),'utf8'),{document,localStorage})
 document.dispatchEvent(new window.Event('DOMContentLoaded'))
 const form=document.querySelector('form'),user=document.getElementById('login_email'),password=document.getElementById('login_password')
 assert.equal(user.autocomplete,'username');assert.equal(password.autocomplete,'current-password')
 assert.ok(document.querySelector('.lotus-login-options .lotus-remember-account'))
 assert.ok(document.querySelector('.lotus-remember-account input+.lotus-checkbox-mark'))
 assert.ok(document.querySelector('.lotus-login-options a[href="#forgot"]'))
 user.value='worker@example.com';password.value='test-value-never-store'
 form.dispatchEvent(new window.Event('submit'))
 assert.equal(localStorage.getItem('lotus-login-username'),'worker@example.com')
 assert.doesNotMatch(JSON.stringify(Object.values(localStorage)),/test-value-never-store/)
 document.getElementById('lotus-remember-account').click()
 assert.equal(localStorage.getItem('lotus-login-username'),'')
 document.body.innerHTML=''
})

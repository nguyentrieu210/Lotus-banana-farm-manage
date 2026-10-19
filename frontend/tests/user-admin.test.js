import test from 'node:test'
import assert from 'node:assert/strict'
import {mobileActions,hasMobileAccess} from '../src/mobile-menu.js'
import {workspaceDirectory} from '../src/workspace-directory.js'
import {workspaceModules} from '../src/workspace-routes.js'
test('user administration is exposed only through its server capability',()=>{
 assert.equal(workspaceModules['nguoi-dung'].capability,'user_admin')
 for(const session of [{},{capabilities:{hr:true}},{capabilities:{stock:true}}]){
  assert.ok(!mobileActions(session).some(x=>x.id==='users'))
  assert.ok(!workspaceDirectory(session).some(x=>x.id==='global-users'))
 }
 const admin={capabilities:{user_admin:true}}
 assert.ok(hasMobileAccess(admin))
 assert.equal(mobileActions(admin).find(x=>x.id==='users').href,'/lotus/nguoi-dung')
 assert.equal(workspaceDirectory(admin).find(x=>x.id==='global-users').href,'/lotus/nguoi-dung')
})

<script setup>
import {nextTick,onBeforeUnmount,ref,watch} from 'vue'
import {parseCccdQr} from '../cccd-qr.js'

const emit = defineEmits(['close','confirmed'])
const enabled = ref(false)
const scanning = ref(false)
const pending = ref(false)
const parsed = ref(null)
const error = ref('')
const notice = ref('')
const targetId = 'lotus-cccd-camera-' + Math.random().toString(36).slice(2)
let reader = null
let alive = true
let generation = 0

async function stopCamera() {
  generation++
  const active = reader
  reader = null
  scanning.value = false
  if (!active) return
  try { if (active.isScanning) await active.stop() } catch (_) { /* already stopped */ }
  try { active.clear() } catch (_) { /* no active renderer */ }
}
async function decoded(text) {
  if (!alive || pending.value || parsed.value) return
  try {
    const info = parseCccdQr(text)
    pending.value = true
    await stopCamera()
    if (alive) { parsed.value = info; error.value = ''; notice.value = 'Đọc QR thành công. Kiểm tra thông tin trước khi điền.' }
  } catch (e) {
    // Do not display raw QR data in the error or log it.
    error.value = e.message || 'Đây không phải mã QR căn cước được hỗ trợ.'
  } finally { pending.value = false }
}
async function openCamera() {
  if (!enabled.value || pending.value) return
  error.value = ''; notice.value = ''; parsed.value = null
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    error.value = 'Camera cần HTTPS hoặc localhost. Có thể chọn ảnh QR từ máy.'
    return
  }
  await stopCamera()
  await nextTick()
  const current = ++generation
  pending.value = true
  try {
    const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
    if (!alive || current !== generation) return
    reader = new Html5Qrcode(targetId, {formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
    await reader.start(
      {facingMode:'environment'},
      {fps:18,qrbox:(viewWidth,viewHeight)=>{
        const side=Math.max(100,Math.min(290,viewWidth-24,viewHeight-24))
        return {width:side,height:side}
      }},
      decoded,()=>{}
    )
    if (!alive || current !== generation) {await stopCamera();return}
    scanning.value = true
  } catch (_) {
    error.value = 'Không mở được camera. Hãy cấp quyền camera hoặc chọn ảnh QR.'
    await stopCamera()
  } finally {pending.value = false}
}
async function fromFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !enabled.value) return
  if (!file.type.startsWith('image/') || file.size > 8 * 1024 * 1024) {
    error.value = 'Chỉ chọn ảnh tối đa 8 MB.'
    return
  }
  error.value = '';notice.value = '';parsed.value = ''
  pending.value = true
  try {
    await stopCamera()
    await nextTick()
    const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
    if (!alive) return
    reader = new Html5Qrcode(targetId,{formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
    const value = await reader.scanFile(file,true)
    if (alive) {
      const info = parseCccdQr(value)
      parsed.value = info
      notice.value = 'Đọc ảnh QR thành công. Kiểm tra thông tin trước khi điền.'
    }
  } catch (e) {
    error.value = e.message?.startsWith('Ngày') || e.message?.includes('QR') ||
      e.message?.includes('Giới tính') || e.message?.includes('Họ tên') ||
      e.message?.includes('Địa chỉ') ? e.message : 'Không đọc được mã QR trong ảnh.'
  } finally {pending.value = false;await stopCamera()}
}
async function close() {await stopCamera();emit('close')}
async function confirm() {
  if (!parsed.value || !enabled.value) return
  emit('confirmed',{...parsed.value})
  await stopCamera()
}
watch(enabled,accepted=>{if(accepted)void openCamera();else void stopCamera()})
onBeforeUnmount(()=>{alive=false;void stopCamera()})
</script>

<template>
 <Teleport to="body"><div class="cccd-overlay" role="presentation" @click.self="close">
  <section class="cccd-dialog" role="dialog" aria-modal="true" aria-label="Quét căn cước">
   <header class="cccd-heading">
    <strong>Quét QR căn cước</strong>
    <button type="button" aria-label="Đóng" class="cccd-x" @click="close">×</button>
   </header>
   <p class="cccd-guide">Dùng mã QR in trên thẻ. Quét QR không xác thực thẻ thật hay chủ thẻ.</p>
   <label class="cccd-consent"><input type="checkbox" v-model="enabled"> Tôi đã thông báo cho người có thẻ về việc sử dụng thông tin để lập hồ sơ nhân sự.</label>
   <div :id="targetId" class="cccd-camera"></div>
   <p v-if="error" role="alert" class="cccd-error">{{error}}</p>
   <p v-if="notice" role="status" class="cccd-success">{{notice}}</p>
   <div v-if="parsed" class="cccd-preview">
    <div><small>Họ tên</small><strong>{{parsed.employee_name}}</strong></div>
    <div><small>Số định danh</small><strong>********{{parsed.cccd.slice(-4)}}</strong></div>
    <div><small>Ngày sinh</small><strong>{{parsed.date_of_birth}}</strong></div>
    <div><small>Giới tính</small><strong>{{parsed.gender==='Male'?'Nam':parsed.gender==='Female'?'Nữ':'Khác'}}</strong></div>
    <div><small>Nơi cư trú</small><strong>{{parsed.current_address}}</strong></div>
    <div><small>Ngày cấp</small><strong>{{parsed.lotus_id_issue_on||'Không có'}}</strong></div>
   </div>
   <div class="cccd-buttons">
    <button v-if="!parsed" type="button" :disabled="!enabled||pending||scanning" @click="openCamera">{{pending?'Đang mở…':scanning?'Đang quét…':'Mở camera'}}</button>
    <label v-if="!parsed" class="cccd-upload" :class="{disabled:!enabled||pending}">
      Chọn ảnh QR<input type="file" accept="image/*" :disabled="!enabled||pending" @change="fromFile">
    </label>
    <button v-if="parsed" type="button" @click="confirm">Dùng thông tin này</button>
    <button v-if="parsed" type="button" @click="openCamera">Quét lại</button>
    <button type="button" @click="close">Đóng</button>
   </div>
   <p class="cccd-guide">Dữ liệu chỉ điền vào hồ sơ khi xác nhận. Không lưu ảnh QR.</p>
  </section>
 </div></Teleport>
</template>

<style scoped>
.cccd-overlay{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;background:rgba(12,20,18,.78);padding:12px;isolation:isolate;color:#202c24}
.cccd-dialog{width:min(100%,480px);max-height:calc(100dvh - 24px);overflow-y:auto;background:#fff!important;opacity:1!important;color:#202c24!important;border-radius:16px;padding:18px;box-shadow:0 16px 48px #0007;overscroll-behavior:contain}
.cccd-heading{display:flex;justify-content:space-between;align-items:center;gap:12px}
.cccd-heading strong{font-size:18px}
.cccd-x{border:0;background:transparent;font-size:30px;color:inherit;cursor:pointer}
.cccd-guide{font-size:13px;line-height:1.5;margin:8px 0;color:#536258!important}
.cccd-consent{display:flex;gap:10px;line-height:1.5;font-size:14px;margin:12px 0}
.cccd-consent input{width:20px;height:20px;flex-shrink:0;margin-top:2px}
.cccd-camera{min-height:12px;overflow:hidden;border-radius:12px;background:#edf2ed}.cccd-camera video{object-fit:cover}
.cccd-error{color:#b42318;font-size:14px}.cccd-success{color:#167344;font-size:14px}
.cccd-preview{margin:12px 0;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cccd-preview div{display:flex;flex-direction:column;gap:3px;min-width:0}
.cccd-preview small{color:#59695e}
.cccd-preview strong{font-size:14px;overflow-wrap:anywhere}
.cccd-preview div:nth-child(5){grid-column:1/-1}
.cccd-buttons{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}.cccd-buttons button{min-height:46px;padding:10px 14px;border:1px solid #d7ded9;border-radius:10px;background:#fff;color:#202c24;font-size:14px;font-weight:650}.cccd-buttons button:first-child{background:#e65b35;color:#fff;border:1px solid #e65b35}
.cccd-upload{display:inline-flex;align-items:center;padding:8px 14px;border:1px solid #c3c3c3;border-radius:7px;cursor:pointer;font-size:14px}
.cccd-upload input{position:absolute;width:1px;height:1px;opacity:0}
.cccd-upload.disabled{opacity:.45;pointer-events:none}
@media(max-width:380px){.cccd-dialog{padding:12px}.cccd-preview{grid-template-columns:1fr 1fr}}
</style>

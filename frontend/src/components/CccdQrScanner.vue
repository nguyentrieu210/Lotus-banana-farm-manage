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
const cameraList = ref([])
const cameraId = ref('')
const targetId = 'lotus-cccd-camera-' + Math.random().toString(36).slice(2)
let reader = null
let alive = true
let generation = 0
let lastInvalidNotice = 0

function cameraErrorMessage(e) {
  const message = String(e?.name || '') + ' ' + String(e?.message || e || '')
  if (/NotAllowed|PermissionDenied|Permission denied|denied/i.test(message)) {
    return 'Camera bị từ chối quyền. Hãy cho phép camera trong cài đặt trang web, rồi bấm Mở camera.'
  }
  if (/NotFound|DevicesNotFound|no camera|requested device not found/i.test(message)) {
    return 'Không tìm thấy camera. Hãy thử chụp ảnh mã QR hoặc chọn ảnh từ máy.'
  }
  if (/NotReadable|TrackStart|Could not start|in use/i.test(message)) {
    return 'Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng camera rồi thử lại.'
  }
  return 'Không mở được camera trên trình duyệt này. Hãy thử Chrome/Safari hoặc chọn ảnh QR.'
}
async function stopCamera() {
  generation++
  const active = reader
  reader = null
  scanning.value = false
  if (!active) return
  try { if (active.isScanning) await active.stop() } catch (_) { /* already stopped */ }
  try { active.clear() } catch (_) { /* no renderer */ }
}
async function decoded(text) {
  if (!alive || pending.value || parsed.value || !enabled.value) return
  let info
  try {
    info = parseCccdQr(text)
  } catch (e) {
    // Keep the camera running when it sees a QR that is not a CCCD.
    // Never display or log the raw code content.
    const now = Date.now()
    if (now - lastInvalidNotice > 1800) {
      error.value = e.message || 'Mã vừa quét không phải QR căn cước.'
      lastInvalidNotice = now
    }
    return
  }
  pending.value = true
  try {
    await stopCamera()
    if (alive && enabled.value) {
      parsed.value = info
      error.value = ''
      notice.value = 'Đọc QR thành công. Kiểm tra thông tin trước khi điền.'
    }
  } finally { pending.value = false }
}
async function openCamera(next = false) {
  if (!enabled.value || pending.value || !alive) return
  error.value = ''; notice.value = ''; parsed.value = null
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    error.value = 'Camera chỉ hoạt động qua HTTPS hoặc localhost. Nếu đang mở bằng địa chỉ IP http, hãy dùng link HTTPS của Lotus hoặc chọn ảnh QR.'
    return
  }
  pending.value = true
  try {
    await stopCamera()
    await nextTick()
    const current = ++generation
    const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
    if (!alive || !enabled.value || current !== generation) return
    // Listing cameras after consent helps pick the real back lens on Android.
    let cameras = []
    try { cameras = await Html5Qrcode.getCameras() } catch (_) { /* use facingMode below */ }
    if (!alive || !enabled.value || current !== generation) return
    cameraList.value = cameras
    if (next && cameras.length > 1) {
      const index = cameras.findIndex(c => c.id === cameraId.value)
      cameraId.value = cameras[(index + 1) % cameras.length].id
    } else if (!cameraId.value && cameras.length) {
      const preferred = cameras.find(c => /back|rear|environment|sau|mặt sau/i.test(c.label) && !/ultra|wide|macro|0\.5/i.test(c.label))
        || cameras.find(c => /back|rear|environment|sau|mặt sau/i.test(c.label))
      cameraId.value = preferred?.id || ''
    }
    const options = {formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false}
    const config = {
      fps:15,
      qrbox:(width,height)=>{
        const side = Math.floor(Math.min(340,width-16,height-16))
        return {width:Math.max(100,side),height:Math.max(100,side)}
      },
      disableFlip:true,
    }
    let instance = new Html5Qrcode(targetId, options)
    reader = instance
    try {
      await instance.start(cameraId.value || {facingMode:'environment'},config,decoded,()=>{})
    } catch (firstError) {
      if (!cameraId.value && cameras.length) {
        // Some phones reject facingMode but accept a device ID.
        try { instance.clear() } catch (_) {}
        instance = new Html5Qrcode(targetId,options)
        reader = instance
        cameraId.value = cameras[0].id
        await instance.start(cameraId.value,config,decoded,()=>{})
      } else {
        throw firstError
      }
    }
    if (!alive || !enabled.value || current !== generation) {
      await stopCamera()
      return
    }
    scanning.value = true
    notice.value = 'Camera đã mở. Đưa toàn bộ mã QR vào khung và giữ yên vài giây.'
  } catch (e) {
    error.value = cameraErrorMessage(e)
    await stopCamera()
  } finally { pending.value = false }
}
async function fromFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !enabled.value || pending.value) return
  if (!file.type.startsWith('image/') || file.size > 8 * 1024 * 1024) {
    error.value = 'Chỉ chọn ảnh tối đa 8 MB.'
    return
  }
  error.value = ''; notice.value = ''; parsed.value = null
  pending.value = true
  try {
    await stopCamera()
    await nextTick()
    const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
    if (!alive || !enabled.value) return
    reader = new Html5Qrcode(targetId,{formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
    let value
    try { value = await reader.scanFile(file,true) }
    catch (_) { throw new Error('Không tìm thấy mã QR rõ nét trong ảnh. Hãy chụp gần hơn, đủ sáng và không bị lóa.') }
    const info = parseCccdQr(value)
    if (alive && enabled.value) {
      parsed.value = info
      notice.value = 'Đọc ảnh QR thành công. Kiểm tra thông tin trước khi điền.'
    }
  } catch (e) {
    error.value = e?.message || 'Không đọc được mã QR trong ảnh.'
  } finally {
    await stopCamera()
    pending.value = false
  }
}
async function close() { await stopCamera(); emit('close') }
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
   <p class="cccd-guide">Dùng mã QR in trên thẻ, không phải mã NFC. Quét QR không xác thực thẻ hay chủ thẻ.</p>
   <label class="cccd-consent"><input type="checkbox" v-model="enabled"> Tôi đã thông báo cho người có thẻ và được đồng ý sử dụng thông tin để lập hồ sơ.</label>
   <div :id="targetId" class="cccd-camera" :class="{active:scanning}"></div>
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
    <button v-if="!parsed" type="button" :disabled="!enabled||pending||scanning" @click="openCamera()">{{pending?'Đang mở…':scanning?'Đang quét…':'Mở camera'}}</button>
    <button v-if="!parsed&&scanning&&cameraList.length>1" type="button" :disabled="pending" @click="openCamera(true)">Đổi camera</button>
    <label v-if="!parsed" class="cccd-upload" :class="{disabled:!enabled||pending}">
      Chụp QR<input type="file" accept="image/*" capture="environment" :disabled="!enabled||pending" @change="fromFile">
    </label>
    <label v-if="!parsed" class="cccd-upload" :class="{disabled:!enabled||pending}">
      Chọn ảnh QR<input type="file" accept="image/*" :disabled="!enabled||pending" @change="fromFile">
    </label>
    <button v-if="parsed" type="button" @click="confirm">Dùng thông tin này</button>
    <button v-if="parsed" type="button" @click="openCamera()">Quét lại</button>
    <button type="button" @click="close">Đóng</button>
   </div>
   <p class="cccd-guide">Đưa mã QR gần camera, tránh bóng và phản sáng. Chỉ điền thông tin khi bạn xác nhận; không lưu ảnh QR.</p>
  </section>
 </div></Teleport>
</template>

<style scoped>
.cccd-overlay{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;background:rgba(12,20,18,.70);padding:12px;isolation:isolate;color:#202c24}
.cccd-dialog{width:min(100%,480px);max-height:calc(100dvh - 24px);overflow-y:auto;background:#fff!important;opacity:1!important;filter:none!important;color:#202c24!important;border-radius:16px;padding:16px;box-shadow:0 16px 48px #0007;overscroll-behavior:contain}
.cccd-heading{display:flex;justify-content:space-between;align-items:center;gap:12px}
.cccd-heading strong{font-size:18px}
.cccd-x{border:0;background:transparent;font-size:30px;color:inherit;cursor:pointer}
.cccd-guide{font-size:13px;line-height:1.5;margin:8px 0;color:#536258!important}
.cccd-consent{display:flex;gap:10px;line-height:1.5;font-size:14px;margin:12px 0}
.cccd-consent input{width:20px;height:20px;flex-shrink:0;margin-top:2px}
.cccd-camera{min-height:220px;overflow:hidden;border-radius:12px;background:#edf2ed}
.cccd-camera.active{background:#111}
.cccd-camera :deep(video){object-fit:cover}
.cccd-camera :deep(img){max-width:100%}
.cccd-error{color:#b42318;font-size:14px}.cccd-success{color:#167344;font-size:14px}
.cccd-preview{margin:12px 0;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cccd-preview div{display:flex;flex-direction:column;gap:3px;min-width:0}
.cccd-preview small{color:#59695e}
.cccd-preview strong{font-size:14px;overflow-wrap:anywhere}
.cccd-preview div:nth-child(5){grid-column:1/-1}
.cccd-buttons{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}.cccd-buttons button{min-height:44px;padding:10px 14px;border:1px solid #d7ded9;border-radius:10px;background:#fff;color:#202c24;font-size:14px;font-weight:650;cursor:pointer}.cccd-buttons button:first-child{background:#e65b35;color:#fff;border:1px solid #e65b35}
.cccd-buttons button:disabled{opacity:.55;cursor:default}
.cccd-upload{display:inline-flex;align-items:center;min-height:44px;padding:8px 14px;border:1px solid #c3c3c3;border-radius:10px;cursor:pointer;font-size:14px}
.cccd-upload input{position:absolute;width:1px;height:1px;opacity:0}
.cccd-upload.disabled{opacity:.45;pointer-events:none}
@media(max-width:380px){.cccd-dialog{padding:12px}.cccd-preview{grid-template-columns:1fr 1fr}}
</style>
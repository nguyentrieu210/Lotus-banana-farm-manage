<script setup>
import {nextTick,onMounted,onBeforeUnmount,ref,watch} from 'vue'
import {parseCccdQr} from '../cccd-qr.js'

const emit = defineEmits(['close','confirmed'])
const scannerDialog = ref(null)
const enabled = ref(false)
const scanning = ref(false)
const pending = ref(false)
const parsed = ref(null)
const error = ref('')
const notice = ref('')
const cameraList = ref([])
const cameraId = ref('')
const torchAvailable = ref(false)
const torchOn = ref(false)
const zoomSupported = ref(false)
const zoomLevel = ref(1)
const zoomRange = ref(null)
const targetId = 'lotus-cccd-camera-' + Math.random().toString(36).slice(2)
let reader = null
let alive = true
let generation = 0
let lastInvalidNotice = 0

onMounted(() => scannerDialog.value?.showModal())
onBeforeUnmount(() => { alive = false; void stopCamera(); scannerDialog.value?.close() })

function cameraErrorMessage(e) {
  const message = String(e?.name || '') + ' ' + String(e?.message || e || '')
  if (/NotAllowed|PermissionDenied|Permission denied|denied/i.test(message)) return 'Chưa cấp quyền camera. Hãy cho phép camera trong cài đặt trang web.'
  if (/NotFound|DevicesNotFound|no camera|requested device not found/i.test(message)) return 'Không tìm thấy camera. Thử dùng camera điện thoại để chụp QR.'
  if (/NotReadable|TrackStart|Could not start|in use/i.test(message)) return 'Camera đang bị ứng dụng khác sử dụng. Đóng ứng dụng đó rồi thử lại.'
  return 'Không mở được camera. Hãy thử Chrome/Safari hoặc chụp QR bằng camera điện thoại.'
}

async function stopCamera() {
  generation++
  const active = reader
  reader = null
  scanning.value = false
  torchAvailable.value = false
  torchOn.value = false
  zoomSupported.value = false
  zoomLevel.value = 1
  zoomRange.value = null
  if (!active) return
  try { if (active.isScanning) await active.stop() } catch (_) { /* camera already stopped */ }
  try { active.clear() } catch (_) { /* renderer already removed */ }
}

async function decoded(raw) {
  if (!alive || !enabled.value || pending.value || parsed.value) return
  let info
  try { info = parseCccdQr(raw) }
  catch (e) {
    if (Date.now() - lastInvalidNotice > 2000) {
      error.value = e.message || 'QR vừa thấy không phải QR căn cước.'
      lastInvalidNotice = Date.now()
    }
    return
  }
  pending.value = true
  try {
    await stopCamera()
    if (alive && enabled.value) {
      parsed.value = info
      error.value = ''
      notice.value = 'Đã đọc QR. Kiểm tra thông tin trước khi điền.'
    }
  } finally { pending.value = false }
}

function chooseBackCamera(cameras) {
  const back = cameras.filter(c => /back|rear|environment|sau|mặt sau/i.test(c.label))
  const main = back.find(c => /main|wide(?!.*ultra)|camera\s*0|chính/i.test(c.label)
    && !/ultra|macro|telephoto|depth|0\.5/i.test(c.label))
    || back.find(c => !/ultra|macro|telephoto|depth|0\.5/i.test(c.label))
  return main?.id || back[0]?.id || ''
}

async function improveFocus(active) {
  try {
    const caps = active.getRunningTrackCapabilities()
    const advanced = []
    if (caps?.focusMode?.includes('continuous')) advanced.push({focusMode:'continuous'})
    if (caps?.exposureMode?.includes('continuous')) advanced.push({exposureMode:'continuous'})
    if (advanced.length) await active.applyVideoConstraints({advanced})
    torchAvailable.value = !!caps?.torch
    if (caps?.zoom?.max > caps?.zoom?.min) {
      zoomSupported.value = true
      zoomRange.value = caps.zoom
      zoomLevel.value = active.getRunningTrackSettings()?.zoom || caps.zoom.min || 1
    }
  } catch (_) { /* unsupported hardware: keep scanning */ }
}

async function openCamera(switchLens = false) {
  if (!alive || !enabled.value || pending.value) return
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    error.value = 'Camera cần link HTTPS. Hãy mở app Lotus qua HTTPS hoặc dùng Chụp QR.'
    return
  }
  pending.value = true
  error.value = ''
  notice.value = ''
  parsed.value = null
  try {
    await stopCamera()
    await nextTick()
    const current = ++generation
    const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
    if (!alive || !enabled.value || current !== generation) return
    let cameras = []
    try { cameras = await Html5Qrcode.getCameras() } catch (_) { /* facingMode fallback */ }
    if (!alive || !enabled.value || current !== generation) return
    cameraList.value = cameras
    if (switchLens && cameras.length > 1) {
      const idx = cameras.findIndex(c => c.id === cameraId.value)
      cameraId.value = idx === -1 ? (chooseBackCamera(cameras) || cameras[0].id) : cameras[(idx + 1) % cameras.length].id
    } else if (!switchLens) {
      // Let Android choose the default back camera first (usually the lens
      // with working close-focus). Enumerated camera IDs can point to ultrawide.
      cameraId.value = ''
    }

    const constraints = cameraId.value
      ? {deviceId:{exact:cameraId.value},width:{ideal:1920},height:{ideal:1080}}
      : {facingMode:'environment',width:{ideal:1920},height:{ideal:1080}}
    const config = {
      // Important: scan the complete camera frame. The old qrbox was cropped
      // to a very thin stripe on some Android devices, so QR was never decoded.
      fps:15,
      videoConstraints:constraints,
      disableFlip:true,
    }
    let active = new Html5Qrcode(targetId,{formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
    reader = active
    try { await active.start(cameraId.value || {facingMode:'environment'},config,decoded,()=>{}) }
    catch (first) {
      // Some Android devices list virtual lenses that cannot actually be opened.
      if (!cameraId.value) throw first
      try { active.clear() } catch (_) {}
      active = new Html5Qrcode(targetId,{formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
      reader = active
      cameraId.value = ''
      config.videoConstraints = {facingMode:'environment',width:{ideal:1280},height:{ideal:720}}
      await active.start({facingMode:'environment'},config,decoded,()=>{})
    }
    if (!alive || !enabled.value || current !== generation) { await stopCamera(); return }
    scanning.value = true
    notice.value = 'Đưa mã QR vào giữa hình. Nếu camera khó lấy nét, thử xa hơn một chút hoặc chụp QR.'
    void improveFocus(active)
  } catch (e) {
    error.value = cameraErrorMessage(e)
    await stopCamera()
  } finally { pending.value = false }
}

async function toggleZoom() {
  if (!reader || !zoomSupported.value || !zoomRange.value || pending.value) return
  try {
    const caps = zoomRange.value
    const target = zoomLevel.value > caps.min + 0.2 ? caps.min : Math.min(caps.max,Math.max(1.7,caps.min))
    await reader.applyVideoConstraints({advanced:[{zoom:target}]})
    zoomLevel.value = target
  } catch (_) {
    zoomSupported.value = false
    error.value = 'Camera không hỗ trợ phóng to.'
  }
}

async function toggleTorch() {
  if (!reader || !scanning.value || pending.value) return
  try {
    const on = !torchOn.value
    await reader.applyVideoConstraints({advanced:[{torch:on}]})
    torchOn.value = on
  } catch (_) {
    torchAvailable.value = false
    error.value = 'Camera này không hỗ trợ bật đèn.'
  }
}

// Read large phone photos locally; do not send ID images to a server.
async function preparePhoto(file,centerCrop = false) {
  if (!file.type.startsWith('image/') && !/\.(jpg|jpeg|png|webp|heic|heif)$/i.test(file.name)) {
    throw new Error('Hãy chọn ảnh QR (JPG, PNG hoặc WebP).')
  }
  if (file.size > 40*1024*1024) throw new Error('Ảnh quá lớn (trên 40 MB). Hãy chụp lại ảnh QR.')
  let image
  try { image = await createImageBitmap(file) }
  catch (_) {
    const url = URL.createObjectURL(file)
    try {
      image = new Image()
      image.src = url
      await image.decode()
    } catch (_) { throw new Error('Không mở được ảnh này. Hãy dùng camera điện thoại chụp JPG.') }
    finally { URL.revokeObjectURL(url) }
  }
  const width = image.width || image.naturalWidth
  const height = image.height || image.naturalHeight
  try {
    // A centered crop keeps small QR pixels instead of shrinking the entire photo.
    const factor = centerCrop ? 0.62 : 1
    const sx = Math.floor(width * (1-factor) / 2)
    const sy = Math.floor(height * (1-factor) / 2)
    const sw = Math.floor(width * factor)
    const sh = Math.floor(height * factor)
    const scale = Math.min(1,3200/Math.max(sw,sh))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1,Math.round(sw*scale))
    canvas.height = Math.max(1,Math.round(sh*scale))
    const context = canvas.getContext('2d',{willReadFrequently:true})
    if (!context) throw new Error('Không xử lý được ảnh QR.')
    context.drawImage(image,sx,sy,sw,sh,0,0,canvas.width,canvas.height)
    const blob = await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.9))
    if (!blob) throw new Error('Không xử lý được ảnh QR.')
    return new File([blob],'cccd-qr.jpg',{type:'image/jpeg'})
  } finally { if (typeof image.close === 'function') image.close() }
}

async function scanPhoto(file) {
  // Try native barcode reader first where supported (often better with small QR).
  if (typeof window.BarcodeDetector === 'function') {
    try {
      const detector = new window.BarcodeDetector({formats:['qr_code']})
      const img = await createImageBitmap(file)
      try {
        const results = await detector.detect(img)
        if (results.length) return results[0].rawValue
      } finally { img.close() }
    } catch (_) { /* try local JS decoder below */ }
  }
  const {Html5Qrcode,Html5QrcodeSupportedFormats} = await import('html5-qrcode')
  if (!alive) return ''
  reader = new Html5Qrcode(targetId,{formatsToSupport:[Html5QrcodeSupportedFormats.QR_CODE],verbose:false})
  try { return await reader.scanFile(file,false) }
  catch (_) { throw new Error('Không tìm thấy mã QR rõ nét. Hãy chụp sát phần mã QR, đủ sáng và tránh lóa.') }
}

async function fromFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !enabled.value || pending.value) return
  error.value = ''
  notice.value = ''
  parsed.value = null
  pending.value = true
  try {
    await stopCamera()
    await nextTick()
    if (!alive || !enabled.value) return
    let raw = ''
    // Read the original high-detail photo first. A small QR can disappear when
    // a phone photo is downscaled before decoding.
    if (file.size <= 16*1024*1024) {
      try { raw = await scanPhoto(file) } catch (_) { await stopCamera() }
    }
    if (!raw) {
      try { raw = await scanPhoto(await preparePhoto(file)) }
      catch (_) { await stopCamera() }
    }
    if (!raw) raw = await scanPhoto(await preparePhoto(file,true))
    const info = parseCccdQr(raw)
    if (alive && enabled.value) {
      parsed.value = info
      notice.value = 'Đã đọc QR từ ảnh. Kiểm tra thông tin trước khi điền.'
      error.value = ''
    }
  } catch (e) { error.value = e?.message || 'Không đọc được QR trong ảnh.' }
  finally { await stopCamera(); pending.value = false }
}

async function close() { await stopCamera(); emit('close') }
async function confirm() {
  if (!parsed.value || !enabled.value) return
  emit('confirmed',{...parsed.value})
  await stopCamera()
}
watch(enabled,accepted=>{ if (accepted) void openCamera(); else void stopCamera() })
</script>

<template>
 <Teleport to="body">
  <dialog ref="scannerDialog" class="cccd-dialog" aria-label="Quét QR căn cước" @cancel.prevent="close">
   <header class="cccd-heading">
    <strong>Quét căn cước</strong>
    <button type="button" aria-label="Đóng" class="cccd-x" @click="close">×</button>
   </header>
   <p class="cccd-guide">Đưa mã QR trên thẻ vào giữa khung.</p>
   <label class="cccd-consent">
    <input v-model="enabled" type="checkbox">
    <span>Đã được người có thẻ đồng ý dùng thông tin để lập hồ sơ.</span>
   </label>
   <div class="cccd-view">
    <div v-show="!parsed" :id="targetId" class="cccd-camera" :class="{active:scanning}"></div>
    <div v-if="!parsed&&!scanning&&!pending" class="cccd-placeholder">
     <span class="cccd-symbol">▣</span><span>{{enabled?'Sẵn sàng quét QR':'Đánh dấu đồng ý để mở camera'}}</span>
    </div>
    <div v-if="pending" class="cccd-loading">Đang xử lý…</div>
    <div v-if="scanning" class="cccd-aim" aria-hidden="true"><span></span></div>
    <div v-if="scanning" class="cccd-camera-actions">
     <button v-if="cameraList.length>1" type="button" aria-label="Đổi camera" title="Đổi camera" :disabled="pending" @click="openCamera(true)">⟳</button>
     <button v-if="zoomSupported" type="button" :aria-label="zoomLevel>1.2?'Thu nhỏ':'Phóng to'" :disabled="pending" @click="toggleZoom" class="cccd-zoom">{{zoomLevel>1.2?'1×':'1.7×'}}</button>
     <button v-if="torchAvailable" type="button" :aria-label="torchOn?'Tắt đèn':'Bật đèn'" :disabled="pending" @click="toggleTorch">{{torchOn?'☀':'☼'}}</button>
    </div>
   </div>
   <p v-if="error" role="alert" class="cccd-error">{{error}}</p>
   <p v-else-if="notice&&!parsed" role="status" class="cccd-hint">{{notice}}</p>
   <div v-if="parsed" class="cccd-preview">
    <div><small>Họ và tên</small><strong>{{parsed.employee_name}}</strong></div>
    <div><small>Ngày sinh</small><strong>{{parsed.date_of_birth}}</strong></div>
    <div><small>Giới tính</small><strong>{{parsed.gender==='Male'?'Nam':parsed.gender==='Female'?'Nữ':'Khác'}}</strong></div>
    <div><small>Số định danh</small><strong>•••• •••• {{parsed.cccd.slice(-4)}}</strong></div>
    <div class="cccd-address"><small>Nơi cư trú</small><strong>{{parsed.current_address}}</strong></div>
    <div><small>Ngày cấp</small><strong>{{parsed.lotus_id_issue_on||'Không có'}}</strong></div>
   </div>
   <template v-if="parsed">
    <button type="button" class="cccd-primary" @click="confirm">Dùng thông tin này</button>
    <button type="button" class="cccd-textbutton" @click="openCamera()">Quét lại</button>
   </template>
   <template v-else>
    <button v-if="enabled&&!scanning&&!pending" class="cccd-primary" type="button" @click="openCamera()">Mở camera quét QR</button>
    <div class="cccd-photos">
     <label :class="{disabled:!enabled||pending}">
      <span>Chụp ảnh QR</span>
      <input type="file" accept="image/*" capture="environment" :disabled="!enabled||pending" @change="fromFile">
     </label>
     <label :class="{disabled:!enabled||pending}">
      <span>Chọn ảnh có QR</span>
      <input type="file" accept="image/*" :disabled="!enabled||pending" @change="fromFile">
     </label>
    </div>
   </template>
   <p class="cccd-foot">Chỉ dùng thông tin sau khi xác nhận. Không lưu ảnh QR.</p>
  </dialog>
 </Teleport>
</template>

<style scoped>
.cccd-dialog::backdrop{background:rgba(12,20,18,.72)}
.cccd-dialog{border:0;margin:auto;width:min(100% - 20px,430px);max-height:calc(100dvh - 20px);overflow-y:auto;background:#fff!important;color:#202c24!important;border-radius:18px;padding:16px;box-shadow:0 12px 36px #0005;overscroll-behavior:contain}
.cccd-heading{display:flex;justify-content:space-between;align-items:center;gap:12px}
.cccd-heading strong{font-size:18px;font-weight:750}
.cccd-x{border:0;background:transparent;font-size:30px;line-height:1;color:#263329;cursor:pointer;padding:4px 6px}
.cccd-guide{font-size:14px;color:#58695b;margin:6px 0 10px}
.cccd-consent{display:flex;align-items:flex-start;gap:10px;margin:8px 0 12px;color:#3b4e3f;font-size:13px;line-height:1.4}
.cccd-consent input{width:20px;height:20px;flex:none;margin:0;accent-color:#e65338}
.cccd-view{position:relative;border-radius:12px;overflow:hidden;background:#152019;min-height:220px;aspect-ratio:1/1;max-height:360px}
.cccd-camera{width:100%;height:100%;min-height:220px;overflow:hidden}
.cccd-camera :deep(video){object-fit:cover;max-width:100%}
.cccd-placeholder,.cccd-loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;color:#fff;font-size:14px;text-align:center;pointer-events:none;padding:12px}
.cccd-placeholder .cccd-symbol{font-size:52px;opacity:.72}
.cccd-loading{background:#15201999}
/* Reticle is decoration only; scanning uses the full video frame. */
.cccd-aim{position:absolute;left:16%;top:16%;width:68%;height:68%;border:2px solid rgba(255,255,255,.9);border-radius:10px;box-shadow:0 0 0 300px rgba(0,0,0,.08);pointer-events:none}
.cccd-aim span{position:absolute;left:25%;top:50%;width:50%;height:1px;background:rgba(255,255,255,.45)}
.cccd-camera-actions{position:absolute;right:9px;top:9px;display:flex;gap:6px}
.cccd-camera-actions button{border:1px solid #fff6;border-radius:30px;background:#161f1cbb;color:#fff;font-size:24px;line-height:1;width:44px;height:44px;cursor:pointer}
.cccd-camera-actions button:disabled{opacity:.5}
.cccd-camera-actions .cccd-zoom{font-size:13px;font-weight:750}
.cccd-error{color:#b42318;font-size:13px;line-height:1.4;margin:10px 0}
.cccd-hint{color:#526659;font-size:13px;line-height:1.4;margin:10px 0}
.cccd-primary{display:block;width:100%;min-height:46px;border:0;background:#e65338;color:#fff;font-size:15px;font-weight:700;border-radius:12px;margin:12px 0 8px;cursor:pointer}
.cccd-photos{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.cccd-photos label{display:flex;align-items:center;justify-content:center;text-align:center;min-height:48px;border:1px solid #cbd8d0;border-radius:12px;background:#f8faf8;color:#243a2b;font-size:14px;font-weight:650;cursor:pointer;position:relative}
.cccd-photos input{position:absolute;width:1px;height:1px;opacity:0}
.cccd-photos .disabled{opacity:.4;pointer-events:none}
.cccd-textbutton{display:block;border:0;background:transparent;color:#2c5f4a;font-size:14px;font-weight:650;margin:4px auto 0;padding:12px}
.cccd-foot{font-size:12px;color:#79877a;text-align:center;margin:10px 0 0;line-height:1.4}
.cccd-preview{margin:12px 0 8px;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cccd-preview>div{display:flex;flex-direction:column;gap:3px;min-width:0}
.cccd-preview small{font-size:12px;color:#677469}
.cccd-preview strong{font-size:14px;overflow-wrap:anywhere}
.cccd-preview .cccd-address{grid-column:1/-1}
@media(max-width:370px){.cccd-dialog{padding:12px}.cccd-view{min-height:190px}.cccd-camera{min-height:190px}}
</style>
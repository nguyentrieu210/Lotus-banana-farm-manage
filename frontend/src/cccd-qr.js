/**
 * Read common Vietnamese CCCD / Can cuoc QR payloads entirely on device.
 * QR is self-reported card data, NOT an authenticity or identity check.
 * Data format: ID | old ID (optional) | full name | DOB | sex | residence | issue date.
 * Do not log or persist raw QR strings.
 */
function dateIso(value, required = false) {
  const text = String(value || '').trim()
  if (!text && !required) return ''
  let dd, mm, yy
  if (/^\d{8}$/.test(text)) {
    dd = text.slice(0, 2); mm = text.slice(2, 4); yy = text.slice(4)
  } else {
    const dmy = text.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/)
    const ymd = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
    if (dmy) [, dd, mm, yy] = dmy
    else if (ymd) [, yy, mm, dd] = ymd
    else throw new Error('Ngày trong mã QR không đúng định dạng.')
  }
  const day = Number(dd), month = Number(mm), year = Number(yy)
  const check = new Date(Date.UTC(year, month - 1, day))
  if (year < 1900 || year > 2100 || check.getUTCFullYear() !== year ||
      check.getUTCMonth() !== month - 1 || check.getUTCDate() !== day) {
    throw new Error('Ngày trong mã QR không hợp lệ.')
  }
  return [yy, String(month).padStart(2, '0'), String(day).padStart(2, '0')].join('-')
}

export function parseCccdQr(raw) {
  if (typeof raw !== 'string' || raw.length > 4096) {
    throw new Error('Không nhận được mã QR căn cước hợp lệ.')
  }
  const parts = raw.replace(/^\uFEFF/, '').trim().split('|').map(v => v.trim())
  if (parts.length < 5 || parts.length > 12) {
    throw new Error('Mã QR không đúng dạng căn cước Việt Nam.')
  }
  const cccd = parts[0]
  if (!/^\d{12}$/.test(cccd)) {
    throw new Error('Không tìm thấy số định danh 12 chữ số trên QR.')
  }
  const hasOldId = /^(?:\d{9}|\d{12})?$/.test(parts[1]) &&
    (parts[1] === '' || /^\d{9}$/.test(parts[1]) || parts.length >= 7)
  const offset = hasOldId ? 1 : 0
  const fullName = parts[1 + offset] || ''
  const dob = parts[2 + offset] || ''
  const genderText = (parts[3 + offset] || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const address = (parts[4 + offset] || '').trim()
  const issued = parts[5 + offset] || ''
  if (!/^[\p{L}\s.'’-]{2,140}$/u.test(fullName)) {
    throw new Error('Họ tên trên QR không hợp lệ.')
  }
  const gender = genderText === 'nam' || genderText === 'male' ? 'Male' :
    genderText === 'nu' || genderText === 'female' ? 'Female' :
    genderText === 'khac' || genderText === 'other' ? 'Other' : ''
  if (!gender) throw new Error('Giới tính trên QR không nhận diện được.')
  if (!address || address.length > 300) throw new Error('Địa chỉ trên QR không hợp lệ.')
  const date_of_birth = dateIso(dob, true)
  const lotus_id_issue_on = dateIso(issued)
  if (lotus_id_issue_on && lotus_id_issue_on < date_of_birth) {
    throw new Error('Ngày cấp trên QR trước ngày sinh.')
  }
  return {
    cccd,
    employee_name: fullName.replace(/\s+/g, ' '),
    date_of_birth,
    gender,
    current_address: address,
    lotus_id_issue_on,
  }
}

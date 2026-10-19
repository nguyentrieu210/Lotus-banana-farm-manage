// Let the browser password manager save the password. Only the username preference
// belongs in localStorage; authentication and MFA remain Frappe's native flow.
document.addEventListener('DOMContentLoaded', () => {
 const username=document.getElementById('login_email'),password=document.getElementById('login_password')
 const form=password?.closest('form')
 if(!form||!username)return
 form.setAttribute('autocomplete','on')
 username.setAttribute('autocomplete','username');username.setAttribute('name','username')
 password.setAttribute('autocomplete','current-password');password.setAttribute('name','password')
 const key='lotus-login-username'
 const label=document.createElement('label');label.className='lotus-remember-account'
 const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.id='lotus-remember-account'
 checkbox.checked=true
 try{const preference=localStorage.getItem(key);if(preference!==null){checkbox.checked=preference!=='';if(preference&&!username.value)username.value=preference}}catch{}
 label.append(checkbox,document.createTextNode('Ghi nhớ tài khoản trên thiết bị này'))
 password.closest('.form-group')?.after(label)
 checkbox.addEventListener('change',()=>{if(!checkbox.checked)try{localStorage.setItem(key,'')}catch{}})
 form.addEventListener('submit',()=>{try{localStorage.setItem(key,checkbox.checked?username.value.trim():'')}catch{}},true)
})

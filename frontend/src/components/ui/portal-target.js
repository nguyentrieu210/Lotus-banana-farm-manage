import {inject,unref} from 'vue'
// Floating content (combobox list, date calendar, popover) must render inside an open modal <dialog>:
// a modal dialog makes everything else inert, so a list teleported to <body> would be unclickable.
export function useDialogPortal(){
 const provided=inject('searchSelectTarget',null)
 return function target(element){
  const value=unref(provided)
  if(value&&value!=='body')return value
  return element?.closest?.('dialog[open]')||'body'
 }
}

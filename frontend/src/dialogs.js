// Native dialog backdrops dispatch clicks at the dialog itself. Padding inside
// the dialog does too, so only dismiss clicks outside its actual rectangle.
export function dismissOnBackdrop(event,busy=false){
  const dialog=event.currentTarget
  if(busy||event.target!==dialog)return
  const rect=dialog.getBoundingClientRect()
  if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close()
}

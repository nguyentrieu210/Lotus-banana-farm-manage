// Small, always different files for uploads (identical content uploaded by two people would share one stored file).
const zlib=require('zlib'),fs=require('fs'),path=require('path'),crypto=require('crypto')
function chunk(type,data){const len=Buffer.alloc(4);len.writeUInt32BE(data.length);const td=Buffer.concat([Buffer.from(type),data]);const crc=Buffer.alloc(4);crc.writeUInt32BE(zlib.crc32(td)>>>0);return Buffer.concat([len,td,crc])}
function png(width=320,height=200){
 const [r,g,b]=crypto.randomBytes(3)
 const rows=[]
 for(let y=0;y<height;y++){const row=Buffer.alloc(1+width*3);for(let x=0;x<width;x++){const k=1+x*3;const line=(x+y)%37<3;row[k]=line?20:r;row[k+1]=line?20:g;row[k+2]=line?20:b}rows.push(row)}
 const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(width,0);ihdr.writeUInt32BE(height,4);ihdr[8]=8;ihdr[9]=2;ihdr[10]=0;ihdr[11]=0;ihdr[12]=0
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('IDAT',zlib.deflateSync(Buffer.concat(rows))),chunk('IEND',Buffer.alloc(0))])
}
function pdf(text){
 const safe=text.replace(/[()\\]/g,'')
 const stream='BT /F1 14 Tf 20 100 Td ('+safe+') Tj ET'
 const objects=['<</Type/Catalog/Pages 2 0 R>>','<</Type/Pages/Kids[3 0 R]/Count 1>>',
  '<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>',
  '<</Length '+stream.length+'>>\nstream\n'+stream+'\nendstream','<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>']
 let out='%PDF-1.4\n%'+crypto.randomBytes(6).toString('hex')+'\n';const offsets=[]
 objects.forEach((o,i)=>{offsets.push(Buffer.byteLength(out));out+=(i+1)+' 0 obj\n'+o+'\nendobj\n'})
 const xref=Buffer.byteLength(out)
 out+='xref\n0 '+(objects.length+1)+'\n0000000000 65535 f \n'+offsets.map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')
 out+='trailer\n<</Size '+(objects.length+1)+'/Root 1 0 R>>\nstartxref\n'+xref+'\n%%EOF\n'
 return Buffer.from(out)
}
const dir=path.join(__dirname,'fixtures');fs.mkdirSync(dir,{recursive:true})
function file(name,kind='png',text='Lotus UAT'){const p=path.join(dir,Date.now()+'-'+crypto.randomBytes(3).toString('hex')+'-'+name);fs.writeFileSync(p,kind==='pdf'?pdf(text):png());return p}
module.exports={file}

const fs=require('node:fs');
const path=require('node:path');
const cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
const frontend=path.join(root,'lotus_farm','public','frontend');
const staging=path.join(__dirname,'hr-native-staging');
fs.mkdirSync(staging,{recursive:true});
const prodManifestFile=path.join(staging,'prod-manifest.json');
cp.execFileSync('docker',['cp','lotus-backend-1:/home/frappe/frappe-bench/apps/lotus_farm/lotus_farm/public/frontend/.vite/manifest.json',prodManifestFile]);
const old=JSON.parse(fs.readFileSync(prodManifestFile,'utf8'));
const latest=JSON.parse(fs.readFileSync(path.join(frontend,'.vite','manifest.json'),'utf8'));
const oldHr=old['hr-mobile.html'],newHr=latest['hr-mobile.html'];
if(!oldHr||!newHr)throw Error('Missing mobile entry');
const oldImports=oldHr.imports.filter(k=>!k.includes('CccdQrScanner')).sort();
const newImports=newHr.imports.filter(k=>!k.includes('CccdQrScanner')).sort();
if(JSON.stringify(oldImports)!==JSON.stringify(newImports))throw Error('Changed non-scanner dependencies; abort selective deploy');
const scannerKey=newHr.imports.find(k=>k.includes('CccdQrScanner'));
if(!scannerKey||!latest[scannerKey])throw Error('Missing newly compiled scanner chunk');
const changed=[...new Set([newHr.file,latest[scannerKey].file,...(latest[scannerKey].css||[])])];
const merged={...old,'hr-mobile.html':newHr,[scannerKey]:latest[scannerKey]};
for(const k of Object.keys(latest)){
 const val=latest[k];
 if(val?.file && changed.includes(val.file))merged[k]=val;
}
for(const relativeFile of changed){
 const source=path.join(frontend,relativeFile),dest=path.join(staging,'assets',path.basename(relativeFile));
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 fs.copyFileSync(source,dest);
}
fs.writeFileSync(path.join(staging,'manifest.json'),JSON.stringify(merged,null,2)+'\n');
console.log(JSON.stringify({old:oldHr.file,new:newHr.file,scanner:latest[scannerKey].file,assets:changed},null,2));

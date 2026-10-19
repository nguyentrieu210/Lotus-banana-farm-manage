// Display registration from lotus-map v2; source KML and XYZ coordinates stay intact.
export function alignedTiles(L,url,options,alignment){
 const half=Math.PI*6378137
 const Tiles=L.TileLayer.extend({
  _getTilePos(c){
   const size=this.getTileSize(),unit=2*half/(256*2**c.z),o=alignment.originMercator,a=alignment.matrixCentered
   const x=c.x*size.x*unit-half-o[0],y=half-c.y*size.y*unit-o[1]
   const px=o[0]+a[0][0]*x+a[0][1]*y+a[0][2],py=o[1]+a[1][0]*x+a[1][1]*y+a[1][2]
   return L.point((px+half)/unit,(half-py)/unit).subtract(this._level.origin)
  },
  createTile(c,done){
   const tile=document.createElement('div'),img=document.createElement('img'),size=this.getTileSize(),a=alignment.matrixCentered
   tile.style.overflow='visible';img.alt='';img.setAttribute('role','presentation')
   Object.assign(img.style,{width:size.x+'px',height:size.y+'px',maxWidth:'none',position:'absolute',left:0,top:0,transformOrigin:'0 0',transform:`matrix(${a[0][0]},${-a[1][0]},${-a[0][1]},${a[1][1]},0,0)`,pointerEvents:'none'})
   img.onload=()=>done(null,tile);img.onerror=()=>{img.onload=null;img.onerror=null;img.src=this.options.errorTileUrl;done(null,tile)}
   tile.appendChild(img);img.src=this.getTileUrl(c);return tile
  }
 })
 return new Tiles(url,options)
}

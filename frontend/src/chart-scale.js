// Round axis scales for the inline SVG charts (spec 004, FR-035): 0 … a "nice" top with 3–5 steps of 1, 2, 2.5 or 5 × 10ⁿ.
export function niceScale(max,ticks=4){
 const top=Number(max)
 if(!(top>0))return {max:1,step:1,ticks:[0,1]}
 const raw=top/ticks,mag=10**Math.floor(Math.log10(raw)),norm=raw/mag
 const step=(norm<=1?1:norm<=2?2:norm<=2.5?2.5:norm<=5?5:10)*mag
 const end=Math.ceil(top/step-1e-9)*step
 const list=[]
 for(let v=0;v<=end+step/2;v+=step)list.push(Number(v.toPrecision(12)))
 return {max:end,step,ticks:list}
}

// Lines through the points that exist; a missing value breaks the line instead of drawing a fake 0.
export function linePath(points){
 let d='',pen=false
 for(const p of points){
  if(!p){pen=false;continue}
  d+=(pen?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)
  pen=true
 }
 return d
}

// A closed band between low and high, for each run of weeks that has both.
export function bandPath(highs,lows){
 const runs=[];let run=[]
 highs.forEach((h,i)=>{if(h&&lows[i])run.push([h,lows[i]]);else if(run.length){runs.push(run);run=[]}})
 if(run.length)runs.push(run)
 return runs.filter(r=>r.length>1).map(r=>'M'+r.map(([h])=>h[0].toFixed(1)+' '+h[1].toFixed(1)).join('L')+'L'+[...r].reverse().map(([,l])=>l[0].toFixed(1)+' '+l[1].toFixed(1)).join('L')+'Z').join('')
}

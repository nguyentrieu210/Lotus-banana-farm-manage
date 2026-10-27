// Minimal Markdown for AI answers: everything is HTML-escaped first, then tables, headings, lists, **bold** and `code`.
const escape=text=>String(text??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
const inline=text=>escape(text).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/(^|[^*])\*([^*\n]+)\*/g,'$1<em>$2</em>')
const cells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim())
export function renderMarkdown(source){
 // Quote markers ('> ') are dropped: the text renders as a normal paragraph.
 const lines=String(source??'').replace(/\r\n/g,'\n').split('\n').map(l=>l.replace(/^\s*>\s?/,'')),out=[]
 let i=0
 while(i<lines.length){
  const line=lines[i]
  if(/^\s*\|.*\|\s*$/.test(line)&&/^\s*\|?\s*:?-{2,}/.test(lines[i+1]||'')){
   const head=cells(line);i+=2;const body=[]
   while(i<lines.length&&/^\s*\|.*\|\s*$/.test(lines[i])){body.push(cells(lines[i]));i++}
   const numeric=v=>/^-?[\d.,]+(\s*(đ|₫|kg|%))?$/.test(v)
   out.push('<div class="ai-md-table"><table><thead><tr>'+head.map(h=>'<th>'+inline(h)+'</th>').join('')+'</tr></thead><tbody>'+body.map(r=>'<tr>'+r.map(c=>'<td'+(numeric(c)?' class="num"':'')+'>'+inline(c)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>')
   continue
  }
  const heading=line.match(/^\s*(#{1,4})\s+(.*)$/)
  if(heading){out.push('<p class="ai-md-heading">'+inline(heading[2])+'</p>');i++;continue}
  if(/^\s*([-*•]|\d+[.)])\s+/.test(line)){
   const ordered=/^\s*\d+[.)]/.test(line),items=[]
   while(i<lines.length&&/^\s*([-*•]|\d+[.)])\s+/.test(lines[i])){items.push(lines[i].replace(/^\s*([-*•]|\d+[.)])\s+/,''));i++}
   out.push((ordered?'<ol>':'<ul>')+items.map(t=>'<li>'+inline(t)+'</li>').join('')+(ordered?'</ol>':'</ul>'))
   continue
  }
  if(!line.trim()){i++;continue}
  const para=[]
  while(i<lines.length&&lines[i].trim()){
   if(para.length&&(/^\s*([-*•]|\d+[.)]|#{1,4})\s+/.test(lines[i])||(/^\s*\|.*\|\s*$/.test(lines[i])&&/^\s*\|?\s*:?-{2,}/.test(lines[i+1]||''))))break
   para.push(inline(lines[i]));i++
  }
  out.push('<p>'+para.join('<br>')+'</p>')
 }
 return out.join('')
}

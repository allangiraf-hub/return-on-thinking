function spark(points, w, h, label, key){
 key=key||'value';
 if(!points||!points.length) return '<em style="color:#9a9a9a;font-size:12px">no data yet</em>';
 const ys=points.map(p=>+p[key]), min=Math.min(...ys), max=Math.max(...ys), pad=(max-min)||1;
 const X=i=>8+(w-16)*i/Math.max(points.length-1,1), Y=v=>h-16-(h-28)*((v-min)/pad);
 let d='';points.forEach((p,i)=>d+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(+p[key]).toFixed(1)+' ');
 const last=points[points.length-1];
 return '<svg viewBox="0 0 '+w+' '+h+'" width="100%"><path d="'+d+'" fill="none" stroke="#2e5e8c" stroke-width="2"/>'
  +'<text x="8" y="'+(h-2)+'" font-size="10" fill="#9a9a9a">'+points[0].date+'</text>'
  +'<text x="'+(w-8)+'" y="'+(h-2)+'" font-size="10" fill="#9a9a9a" text-anchor="end">'+last.date+'</text>'
  +'<text x="'+(w-8)+'" y="13" font-size="11" fill="#333" text-anchor="end">'+label+': '+(+last[key]).toLocaleString()+'</text></svg>';
}

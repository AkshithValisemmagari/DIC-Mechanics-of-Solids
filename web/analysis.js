/* Measurement profiles use real candidate rows/columns; no spatial interpolation. */
window.LabAnalysis=(()=>{
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const nice=v=>!finite(v)?'—':v!==0&&(Math.abs(v)<.001||Math.abs(v)>=1e5)?v.toExponential(2):Number(v.toPrecision(4)).toString();
  function lines(data,axis){const k=axis==='horizontal'?1:0;return [...new Set(data.dic.map(d=>d[k]))].sort((a,b)=>a-b);}
  function crossesHole(data,a,b){const r=data.config.hole_radius_m;if(!r)return false;const x=data.x_m[a],y=data.y_m[a],dx=data.x_m[b]-x,dy=data.y_m[b]-y,t=Math.max(0,Math.min(1,-(x*dx+y*dy)/(dx*dx+dy*dy||1)));return Math.hypot(x+t*dx,y+t*dy)<r;}
  function stats(truth,measured){const errors=truth.map((v,i)=>finite(v)&&finite(measured[i])?measured[i]-v:null).filter(finite);return{n:errors.length,rmse:errors.length?Math.sqrt(errors.reduce((s,e)=>s+e*e,0)/errors.length):null,max:errors.length?Math.max(...errors.map(Math.abs)):null};}
  function profile(data,key,axis,index){
    const available=lines(data,axis),k=axis==='horizontal'?1:0,position=available[Math.max(0,Math.min(available.length-1,index))];
    const ids=data.dic.map((d,i)=>d[k]===position?i:-1).filter(i=>i>=0).sort((a,b)=>(axis==='horizontal'?data.x_m[a]-data.x_m[b]:data.y_m[a]-data.y_m[b]));
    const f=data.fields[key],base=data.baseline,truth=[],measured=[],baseline=[],x=[],rows=[];
    function gap(){x.push(null);truth.push(null);measured.push(null);baseline.push(null);}
    ids.forEach((i,j)=>{if(j&&crossesHole(data,ids[j-1],i))gap();x.push((axis==='horizontal'?data.x_m[i]:data.y_m[i])*1000);truth.push(f.truth[i]);const n=data.dic[i][9]&&finite(f.measured[i])?f.measured[i]:null;const b=base&&base.dic[i][9]&&finite(base.fields[key].measured[i])?base.fields[key].measured[i]:null;measured.push(n);baseline.push(b);rows.push([data.x_m[i]*1000,data.y_m[i]*1000,f.truth[i],n,b]);});
    // In a pair, quantify both errors on the same centres, not survivor-biased sets.
    const commonTruth=truth.map((t,i)=>!base||finite(measured[i])&&finite(baseline[i])?t:null);
    return{x,truth,measured,baseline,rows,position_mm:ids.length?(axis==='horizontal'?data.y_m[ids[0]]:data.x_m[ids[0]])*1000:null,stats:stats(commonTruth,measured),baseStats:stats(commonTruth,baseline),unit:f.unit,label:f.label};
  }
  function chart(ctx,w,h,x,series,{xlabel='',ylabel='',zero=false}={}){
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
    const points=[];series.forEach(s=>s.values.forEach((v,i)=>{if(finite(v)&&finite(x[i]))points.push([x[i],v]);}));
    if(!points.length){ctx.fillStyle='#6f8381';ctx.font='13px system-ui';ctx.fillText('No valid estimates on this line. Choose another line.',25,h/2);return;}
    let xmin=Math.min(...points.map(p=>p[0])),xmax=Math.max(...points.map(p=>p[0])),ymin=Math.min(...points.map(p=>p[1])),ymax=Math.max(...points.map(p=>p[1]));
    if(zero){ymin=Math.min(0,ymin);ymax=Math.max(0,ymax);}if(xmax===xmin){xmin-=.5;xmax+=.5;}let pad=(ymax-ymin)*.1;if(pad<1e-12)pad=Math.max(1e-6,Math.abs(ymin)*.05);ymin-=pad;ymax+=pad;
    const left=76,right=22,top=35,bottom=54,p=(x,y)=>[left+(x-xmin)/(xmax-xmin)*(w-left-right),h-bottom-(y-ymin)/(ymax-ymin)*(h-top-bottom)];
    ctx.font='10px system-ui';ctx.lineWidth=1;
    for(let j=0;j<=4;j++){const y=ymin+(ymax-ymin)*j/4,py=p(xmin,y)[1];ctx.strokeStyle='#e4ece7';ctx.beginPath();ctx.moveTo(left,py);ctx.lineTo(w-right,py);ctx.stroke();ctx.fillStyle='#6f8381';ctx.textAlign='right';ctx.fillText(nice(y),left-9,py+3);const xx=xmin+(xmax-xmin)*j/4;ctx.textAlign='center';ctx.fillText(nice(xx),p(xx,ymin)[0],h-bottom+18);}
    ctx.fillStyle='#43645c';ctx.fillText(xlabel,(left+w-right)/2,h-12);ctx.save();ctx.translate(14,h/2);ctx.rotate(-Math.PI/2);ctx.fillText(ylabel,0,0);ctx.restore();ctx.textAlign='left';
    for(const s of series){ctx.strokeStyle=s.color;ctx.fillStyle=s.color;ctx.lineWidth=s.dashed?2:1.7;ctx.setLineDash(s.dashed?[6,4]:[]);ctx.beginPath();let pen=false;s.values.forEach((v,i)=>{if(!finite(v)||!finite(x[i])){pen=false;return;}const q=p(x[i],v);if(pen)ctx.lineTo(...q);else ctx.moveTo(...q);pen=true;});ctx.stroke();ctx.setLineDash([]);if(s.dots)s.values.forEach((v,i)=>{if(finite(v)&&finite(x[i])){const q=p(x[i],v);ctx.beginPath();ctx.arc(...q,2.8,0,2*Math.PI);ctx.fill();}});}
  }
  function csv(profile,paired){const header=['x_mm','y_mm','ground_truth_'+profile.unit,'dic_'+profile.unit];if(paired)header.push('baseline_dic_'+profile.unit);return header.join(',')+'\n'+profile.rows.map(r=>r.slice(0,paired?5:4).map(v=>finite(v)?v:'').join(',')).join('\n')+'\n';}
  return{finite,nice,lines,profile,stats,chart,csv,crossesHole};
})();

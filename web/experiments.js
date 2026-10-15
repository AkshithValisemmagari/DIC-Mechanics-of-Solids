/* UI for real measurement profiles, paired noise, and analytical shaft plots. */
window.LabExperiments=(()=>{
  let api,lastRun=null,profileData=null;const A=window.LabAnalysis;
  const $=id=>api.$(id),result=()=>api.getResult(),cv=id=>api.canvas(id),fmt=(v,n=3)=>api.fmt(v,n);
  function controls(name){
    const square=name==='square_torsion',shaft=name==='torsion'||square,bending=name==='pure_bending';
    for(const [id,hidden]of[['heightLabel',shaft],['thicknessLabel',shaft],['forceControl',shaft||bending],['radiusControl',!shaft||square],['sideControl',!square],['torqueControl',!shaft],['momentControl',!bending],['cameraControls',shaft&&!square],['torsionOnlyNote',!shaft||square],['holeControl',name!=='plate_with_hole']])$(id).hidden=hidden;
    for(const id of ['height_mm','thickness_mm','force_n','radius_mm','side_mm','torque_nm','moment_nm','hole_radius_mm'])$(id).disabled=$(id).closest('label').hidden;
    $('cameraControls').querySelectorAll('input,select').forEach(el=>el.disabled=shaft&&!square);
    $('compare_noise').disabled=shaft;
    $('compare_noise').closest('label').hidden=square;
    $('compare_noise').closest('label').nextElementSibling.hidden=square;
    $('loadHint').textContent=square?'Equal and opposite end torques · θ(L/2) = 0':shaft?'Torque about the shaft axis · θ(0) = 0':bending?'Equal and opposite end moments · change the sign to reverse bending':name==='cantilever'?'Upward end force · beam bending + shear':name==='plate_with_hole'?'Equivalent nominal load · remote stress = F / (width × thickness)':'Axial tension · stress = force / gross area';
  }
  function configure(data){
    const shaft=!!data.analysis_only||!!data.stereo;
    document.querySelectorAll('[data-tab]').forEach(b=>{b.hidden=shaft?['images','fields','noise'].includes(b.dataset.tab):b.dataset.tab==='torsion';});
    document.querySelector('[data-tab="stereo"]').hidden=!data.stereo;
    document.querySelector('[data-tab="torsion"]').hidden=!data.analysis_only;
    if(document.querySelector('[data-tab].active')?.hidden)document.querySelector('[data-tab="model"]').click();
    $('dicMethods').hidden=shaft;
    $('methodIntro').textContent=shaft?'This experiment evaluates analytical shaft mechanics; no DIC is performed.':'The images are the only motion information passed to DIC.';
    $('modelCaption').textContent=shaft?'Cross-sections rotate by θ(x) = Tx/(GJ). The marker lines make twist visible. Magnification exaggerates angle only; stress colours and reported values use the actual load.':'3D display of the 2D plane-stress solution, extruded through the entered thickness. Playback and magnification change only the view; DIC results stay unchanged.';
    const option=$('stressView').querySelector('[value="tau"]');option.textContent=shaft?'Shaft shear magnitude |τxθ|':'Shear stress magnitude |τxy|';
    for(const o of $('stressView').options)o.hidden=o.disabled=shaft&&!['von_mises','tau','plain'].includes(o.value);
    if($('stressView').selectedOptions[0]?.disabled)$('stressView').value='von_mises';
    const labels=shaft?['END TWIST','MAX SHEAR STRESS','MAX VON MISES','EXPERIMENT TIME']:['DISPLACEMENT RMSE','VALID DIC SUBSETS','MAX TRUE MOTION','EXPERIMENT TIME'];
    const hints=shaft?['Analytical · degrees','Analytical · MPa','Analytical · MPa','Analytical model and report']:['Measured vs analytical · pixels','Accepted / candidate centres','On candidate centres · pixels','Images → fields → validation'];
    document.querySelectorAll('.metrics>div').forEach((el,i)=>{el.querySelector('label').textContent=labels[i];el.querySelector('small').textContent=hints[i];});
    if(lastRun!==data.run_id){lastRun=data.run_id;$('profileLine').dataset.initial='1';}
    if(!shaft&&data.baseline){$('noiseLevel').textContent=`σ = ${data.config.camera.noise_std.toFixed(3)}`;noiseImages();}
  }
  function profile(){
    const d=result();if(!d||d.analysis_only||d.stereo)return;
    const axis=$('profileAxis').value,available=A.lines(d,axis),slider=$('profileLine');slider.max=available.length-1;
    if(slider.dataset.initial==='1'){slider.value=Math.floor((available.length-1)/2);slider.dataset.initial='0';}
    profileData=A.profile(d,$('field').value,axis,+slider.value);
    $('profilePosition').textContent=`${axis==='horizontal'?'y':'x'} = ${fmt(profileData.position_mm)} mm · line ${+slider.value+1} / ${available.length}`;
    const series=[{values:profileData.truth,color:'#183f43',dashed:true},{values:profileData.measured,color:'#d57245',dots:true}];
    if(d.baseline)series.push({values:profileData.baseline,color:'#087f85',dots:true});
    $('baselineKey').hidden=!d.baseline;
    const {c,w,h}=cv('profileCanvas');A.chart(c,w,h,profileData.x,series,{xlabel:`${axis==='horizontal'?'x':'y'} (mm)`,ylabel:`${profileData.label} (${profileData.unit})`});
    const s=profileData.stats,b=profileData.baseStats;$('profileStats').textContent=`${d.baseline?'Common valid':'Valid'} points: ${s.n}. ${d.baseline?'Selected noise':'DIC'} — RMSE ${fmt(s.rmse,5)}, max |error| ${fmt(s.max,5)} ${profileData.unit}.`+(d.baseline?` Baseline — RMSE ${fmt(b.rmse,5)}, max |error| ${fmt(b.max,5)} ${profileData.unit}.`:'');
    $('profileDownload').disabled=!profileData.rows.length;
    const map=cv('profileMap'),bounds=d.bounds,p=api.pointTransform(map.w,map.h,bounds,25),a=p(bounds[0],bounds[2]),z=p(bounds[1],bounds[3]);
    map.c.fillStyle='#e2eee6';map.c.fillRect(a[0],z[1],z[0]-a[0],a[1]-z[1]);map.c.strokeStyle='#86a997';map.c.strokeRect(a[0],z[1],z[0]-a[0],a[1]-z[1]);
    map.c.strokeStyle='#d57245';map.c.lineWidth=2;const q=profileData.position_mm/1000;const endpoints=axis==='horizontal'?[p(bounds[0],q),p(bounds[1],q)]:[p(q,bounds[2]),p(q,bounds[3])];map.c.beginPath();map.c.moveTo(...endpoints[0]);map.c.lineTo(...endpoints[1]);map.c.stroke();
    if(d.config.hole_radius_m){const centre=p(0,0),r=d.config.hole_radius_m*(z[0]-a[0])/(bounds[1]-bounds[0]);map.c.fillStyle='#f6f9f5';map.c.beginPath();map.c.arc(...centre,r,0,2*Math.PI);map.c.fill();map.c.strokeStyle='#86a997';map.c.stroke();}
    map.c.font='10px system-ui';map.c.fillStyle='#536d61';map.c.fillText('Reference geometry',10,15);
  }
  function noiseImages(){const d=result();if(!d?.baseline)return;const name=$('noiseImage').value;$('baselineImage').src=d.baseline.asset_prefix+name;$('noisyImage').src=d.asset_prefix+name;}
  function noise(){
    const d=result(),paired=d&&!d.analysis_only&&d.baseline;$('noiseEmpty').hidden=!!paired;$('noiseResults').hidden=!paired;if(!paired)return;
    const key=$('noiseField').value,stats=d.noise_comparison[key],sets=[d.baseline,d],values=[];
    for(const s of sets)s.fields[key].measured.forEach((v,i)=>{if(s.dic[i][9]&&A.finite(v))values.push(v);});
    let lo=values.length?Math.min(...values):0,hi=values.length?Math.max(...values):1;if(hi===lo){const pad=Math.max(1e-6,Math.abs(lo)*.05);lo-=pad;hi+=pad;}
    for(const [k,s]of sets.entries()){const {c,w,h}=cv(k?'noisyNoiseField':'baselineNoiseField'),p=api.pointTransform(w,h,s.bounds,35),a=p(s.bounds[0],s.bounds[2]),b=p(s.bounds[1],s.bounds[3]);c.strokeStyle='#d1e1d7';c.strokeRect(a[0],b[1],b[0]-a[0],a[1]-b[1]);let count=0;s.fields[key].measured.forEach((v,i)=>{if(!s.dic[i][9]||!A.finite(v))return;count++;c.fillStyle=api.color((v-lo)/(hi-lo));c.beginPath();c.arc(...p(s.x_m[i],s.y_m[i]),3,0,2*Math.PI);c.fill();});c.font='11px system-ui';c.fillStyle='#6f8381';c.fillText(`${count} valid recovered values`,18,h-12);}
    $('noiseLegend').innerHTML=`<span>${fmt(lo)}</span><span>Shared recovered-field scale · ${stats.unit}</span><span>${fmt(hi)}</span><div class="gradient"></div>`;
    const total=d.dic.length;$('noiseStats').innerHTML=`<table><thead><tr><th>${stats.label}</th><th>No added noise</th><th>Selected noise</th></tr></thead><tbody><tr><td>Valid field points / candidates</td><td>${stats.baseline_valid} / ${total}</td><td>${stats.noisy_valid} / ${total}</td></tr><tr><td>Common points used for both errors</td><td>${stats.common_count}</td><td>${stats.common_count}</td></tr><tr><td>RMSE (${stats.unit})</td><td>${fmt(stats.baseline.rmse,5)}</td><td>${fmt(stats.noisy.rmse,5)}</td></tr><tr><td>Maximum |error| (${stats.unit})</td><td>${fmt(stats.baseline.max_abs,5)}</td><td>${fmt(stats.noisy.max_abs,5)}</td></tr></tbody></table>`;
  }
  function torsion(){
    const d=result();if(!d?.analysis_only)return;const t=d.torsion;
    for(const [id,x,y,xlabel,ylabel,color]of[['twistCanvas',t.x_m.map(v=>v*1000),t.twist_deg,'Axial position x (mm)','Twist (degrees)','#086c58'],['radialCanvas',t.r_m.map(v=>v*1000),t.shear_mpa,'Radius r (mm)','Signed shear stress (MPa)','#d57245']]){const {c,w,h}=cv(id);A.chart(c,w,h,x,[{values:y,color}],{xlabel,ylabel,zero:true});}
    const {c,w,h}=cv('sectionCanvas'),R=Math.min(w*.32,h*.38),ox=w/2,oy=h/2;
    for(let i=80;i>=1;i--){c.fillStyle=`rgb(${Specimen3D.stressColor(t.max_shear_pa*i/80,t.max_shear_pa).join(',')})`;c.beginPath();c.arc(ox,oy,R*i/80,0,2*Math.PI);c.fill();}
    c.fillStyle='#143e3b';c.font='12px system-ui';c.textAlign='center';c.fillText('0 MPa',ox,oy+4);c.fillText(`${fmt(t.max_shear_pa/1e6)} MPa at r = ${fmt(d.config.radius_m*1000)} mm`,ox,h-14);c.textAlign='left';
    $('torsionEquations').textContent=`G = E / [2(1 + ν)] = ${fmt(t.shear_modulus_pa/1e9)} GPa · J = πR⁴/2 = ${fmt(t.polar_moment_m4)} m⁴. θ(x) = Tx/(GJ); τ(r) = Tr/J; σVM = √3|τ|. Positive torque rotates y toward z about +x. These plots show the actual full torque; playback affects only the 3D view. Uniform surface stress does not mean uniform stress through the cross-section.`;
  }
  function init(dependencies){api=dependencies;$('noiseField').innerHTML=$('field').innerHTML;
    $('profileAxis').addEventListener('change',()=>{$('profileLine').dataset.initial='1';profile();});$('profileLine').addEventListener('input',profile);$('noiseField').addEventListener('change',noise);$('noiseImage').addEventListener('change',noiseImages);
    $('profileDownload').addEventListener('click',()=>{if(!profileData)return;const blob=new Blob([A.csv(profileData,!!result().baseline)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`${result().run_id}-${$('field').value}-${$('profileAxis').value}-line.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    controls('axial_bar');
  }
  return{init,controls,configure,render(){profile();noise();torsion();}};
})();

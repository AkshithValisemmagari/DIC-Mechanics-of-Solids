/* Square torsion measurements. All displayed DIC values come from image matches. */
window.StereoLab=(()=>{
  let api,previews,renderPending=false;const keys=['left_reference','right_reference','left_deformed','right_deformed'];
  const $=id=>api.$(id),cv=id=>api.canvas(id),fmt=(v,n=4)=>api.fmt(v,n),finite=Number.isFinite;
  function init(dependencies){
    api=dependencies;
    previews=StereoPreviews.create(()=>{
      if(renderPending)return;
      renderPending=true;requestAnimationFrame(()=>{renderPending=false;render();});
    });
    for(const id of ['stereoField','stereoRow','stereoImageMode','stereoPoints'])$(id).addEventListener('change',render);
    for(const key of keys)$('stereoRetry_'+key).addEventListener('click',()=>{
      previews.retry(key+($('stereoImageMode').value==='smoothed'?'_smoothed':''));
    });
  }
  function display(d){
    const c=d.config,s=d.summary;
    $('play').textContent='▶ Play';$('empty').hidden=true;$('state').className='state';$('state').textContent='Experiment complete';
    $('sceneTitle').textContent='Square beam · free warping';
    $('runCaption').textContent=`Square torsion · ${c.load_description.material_name} · ${fmt(c.torque_nm)} N·m · ${fmt(c.length_m*1000)} mm × ${fmt(c.side_m*1000)} mm square`;
    const labels=['3D DISPLACEMENT RMSE','MATCHED POINTS','MAX TRUE MOTION','EXPERIMENT TIME'];
    const hints=['Vector error · mm','Accepted / candidate centres','On candidate centres · mm','Four images → 3D → validation'];
    document.querySelectorAll('.metrics>div').forEach((el,i)=>{el.querySelector('label').textContent=labels[i];el.querySelector('small').textContent=hints[i];});
    $('metricError').textContent=fmt(s.displacement_vector_rmse_mm,5);api.showCoverage(s,true);
    $('metricMotion').textContent=fmt(s.max_true_displacement_mm,4);$('metricTime').textContent=fmt(d.elapsed_s,1)+' s';
    for(const id of ['play','phase','mag'])$(id).disabled=false;$('phase').value=1;$('phaseOut').textContent='100%';
    $('modelCaption').textContent='Square-section torsion with axial warping. Visual magnification exaggerates twist and warping only; camera images and measurements use the actual load. The middle section has zero rotation; both ends rotate equally in opposite directions. Axial warping is free.';
    $('stressView').querySelector('[value="tau"]').textContent='Shear stress magnitude √(τxy² + τxz²)';
    $('methodIntro').textContent='Stereo DIC receives only four images, support masks, camera calibration and correlation settings.';
    $('methodDetails').textContent='Square Saint-Venant torsion → inverse pinhole rendering with cubic interpolation → independent affine ZNCC matching across cameras and time → cycle, epipolar, reprojection and neighbour checks → 3D triangulation → local quadratic surface fitting → Green–Lagrange surface strain. Ground truth is used only after reconstruction for validation. Interior stress is analytical; no measured bulk stress is inferred from one face.';
    $('methodDetails').textContent+=(s.preprocessing?.kernel_radius_px?` ${api.denoiseLabel(s.preprocessing)} is applied after capture and before all matching; original images are preserved.`:' DIC denoising is off.');
    $('warnings').replaceChildren(...c.warnings.map(text=>{const p=document.createElement('p');p.textContent=text;return p;}));
    $('raw').textContent=JSON.stringify({config:c,summary:s,calibration:d.calibration},null,2);
    $('download').href=d.asset_prefix+'download.zip';$('report').href=d.asset_prefix+'report.html';
    $('download').classList.remove('disabled');$('report').classList.remove('disabled');
    const smoothed=!!s.preprocessing?.kernel_radius_px;
    $('stereoImageMode').querySelector('[value="smoothed"]').disabled=!smoothed;
    if(previews.setRun(d.run_id,d.asset_prefix)){
      $('stereoImageMode').value=smoothed?'smoothed':'original';
      const rows=[...new Set(d.y_m)].sort((a,b)=>a-b);
      $('stereoRow').replaceChildren(...rows.map(y=>{const o=document.createElement('option');o.value=y;o.textContent=`y = ${fmt(y*1000,2)} mm`;return o;}));
      $('stereoRow').selectedIndex=Math.floor(rows.length/2);
    }
  }
  function render(){
    const d=api?.getResult();if(!d?.stereo)return;
    const r=d.stereo_result,f=d.fields[$('stereoField').value],n=r.valid.length;
    const sigma=d.summary.preprocessing?.kernel_radius_px||0,smoothed=sigma>0&&$('stereoImageMode').value==='smoothed';
    $('stereoPreprocessing').textContent=sigma>0
      ?`DIC used ${api.denoiseLabel(d.summary.preprocessing)} on all four images. Showing ${smoothed?'smoothed DIC inputs':'original camera images'}. Switching this preview does not change the measurements. Filtering excludes boundary-affected support; exact floating-point inputs are in the run download.`
      :'DIC denoising: Off. These original camera images were used for matching. Select a filter in DIC & imaging settings and run again to see smoothed inputs.';
    previews.select(smoothed);
    for(const [k,key] of keys.entries()){
      const state=previews.get(key+(smoothed?'_smoothed':'')),im=state.image;
      const status=$('stereoStatus_'+key),retry=$('stereoRetry_'+key);
      status.hidden=state.status==='loaded';retry.hidden=state.status!=='error';
      $('stereoStatusText_'+key).textContent=state.status==='error'
        ?'Image could not load after 3 attempts. Measurement results are still available.'
        :state.status==='retrying'?'Image request failed. Retrying…'
        :state.status==='loading'&&state.attempts>1?`Retrying image (${state.attempts} / 3)…`:'Loading image…';
      const {c,w,h}=cv('stereo_'+key);c.fillStyle='#eff2ee';c.fillRect(0,0,w,h);if(!im||w<=16||h<=16)continue;
      const scale=Math.min((w-16)/im.width,(h-16)/im.height),x=(w-im.width*scale)/2,y=(h-im.height*scale)/2;
      c.drawImage(im,x,y,im.width*scale,im.height*scale);
      // Payload coordinate order is L0,R0,L1,R1.
      if($('stereoPoints').checked)r.coordinates_px.forEach((points,i)=>{if(k&&!r.valid[i])return;const p=points[k];if(!p.every(finite))return;c.fillStyle=r.valid[i]?'#20bd8e':'#888';c.beginPath();c.arc(x+p[0]*scale,y+p[1]*scale,2,0,Math.PI*2);c.fill();});
    }
    const valid=f.measured.map((v,i)=>r.valid[i]&&finite(v)&&finite(f.truth[i]));
    const vals=f.truth.flatMap((v,i)=>valid[i]?[v,f.measured[i]]:[]);
    let lo=vals.length?Math.min(...vals):0,hi=vals.length?Math.max(...vals):1;
    if(hi-lo<1e-10){const pad=Math.max(1e-6,Math.abs(lo)*.05);lo-=pad;hi+=pad;}
    const error=f.measured.map((v,i)=>valid[i]?v-f.truth[i]:null),emax=Math.max(1e-9,...error.filter(finite).map(Math.abs));
    for(const id of ['stereoTruth','stereoMeasured','stereoError']){const el=$(id),width=el.getBoundingClientRect().width;if(width>60)el.style.height=Math.min(260,Math.max(130,(width-60)*(d.bounds[3]-d.bounds[2])/(d.bounds[1]-d.bounds[0])+60))+'px';}
    for(const [key,values,isError] of [['Truth',f.truth,false],['Measured',f.measured,false],['Error',error,true]]){
      const {c,w,h}=cv('stereo'+key),p=api.pointTransform(w,h,d.bounds,30),a=p(d.bounds[0],d.bounds[2]),b=p(d.bounds[1],d.bounds[3]);
      c.strokeStyle='#ccdcd2';c.strokeRect(a[0],b[1],b[0]-a[0],a[1]-b[1]);
      for(let i=0;i<n;i++){const q=p(d.x_m[i],d.y_m[i]);c.fillStyle=valid[i]?api.color(isError?(values[i]+emax)/(2*emax):(values[i]-lo)/(hi-lo),isError):'#cbd1cc';c.beginPath();c.arc(...q,valid[i]?3:1.5,0,Math.PI*2);c.fill();}
      c.fillStyle='#607a70';c.font='10px system-ui';c.fillText('Reference face · x →',20,h-10);
      if(!valid.some(Boolean))c.fillText('No valid field estimates',30,h/2-15);
      $('stereo'+key+'Legend').innerHTML=isError&&LabPresentation.zeroError(error)?`<span class="zero-error">Error: 0 ${f.unit} · all valid points</span><div class="gradient zero"></div>`:`<span>${fmt(isError?-emax:lo)}</span><span>${f.unit}</span><span>${fmt(isError?emax:hi)}</span><div class="gradient ${isError?'error':''}"></div>`;
    }
    const s=f.statistics;$('stereoStats').textContent=`${f.label}: ${s.n_valid} valid values / ${n} candidates · RMSE ${fmt(s.rmse,5)} ${f.unit} · max |error| ${fmt(s.max_abs,5)} ${f.unit}. Grey marks indicate unavailable estimates. Magnitude RMSE differs from the vector RMSE in the top card.`;
    const row=+$('stereoRow').value,ids=d.y_m.map((y,i)=>Math.abs(y-row)<1e-10?i:-1).filter(i=>i>=0).sort((a,b)=>d.x_m[a]-d.x_m[b]);
    const chart=cv('stereoProfile');LabAnalysis.chart(chart.c,chart.w,chart.h,ids.map(i=>d.x_m[i]*1000),[
      {values:ids.map(i=>f.truth[i]),color:'#183f43',dashed:true},{values:ids.map(i=>valid[i]?f.measured[i]:null),color:'#d57245',dots:true}
    ],{xlabel:'Reference x (mm)',ylabel:`${f.label} (${f.unit})`});
    const t=d.torsion,tw=cv('squareTwist');LabAnalysis.chart(tw.c,tw.w,tw.h,t.x_m.map(x=>x*1000),[{values:t.twist_deg,color:'#087f85'}],{xlabel:'Axial position (mm)',ylabel:'Analytical twist (degrees)',zero:true});
    const sc=cv('squareSection'),a=Math.min(sc.w-70,sc.h-65),ox=(sc.w-a)/2,oy=15,grid=t.section_shear_mpa,N=grid.length;
    for(let j=0;j<N;j++)for(let i=0;i<N;i++){sc.c.fillStyle=`rgb(${Specimen3D.stressColor(grid[j][i],t.max_shear_pa/1e6).join(',')})`;sc.c.fillRect(ox+i*a/N,oy+(N-1-j)*a/N,a/N+1,a/N+1);}
    sc.c.fillStyle='#3a5b51';sc.c.font='11px system-ui';sc.c.fillText(`0 → ${fmt(t.max_shear_pa/1e6)} MPa · y →, z ↑`,ox,oy+a+20);
    const q=d.summary;$('stereoQuality').textContent=`Coverage: ${q.valid_displacement_subsets}/${n} displacement, ${q.valid_strain_subsets}/${n} surface strain. Status counts: ${Object.entries(q.status_counts).map(([k,v])=>`${k.replaceAll('_',' ')}: ${v}`).join(' · ')}. Limits: minimum ZNCC 0.85; cycle 0.30 px; epipolar 0.25 px; reprojection 0.20 px. Passing checks does not guarantee an exact measurement. Full correspondences and rejected-point diagnostics are included in Download this run.`;
  }
  return{init,display,render};
})();

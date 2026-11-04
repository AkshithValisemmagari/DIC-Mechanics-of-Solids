/* Results presentation only: no measurement, validation or acceptance decisions. */
(function(root){
 'use strict';
 const finite=Number.isFinite;
 const names={axial_bar:'Axial bar',cantilever:'Cantilever',plate_with_hole:'Plate with a hole',pure_bending:'Pure bending',square_torsion:'Square torsion',torsion:'Circular torsion'};
 const statuses={'1':'Excluded by the reference mask','2':'Insufficient reference texture','3':'Forward fit did not converge','4':'Forward correlation below the limit','5':'Target support unavailable','6':'Search or deformation limit reached','7':'Reverse match failed','8':'Return-position mismatch',cycle:'Stereo route mismatch',epipolar:'Camera-pair alignment check failed',reprojection:'Camera reprojection check failed',triangulation:'3D reconstruction failed',neighbour_inconsistent:'Neighbouring image motions disagree'};
 function format(value){
  if(!finite(value))return '—';
  if(value!==0&&Math.abs(value)<.001)return value.toExponential(2);
  return value.toLocaleString('en-US',{maximumFractionDigits:Math.abs(value)>=1000?0:3});
 }
 function rejectionLabel(key){
  if(statuses[key])return statuses[key];
  const prefixes=[['right_temporal_','Right temporal match'],['reference_','Reference stereo match'],['temporal_','Left temporal match'],['right_','Right deformed match'],['cross_','Deformed stereo match'],['reverse_','Reverse temporal match']];
  const reasons={source_support:'source patch outside valid support',target_support:'target support unavailable',search_support:'search outside image support',low_texture:'insufficient texture',optimizer:'fit did not converge',low_correlation:'low correlation',parameter_bound:'search or deformation limit reached'};
  for(const [prefix,label]of prefixes)if(key.startsWith(prefix))return label+': '+(reasons[key.slice(prefix.length)]||key.slice(prefix.length).replaceAll('_',' '));
  return 'Other rejection ('+key.replaceAll('_',' ')+')';
 }
 function row(key,label,unit,stats,scale=1){
  return {key,label,unit,rmse:finite(stats?.vector_rmse)?stats.vector_rmse*scale:null,max:finite(stats?.max_vector_error)?stats.max_vector_error*scale:null,n:finite(stats?.n_valid)?stats.n_valid:null};
 }
 function model(payload){
  const s=payload.summary||{},c=payload.config||{},stereo=!!payload.stereo,analytic=!!payload.analysis_only;
  const settings=[names[c.benchmark||s.benchmark]||'Experiment'];
  if(c.load_description?.material_name)settings.push(c.load_description.material_name);
  if(analytic){
   const t=payload.torsion||{};
   return {analytic:true,title:'Analytical results',settings:settings.join(' · '),counts:[],errors:[
    {key:'twist',label:'End twist',unit:'degrees',value:finite(t.end_twist_rad)?t.end_twist_rad*180/Math.PI:null},
    {key:'shear',label:'Peak shear stress',unit:'MPa',value:finite(t.max_shear_pa)?t.max_shear_pa/1e6:null},
    {key:'von_mises',label:'Peak von Mises stress',unit:'MPa',value:finite(t.max_von_mises_pa)?t.max_von_mises_pa/1e6:null}],components:[],rejections:[],
    note:'Analytical predictions only. No camera-based measurement, recovered stress or RMSE is computed in this mode.',geometry:''};
  }
  const p=s.preprocessing;
  if(p?.method==='gaussian')settings.push('Gaussian denoising σ = '+p.sigma_px+' px');
  else if(p?.method==='wiener')settings.push('Local Wiener denoising · '+(p.window_size_px||5)+' × '+(p.window_size_px||5)+' px');
  else if(p?.method==='off')settings.push('DIC denoising: Off');
  if(s.forward_backward)settings.push(s.forward_backward.tolerance_px==null?'Reverse verification: Off':'Return tolerance = '+s.forward_backward.tolerance_px.toFixed(2)+' px');
  if(stereo)settings.push('Stereo surface measurement');
  const total=s.candidate_subsets,eligible=stereo?total:s.eligible_reference_subsets,accepted=s.valid_displacement_subsets;
  const percent=finite(accepted)&&finite(eligible)&&eligible>0?(100*accepted/eligible).toFixed(1)+'%':'N/A';
  const counts=[{label:'Matched displacement points',value:format(accepted)+' / '+format(eligible),detail:percent+' of eligible locations'}];
  if(stereo)counts.push({label:'Surface-strain points',value:format(s.valid_strain_subsets),detail:'From accepted 3D measurements'});
  else counts.push({label:'Strain estimates',value:format(s.strain?.n_valid),detail:'Points with a valid strain fit'},{label:'Stress estimates',value:format(s.stress_pa?.n_valid),detail:'Points with recovered stress'});
  counts.push({label:'Matching rejections',value:format(finite(eligible)&&finite(accepted)?eligible-accepted:null),detail:'Eligible points that did not pass'});
  const geometry=stereo?'Reference candidates already have full raw reference support. Filtering and matching can reject additional points.':format(total)+' grid candidates · '+format(finite(total)&&finite(eligible)?total-eligible:null)+' excluded by the reference mask before matching.';
  let errors=[],components=[];
  if(stereo){
   errors.push({key:'displacement',label:'3D displacement vector',unit:'mm',rmse:s.displacement_vector_rmse_mm,max:null,n:accepted});
   for(const [key,label]of [['exx','Surface axial strain Eₓₓ'],['eyy','Surface transverse strain Eᵧᵧ'],['gamma','Surface shear 2Eₓᵧ']]){
    const f=payload.fields?.[key];errors.push({key,label,unit:'µε',rmse:f?.statistics?.rmse,max:f?.statistics?.max_abs,n:f?.statistics?.n_valid});
   }
   for(const [key,label]of [['u','Axial displacement u'],['v','Transverse displacement v'],['w','Depth displacement w']]){
    const f=payload.fields?.[key];components.push({key,label,unit:'mm',rmse:f?.statistics?.rmse,max:f?.statistics?.max_abs,n:f?.statistics?.n_valid});
   }
  }else{
   errors=[row('displacement','Displacement vector','px',s.displacement_px),row('strain','Strain components','µε',s.strain,1e6),row('stress','Stress components','MPa',s.stress_pa,1e-6)];
   for(const [stats,labels,unit,scale]of [[s.displacement_px,['Horizontal displacement','Vertical displacement'],'px',1],[s.strain,['Axial strain εxx','Transverse strain εyy','Engineering shear γxy'],'µε',1e6],[s.stress_pa,['Axial stress σxx','Transverse stress σyy','Shear stress τxy'],'MPa',1e-6]]){
    labels.forEach((label,index)=>components.push({label,unit,rmse:finite(stats?.component_rmse?.[index])?stats.component_rmse[index]*scale:null,n:stats?.n_valid}));
   }
  }
  const rejections=Object.entries(s.status_counts||{}).filter(([key,count])=>key!=='0'&&key!=='accepted'&&finite(count)&&count>0).map(([key,count])=>({key,label:rejectionLabel(key),count,excluded:key==='1'}));
  return {analytic:false,stereo,title:'Measured results',settings:settings.join(' · '),counts,geometry,errors,components,rejections,
   note:stereo?'3D displacement RMSE is a vector error; each surface-strain row describes one component. Bulk stress remains analytical, not DIC-recovered. A dash means the metric was not reported.':'Errors use accepted, finite measurement/truth pairs. Displacement combines two components; strain and stress combine three. Combined stress error is not a von Mises stress error.',
   interpretation:'Coverage describes how many points passed checks, not an accuracy percentage. Compare error magnitudes with the analytical field and applied load. Values are rounded for display; Technical details retains the full JSON.'};
 }
 function init(document){
  const $=id=>document.getElementById(id),el=(tag,text)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;return e;};
  const numeric=(value,unit)=>{const cell=el('td',format(value));if(finite(value))cell.title='Exact converted value: '+value+(unit?' '+unit:'');return cell;};
  function table(rows,analytic=false,components=false,stereo=false){
   const wrap=el('div');wrap.className='results-table-wrap';
   const t=el('table');t.className='results-table';const caption=el('caption',analytic?'Analytical predictions':components?'Component error details':'Measurement error compared with ground truth');t.append(caption);
   const head=el('thead'),hrow=el('tr');
   for(const text of analytic?['Quantity','Value']:components?['Component','RMSE','Points']:stereo?['Quantity','RMSE','Largest error','Points']:['Quantity','Combined RMSE','Largest combined error','Points']){const th=el('th',text);th.scope='col';hrow.append(th);}head.append(hrow);t.append(head);
   const body=el('tbody');for(const row of rows){const tr=el('tr');if(row.key)tr.dataset.resultKind=row.key;const th=el('th',row.label);th.scope='row';th.append(el('small',row.unit));tr.append(th);
    if(analytic)tr.append(numeric(row.value,row.unit));else{tr.append(numeric(row.rmse,row.unit));if(!components)tr.append(numeric(row.max,row.unit));tr.append(numeric(row.n));}body.append(tr);
   }t.append(body);wrap.append(t);return wrap;
  }
  $('copyTechnical').addEventListener('click',async()=>{
   const status=$('copyTechnicalStatus');status.textContent='';
   try{await document.defaultView.navigator.clipboard.writeText($('raw').textContent);status.textContent='JSON copied.';}
   catch{status.textContent='Copy unavailable here. Select and copy the JSON below.';}
  });
  return {render(payload){
   const m=model(payload);$('readableResults').hidden=false;$('resultsHeading').textContent=m.title;$('resultsSettings').textContent=m.settings;
   $('resultsCounts').replaceChildren(...m.counts.map(item=>{const card=el('div');card.className='result-count';card.append(el('span',item.label),el('strong',item.value),el('small',item.detail));return card;}));
   $('resultsGeometry').textContent=m.geometry;$('resultsErrors').replaceChildren(table(m.errors,m.analytic,false,m.stereo));
   $('resultsExplanation').textContent=m.note;$('resultsInterpretation').textContent=m.interpretation||'';
   $('componentResults').hidden=!m.components.length;$('componentErrors').replaceChildren(...(m.components.length?[table(m.components,false,true)]:[]));
   $('rejectionResults').hidden=m.analytic;
   const list=el('table');list.className='results-table';list.append(el('caption','Why points were not used'));
   const head=el('thead'),hr=el('tr');for(const label of ['Reason','Points']){const th=el('th',label);th.scope='col';hr.append(th);}head.append(hr);list.append(head);
   const body=el('tbody');if(!m.rejections.length){const tr=el('tr'),td=el('td','No rejections reported.');td.colSpan=2;tr.append(td);body.append(tr);}else for(const item of m.rejections){const tr=el('tr'),th=el('th',item.label+(item.excluded?' (not a matching failure)':''));th.scope='row';tr.append(th,numeric(item.count));body.append(tr);}list.append(body);$('rejectionCounts').replaceChildren(list);
   $('copyTechnical').disabled=false;$('copyTechnicalStatus').textContent='';
  }};
 }
 const api={model,format,init};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LabResults=api;
})(typeof window!=='undefined'?window:this);

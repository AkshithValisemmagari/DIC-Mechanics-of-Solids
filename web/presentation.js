/* Display-only helpers. These never accept, reject or alter measurements. */
(function(root){
 'use strict';
 const reasons={source_support:'The deformed patch crosses unsupported pixels.',target_support:'No supported return patch was found in the reference image.',low_texture:'The deformed patch has insufficient texture.',low_correlation:'The reverse match has low correlation.',optimizer:'The reverse fit did not converge.',parameter_bound:'The reverse fit reached a search or deformation limit.'};
 function reverseDetail(point,tolerance,forwardStatus){
  if(!point)return 'Reverse-check details are unavailable for this saved run. Run the experiment again with the updated server.';
  if(point.reverse_status==='disabled')return 'Reverse verification was disabled for this run.';
  if(point.reverse_status==='not_checked')return 'Reverse check not attempted: the forward match was rejected.';
  const error=point.round_trip_error_px;
  const limit=Number.isFinite(tolerance)?tolerance.toFixed(2)+' px':'unavailable';
  const parts=[];
  if(Number.isFinite(error)){
   const digits=Number.isFinite(tolerance)&&Math.abs(error-tolerance)<.00005?8:4;
   parts.push('Return error: '+error.toFixed(digits)+' px');
  }else parts.push('Return error: unavailable');
  parts.push('Allowed: '+limit);
  if(Number.isFinite(point.reverse_zncc))parts.push('Reverse correlation: '+point.reverse_zncc.toFixed(4));
  if(forwardStatus===0&&point.reverse_status==='matched')parts.push('Return check passed.');
  else if(point.reverse_status==='cycle_error')parts.push('Rejected: the return position is too far from the starting point.');
  else parts.push('Rejected: '+(reasons[point.reverse_status]||'The reverse match did not pass its checks.'));
  return parts.join(' · ');
 }
 function zeroError(values){
  const finite=values.filter(Number.isFinite);
  return finite.length>0&&finite.every(value=>value===0);
 }
 const api={reverseDetail,zeroError};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.LabPresentation=api;
})(typeof window!=='undefined'?window:this);

const assert=require('node:assert/strict');
const P=require('../web/presentation.js');
const pass={round_trip_error_px:.08,reverse_zncc:.98,reverse_status:'matched'};
assert.match(P.reverseDetail(pass,.3,0),/Return error: 0.0800 px/);
assert.match(P.reverseDetail(pass,.3,0),/Allowed: 0.30 px/);
assert.match(P.reverseDetail(pass,.3,0),/Return check passed/);
assert.match(P.reverseDetail({...pass,round_trip_error_px:.42,reverse_status:'cycle_error'},.3,8),/Rejected: the return position/);
for(const reason of ['source_support','target_support','low_texture','low_correlation','optimizer','parameter_bound']){
 const text=P.reverseDetail({round_trip_error_px:null,reverse_zncc:null,reverse_status:reason},.3,7);
 assert.match(text,/Return error: unavailable/);assert.match(text,/Rejected:/);assert(!text.includes('NaN'));
}
assert.match(P.reverseDetail({reverse_status:'not_checked'},.3,5),/not attempted/);
assert.match(P.reverseDetail({reverse_status:'disabled'},null,0),/disabled/);
assert.match(P.reverseDetail(null,.3,0),/unavailable for this saved run/);
assert.match(P.reverseDetail({...pass,round_trip_error_px:.3000001,reverse_status:'cycle_error'},.3,8),/0.30000010 px/);
assert(P.zeroError([0,0,null]));assert(!P.zeroError([]));assert(!P.zeroError([null,NaN]));assert(!P.zeroError([0,1e-15]));
console.log('PASS: reverse explanations, unavailable/disabled checks, near-threshold precision and exact-zero error labels.');

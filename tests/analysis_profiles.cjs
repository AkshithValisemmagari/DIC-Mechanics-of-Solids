/* Pure profile tests: acceptance masks, holes, signed coordinates and CSV. */
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../web/analysis.js'),'utf8'),context);
const A=context.window.LabAnalysis;
const d={config:{hole_radius_m:.005},dic:[[-10,0,0,0,0,0,0,0,1,1],[-3,0,0,0,0,0,0,0,1,0],[3,0,0,0,0,0,0,0,1,0],[10,0,0,0,0,0,0,0,1,1]],x_m:[-.01,-.003,.003,.01],y_m:[0,0,0,0],fields:{u:{label:'u',unit:'mm',truth:[-1,null,null,1],measured:[-1,100,100,2]}}};
let p=A.profile(d,'u','horizontal',0);
assert.equal(p.stats.n,2);assert.equal(p.stats.max,1);assert.equal(p.rows.length,4);
assert(p.x.includes(null));assert.equal(p.measured.filter(x=>x!==null).length,2);
assert(A.csv(p,false).includes('-3,0,,\n'));assert(A.csv(p,false).includes('-10,0,-1,-1'));
d.baseline=JSON.parse(JSON.stringify(d));d.baseline.fields.u.measured=[-1,0,0,null];
p=A.profile(d,'u','horizontal',0);assert.equal(p.stats.n,1);assert.equal(p.stats.rmse,0);assert.equal(p.baseStats.rmse,0);
assert.equal(A.csv(p,true).split('\n')[0],'x_mm,y_mm,ground_truth_mm,dic_mm,baseline_dic_mm');
const bridged={...d,x_m:[-.01,.01],y_m:[0,0],dic:[d.dic[0],d.dic[3]],fields:{u:{label:'u',unit:'mm',truth:[-1,1],measured:[-1,1]}},baseline:null};
p=A.profile(bridged,'u','horizontal',0);assert.equal(p.x.length,3);assert.equal(p.x[1],null);assert.equal(p.truth[1],null);
console.log('PASS: actual measurement profiles, common-centre errors, invalid-value gaps, hole crossing and CSV.');

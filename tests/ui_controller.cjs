const fs=require('fs'),assert=require('assert');
const {JSDOM}=require('jsdom');
const root=require('path').resolve(__dirname,'..');
const dom=new JSDOM(fs.readFileSync(root+'/web/index.html','utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,errors=[];
w.addEventListener('error',e=>errors.push(e.message));
w.fetch=(url,opts)=>fetch(new URL(url,'http://127.0.0.1:8765'),opts);
w.HTMLCanvasElement.prototype.getContext=function(){return new Proxy({},{get:(target,key)=>target[key]||(()=>{}),set:(target,key,value)=>(target[key]=value,true)});};
w.HTMLCanvasElement.prototype.getBoundingClientRect=()=>({width:500,height:300,left:0,top:0});
w.Image=class {set src(url){fetch(new URL(url,'http://127.0.0.1:8765')).then(r=>r.arrayBuffer()).then(b=>{const a=Buffer.from(b);this.width=a.readUInt32BE(16);this.height=a.readUInt32BE(20);if(this.onload)this.onload();}).catch(e=>this.onerror?.(e));}};

const $=id=>w.document.getElementById(id);
async function until(fn){const end=Date.now()+60000;while(!fn()){if(Date.now()>end)throw Error('Timeout: '+$('message').textContent);await new Promise(r=>setTimeout(r,100));}}
function change(id,value,event='input'){$(id).value=value;$(id).dispatchEvent(new w.Event(event,{bubbles:true}));}
(async()=>{
 for(let i=0;i<50;i++){try{await fetch('http://127.0.0.1:8765/api/settings');break;}catch(e){await new Promise(r=>setTimeout(r,100));}}
 w.eval(fs.readFileSync(root+'/web/model3d.js','utf8'));
 w.eval(fs.readFileSync(root+'/web/app.js','utf8'));
 await until(()=>!$('controls').disabled);
 change('material','steel','change');assert.equal($('E_gpa').value,'200');
 $('experiment').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await until(()=>$('state').textContent==='Experiment complete');
 assert(!$('download').classList.contains('disabled'));assert($('metricError').textContent!=='—');
 assert($('runCaption').textContent.includes('Steel'));
 w.document.querySelector('[data-tab="images"]').click();assert($('images').classList.contains('active'));
 w.document.querySelector('[data-tab="fields"]').click();change('field','von_mises','change');assert($('fieldStats').textContent.includes('Von Mises'));
 const previous=$('metricError').textContent;change('force_n','20000');assert.equal($('state').textContent,'Inputs changed');assert.equal($('metricError').textContent,previous);
 change('material','custom','change');assert.equal($('E_gpa').readOnly,false);
 w.document.querySelector('[data-object="plate_with_hole"]').click();assert(!$('holeControl').hidden);assert.equal($('length_mm').value,'80');
 change('force_n','0');$('experiment').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await until(()=>$('state').textContent==='Experiment complete');assert($('methodDetails').textContent.includes('At zero load'));
 assert($('runCaption').textContent.includes('Plate with a hole'));
 change('force_n','999999999');$('experiment').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await until(()=>$('message').className==='error');assert($('message').textContent.includes('force_n'));
 assert.deepEqual(errors,[]);
 console.log('PASS: presets, custom material, run submission, tabs, field switching, stale results, object selection, zero load, export link and invalid-input error. Canvas drawing is stubbed; this is not a visual browser test.');
 dom.window.close();
})().catch(e=>{console.error(e);dom.window.close();process.exitCode=1;});

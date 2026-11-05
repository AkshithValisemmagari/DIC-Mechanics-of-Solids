/* Deterministic delivery tests: no network, measurements or browser dependency. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/stereo-previews.js'),'utf8');
const keys=['left_reference','right_reference','left_deformed','right_deformed'];
function setup(){
  let now=0,nextTimer=0,inFlight=0,peak=0,changes=0;
  const timers=new Map(),requests=[];
  class Image{
    set src(url){
      this.url=url;
      if(!url){if(this.pending){this.pending=false;inFlight--;}return;}
      this.pending=true;inFlight++;peak=Math.max(peak,inFlight);requests.push(this);
    }
    complete(ok=true){
      assert(this.pending,'Request must be active');this.pending=false;inFlight--;
      if(ok){this.naturalWidth=this.width=800;this.naturalHeight=this.height=192;this.onload?.();}
      else this.onerror?.();
    }
  }
  const sandbox={window:{},Image,setTimeout(fn,ms){const id=++nextTimer;timers.set(id,{at:now+ms,fn});return id;},clearTimeout(id){timers.delete(id);}};
  vm.runInNewContext(source,sandbox);
  const loader=sandbox.window.StereoPreviews.create(()=>changes++);
  function advance(ms){
    const end=now+ms;
    while(true){
      const next=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];
      if(!next||next[1].at>end)break;
      now=next[1].at;timers.delete(next[0]);next[1].fn();
    }
    now=end;
  }
  function finishAll(){while(requests.some(r=>r.pending))requests.find(r=>r.pending).complete();}
  loader.setRun('one','/runs/one/');
  return{loader,requests,advance,finishAll,get peak(){return peak;},get inFlight(){return inFlight;},get changes(){return changes;},timers};
}
function test(name,fn){fn();console.log('PASS: '+name);}
test('only four selected previews load, at most two at once; all four stay cached',()=>{
  const h=setup();h.loader.select(true);
  assert.equal(h.requests.length,2);assert.equal(h.loader.get(keys[2]+'_smoothed').status,'queued');
  h.requests[1].complete();h.requests[0].complete();h.finishAll();
  assert.equal(h.requests.length,4);assert.equal(h.peak,2);
  for(const key of keys)assert.equal(h.loader.get(key+'_smoothed').status,'loaded');
  h.loader.select(true);assert.equal(h.requests.length,4);
  h.loader.select(false);h.finishAll();assert.equal(h.requests.length,8);
  h.loader.select(true);assert.equal(h.requests.length,8);
});
test('temporary failure retries with a fresh URL while other panels finish',()=>{
  const h=setup();h.loader.select(true);const failed=h.requests[0];failed.complete(false);
  h.finishAll();assert.equal(h.loader.get(keys[0]+'_smoothed').status,'retrying');
  assert.equal(h.requests.length,4);h.advance(399);assert.equal(h.requests.length,4);
  h.advance(1);assert.equal(h.requests.length,5);assert.match(h.requests[4].url,/preview_retry=2$/);
  h.requests[4].complete();
  for(const key of keys)assert.equal(h.loader.get(key+'_smoothed').status,'loaded');
  assert.equal(h.peak,2);
});
test('three failures remain visible; redraw does not restart; manual retry recovers',()=>{
  const h=setup();h.loader.select(true);h.requests[0].complete(false);h.finishAll();
  h.advance(400);h.requests.at(-1).complete(false);
  h.advance(1200);h.requests.at(-1).complete(false);
  const key=keys[0]+'_smoothed',count=h.requests.length;
  assert.equal(h.loader.get(key).status,'error');assert.equal(h.loader.get(key).attempts,3);
  h.loader.select(true);h.advance(30000);assert.equal(h.requests.length,count);
  h.loader.retry(key);h.requests.at(-1).complete();
  assert.equal(h.loader.get(key).status,'loaded');assert.equal(h.loader.get(key).attempts,1);
});
test('hung requests time out, release slots and retry without exceeding the limit',()=>{
  const h=setup();h.loader.select(false);const hung=h.requests[0];
  h.requests[1].complete();
  h.advance(15000);
  assert.equal(hung.pending,false);assert.equal(h.loader.get(keys[0]).status,'retrying');
  h.advance(400);assert(h.requests.some(r=>r.url.endsWith('preview_retry=2')));
  assert.equal(h.peak,2);assert(h.inFlight<=2);
});
test('switching mode discards queued old variants and reuses completed images',()=>{
  const h=setup();h.loader.select(true);h.loader.select(false);
  h.requests[0].complete();h.requests[1].complete();h.finishAll();
  assert.equal(h.requests.filter(r=>r.url.includes('_smoothed')).length,2);
  h.loader.select(true);h.finishAll();
  assert.equal(h.requests.filter(r=>r.url.includes('_smoothed')).length,4);
  assert.equal(h.peak,2);
});
test('switching mode cancels scheduled retries for the unselected variant',()=>{
  const h=setup();h.loader.select(true);h.requests[0].complete(false);
  h.loader.select(false);h.finishAll();const count=h.requests.length;
  h.advance(30000);assert.equal(h.requests.length,count);
  h.loader.select(true);h.finishAll();assert.equal(h.loader.get(keys[0]+'_smoothed').status,'loaded');
});
test('a new run cancels old timers and ignores late callbacks',()=>{
  const h=setup();h.loader.select(true);const late=h.requests[1].onload;
  h.requests[0].complete(false);h.loader.setRun('two','/runs/two/');h.loader.select(false);
  late();h.finishAll();h.advance(30000);
  assert.equal(h.requests.filter(r=>r.url.startsWith('/runs/two/')).length,4);
  assert.equal(h.loader.get(keys[0]+'_smoothed').status,'idle');
  for(const key of keys)assert.equal(h.loader.get(key).status,'loaded');
  assert.equal(h.inFlight,0);assert.equal(h.timers.size,0);
});
test('decode failure cannot count as a successfully loaded image',()=>{
  const h=setup();h.loader.select(false);const bad=h.requests[0];
  bad.pending=false;bad.onload();
  assert.equal(h.loader.get(keys[0]).status,'retrying');
});

/* Preview delivery only. No measurement data or acceptance decisions are changed. */
window.StereoPreviews=(()=>{
  const keys=['left_reference','right_reference','left_deformed','right_deformed'];
  const maxAttempts=3,timeoutMs=15000,delays=[400,1200];
  function create(onChange){
    let run=null,prefix='',generation=0,active=0,queue=[],wanted=new Set(),entries=new Map();
    function enqueue(key){
      const entry=entries.get(key)||{status:'idle',attempts:0,image:null};
      entries.set(key,entry);
      if(entry.status!=='idle')return;
      entry.status='queued';queue.push(key);
    }
    function pump(){
      while(active<2&&queue.length){
        const key=queue.shift(),entry=entries.get(key);
        if(!wanted.has(key)||entry.status!=='queued')continue;
        const current=generation,image=new Image();let finished=false;
        entry.status='loading';entry.attempts++;active++;
        function finish(ok){
          if(finished||current!==generation)return;
          finished=true;clearTimeout(entry.timeout);image.onload=image.onerror=null;
          entry.cancel=null;active--;
          if(ok&&image.naturalWidth>0&&image.naturalHeight>0){
            entry.status='loaded';entry.image=image;
          }else if(!wanted.has(key)){
            entry.status='idle';entry.attempts=0;
          }else if(entry.attempts<maxAttempts){
            entry.status='retrying';
            entry.retryTimer=setTimeout(()=>{
              entry.retryTimer=null;
              if(current!==generation)return;
              entry.status='idle';
              if(wanted.has(key)){enqueue(key);pump();onChange();}
            },delays[entry.attempts-1]);
          }else entry.status='error';
          pump();onChange();
        }
        entry.cancel=()=>{
          finished=true;clearTimeout(entry.timeout);image.onload=image.onerror=null;
          image.src='';
        };
        image.onload=()=>finish(true);image.onerror=()=>finish(false);
        entry.timeout=setTimeout(()=>{
          // Stop a hung transfer before opening another queue slot.
          image.onload=image.onerror=null;image.src='';finish(false);
        },timeoutMs);
        // Bypass a cached gateway failure on subsequent attempts.
        image.src=prefix+key+'.png'+(entry.attempts>1?'?preview_retry='+entry.attempts:'');
      }
    }
    function setRun(id,assetPrefix){
      if(run===id&&prefix===assetPrefix)return false;
      generation++;
      for(const entry of entries.values()){
        clearTimeout(entry.retryTimer);entry.cancel?.();
      }
      run=id;prefix=assetPrefix;active=0;queue=[];wanted=new Set();entries=new Map();
      return true;
    }
    function select(smoothed){
      const selected=keys.map(key=>key+(smoothed?'_smoothed':''));
      wanted=new Set(selected);
      queue=queue.filter(key=>wanted.has(key));
      for(const [key,entry] of entries){
        if(wanted.has(key))continue;
        if(entry.status==='queued')entry.status='idle';
        if(entry.status==='retrying'){
          clearTimeout(entry.retryTimer);entry.retryTimer=null;entry.status='idle';
        }
      }
      for(const key of selected)enqueue(key);
      pump();
    }
    function get(key){return entries.get(key)||{status:'idle',attempts:0,image:null};}
    function retry(key){
      const entry=entries.get(key);
      if(!wanted.has(key)||entry?.status!=='error')return;
      entry.status='idle';entry.attempts=0;enqueue(key);pump();onChange();
    }
    return{setRun,select,get,retry};
  }
  return{create};
})();

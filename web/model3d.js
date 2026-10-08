/* Local 3D renderer for the deformation panel only.
 * A perspective camera displays the existing in-plane solution extruded through
 * the entered thickness. No out-of-plane mechanics are added or inferred.
 * No network libraries or WebGL support required.
 */
window.Specimen3D=(()=>{
  const view={yaw:-.52,pitch:.40,zoom:1};
  let cached=null,geometry=null,boundCanvas=null,redraw=null,drag=null;
  const stressIndex={stress_xx:5,stress_yy:6,tau:7,von_mises:8};
  function stressColor(value,max){const t=max>0?clamp(value/max,0,1):0,stops=[[48,117,232],[33,196,204],[244,211,70],[247,135,49],[229,55,54]],p=t*4,i=Math.min(3,Math.floor(p)),f=p-i;return stops[i].map((v,k)=>Math.round(v+(stops[i+1][k]-v)*f));}
  function stressRange(data,mode,phase){const k={stress_xx:0,stress_yy:1,tau:2,von_mises:3}[mode];if(k==null||!data?.stress_surface)return null;const max=data.stress_surface.reduce((a,p)=>Math.max(a,Math.abs(p[k])),0);return{max,peak:max*phase};}
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  function reset(){Object.assign(view,{yaw:-.52,pitch:.40,zoom:1});redraw?.();}
  function front(){Object.assign(view,{yaw:0,pitch:0,zoom:1});redraw?.();}
  function zoom(amount){view.zoom=clamp(view.zoom*amount,.4,3.5);redraw?.();}
  function connect(el,callback){
    if(boundCanvas===el)return;boundCanvas=el;redraw=callback;
    el.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={x:e.clientX,y:e.clientY,id:e.pointerId};el.setPointerCapture?.(e.pointerId);el.classList.add('orbiting');});
    el.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;view.yaw+=(e.clientX-drag.x)*.008;view.pitch=clamp(view.pitch+(e.clientY-drag.y)*.008,-1.45,1.45);drag.x=e.clientX;drag.y=e.clientY;redraw();});
    const release=()=>{drag=null;el.classList.remove('orbiting');};
    el.addEventListener('pointerup',release);el.addEventListener('pointercancel',release);el.addEventListener('lostpointercapture',release);
    el.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.001));},{passive:false});
    el.addEventListener('dblclick',reset);
    el.addEventListener('keydown',e=>{let handled=true;switch(e.key){case'ArrowLeft':view.yaw-=.12;break;case'ArrowRight':view.yaw+=.12;break;case'ArrowUp':view.pitch=clamp(view.pitch-.12,-1.45,1.45);break;case'ArrowDown':view.pitch=clamp(view.pitch+.12,-1.45,1.45);break;case'+':case'=':zoom(1.15);break;case'-':zoom(1/1.15);break;case'0':reset();break;default:handled=false;}if(handled){e.preventDefault();redraw();}});
    document.getElementById('viewReset')?.addEventListener('click',reset);
    document.getElementById('viewFront')?.addEventListener('click',front);
    document.getElementById('viewZoomIn')?.addEventListener('click',()=>zoom(1.2));
    document.getElementById('viewZoomOut')?.addEventListener('click',()=>zoom(1/1.2));
  }
  // Bilinear sampling is for display tessellation only; it never enters DIC.
  function sample(data,x,y){
    const grid=data.mesh,ny=grid.length,nx=grid[0].length,b=data.bounds;
    const gx=clamp((x-b[0])/(b[1]-b[0])*(nx-1),0,nx-1),gy=clamp((y-b[2])/(b[3]-b[2])*(ny-1),0,ny-1);
    const ix=Math.min(nx-2,Math.floor(gx)),iy=Math.min(ny-2,Math.floor(gy)),s=gx-ix,t=gy-iy;
    const mix=k=>(1-t)*((1-s)*grid[iy][ix][k]+s*grid[iy][ix+1][k])+t*((1-s)*grid[iy+1][ix][k]+s*grid[iy+1][ix+1][k]);
    return[x,y,mix(2),mix(3)];
  }
  function build(data){
    const vertices=[],faces=[],edgeLoops=[];
    const thickness=data.config.user_inputs.thickness_mm/1000;
    function add(p,z,stress){vertices.push([p[0],p[1],z,p[2],p[3],...(stress||[])]);return vertices.length-1;}
    function surfaces(points,cells,loops){
      const top=points.map((p,i)=>add(p,thickness/2,data.stress_surface?.[i])),bottom=points.map((p,i)=>add(p,-thickness/2,data.stress_surface?.[i]));
      for(const cell of cells){faces.push({ids:cell.map(i=>top[i]),kind:'face'});faces.push({ids:[...cell].reverse().map(i=>bottom[i]),kind:'back'});}
      for(const {ids,hole} of loops){
        edgeLoops.push(ids.map(i=>top[i]),ids.map(i=>bottom[i]));
        for(let j=0;j<ids.length;j++){const a=ids[j],b=ids[(j+1)%ids.length];faces.push({ids:hole?[top[a],top[b],bottom[b],bottom[a]]:[top[a],bottom[a],bottom[b],top[b]],kind:'side'});}
      }
    }
    if(data.hole?.length){
      // Ring-to-rectangle mesh: no triangles span the open hole.
      const rings=14,points=[],cells=[],a=data.config.hole_radius_m,b=data.bounds;
      const angleValues=Array.from({length:96},(_,j)=>2*Math.PI*j/96);
      // Include exact rectangle corners in addition to uniform angular rays.
      for(const x of [b[0],b[1]])for(const y of [b[2],b[3]]){const angle=(Math.atan2(y,x)+2*Math.PI)%(2*Math.PI);if(!angleValues.some(v=>Math.abs(v-angle)<1e-10))angleValues.push(angle);}
      angleValues.sort((x,y)=>x-y);const angles=angleValues.length;
      for(let r=0;r<=rings;r++)for(let j=0;j<angles;j++){
        const theta=angleValues[j],ct=Math.cos(theta),st=Math.sin(theta);
        const radius=Math.min(ct>=0?b[1]/Math.max(ct,1e-12):b[0]/Math.min(ct,-1e-12),st>=0?b[3]/Math.max(st,1e-12):b[2]/Math.min(st,-1e-12));
        const distance=a+(radius-a)*r/rings,x=distance*ct,y=distance*st;
        let p=sample(data,x,y);
        if(r===0){const pos=theta/(2*Math.PI)*(data.hole.length-1),k=Math.floor(pos),f=pos-k,p0=data.hole[k],p1=data.hole[Math.min(k+1,data.hole.length-1)];p=[x,y,p0[2]*(1-f)+p1[2]*f,p0[3]*(1-f)+p1[3]*f];}
        points.push(p);
      }
      for(let r=0;r<rings;r++)for(let j=0;j<angles;j++){const k=(j+1)%angles;cells.push([r*angles+j,(r+1)*angles+j,(r+1)*angles+k,r*angles+k]);}
      surfaces(points,cells,[{ids:Array.from({length:angles},(_,j)=>rings*angles+j),hole:false},{ids:Array.from({length:angles},(_,j)=>j),hole:true}]);
    }else{
      const rows=data.mesh.length,cols=data.mesh[0].length,points=data.mesh.flat().map(p=>p.slice(0,4)),cells=[],outer=[];
      for(let y=0;y<rows-1;y++)for(let x=0;x<cols-1;x++){const i=y*cols+x;cells.push([i,i+1,i+1+cols,i+cols]);}
      for(let x=0;x<cols;x++)outer.push(x);for(let y=1;y<rows;y++)outer.push(y*cols+cols-1);for(let x=cols-2;x>=0;x--)outer.push((rows-1)*cols+x);for(let y=rows-2;y>0;y--)outer.push(y*cols);
      surfaces(points,cells,[{ids:outer,hole:false}]);
    }
    return{vertices,faces,edgeLoops,thickness};
  }
  function rotate(p){const cy=Math.cos(view.yaw),sy=Math.sin(view.yaw),cp=Math.cos(view.pitch),sp=Math.sin(view.pitch),x=p[0]*cy+p[2]*sy,z=-p[0]*sy+p[2]*cy;return[x,p[1]*cp-z*sp,p[1]*sp+z*cp];}
  function normal(a,b,c){const u=b.map((v,i)=>v-a[i]),v=c.map((q,i)=>q-a[i]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],length=Math.hypot(...n)||1;return n.map(v=>v/length);}
  function render(ctx,w,h,data,mag,phase,mode="von_mises"){
    if(w<10||h<10)return;
    ctx.fillStyle='#112f30';ctx.fillRect(0,0,w,h);ctx.strokeStyle='rgba(157,201,185,.045)';ctx.lineWidth=1;
    for(let x=0;x<w;x+=28){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=0;y<h;y+=28){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    if(!data)return;
    if(cached!==data){cached=data;geometry=build(data);}
    const {vertices,faces,edgeLoops,thickness}=geometry,f=mag*phase,b=data.bounds;
    const range=stressRange(data,mode,phase),stressKey=stressIndex[mode];
    let lo=[b[0],b[2],-thickness/2],hi=[b[1],b[3],thickness/2];
    for(const p of vertices){lo[0]=Math.min(lo[0],p[0]+mag*p[3]);hi[0]=Math.max(hi[0],p[0]+mag*p[3]);lo[1]=Math.min(lo[1],p[1]+mag*p[4]);hi[1]=Math.max(hi[1],p[1]+mag*p[4]);}
    const centre=lo.map((v,i)=>(v+hi[i])/2),radius=Math.hypot(...hi.map((v,i)=>(v-lo[i])/2))||1;
    const distance=4;
    function cameraPoint(p){return rotate(p.map((v,i)=>(v-centre[i])/radius));}
    // Fit the full-load envelope at this camera angle, so animation does not
    // breathe in size and slender beams still use the available viewport.
    const fit=[];
    for(const p of vertices)for(const amount of [0,mag]){const q=cameraPoint([p[0]+amount*p[3],p[1]+amount*p[4],p[2]]),k=distance/(distance-q[2]);fit.push([q[0]*k,q[1]*k]);}
    let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
    for(const p of fit){x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,p[1]);y1=Math.max(y1,p[1]);}
    const scale=.92*Math.min(Math.max(20,w-160)/Math.max(x1-x0,.05),Math.max(20,h-145)/Math.max(y1-y0,.05))*view.zoom;
    function project(p){const k=distance/(distance-p[2]);return[w/2+scale*(p[0]*k-(x0+x1)/2),h/2-scale*(p[1]*k-(y0+y1)/2),p[2]];}
    const camera=vertices.map(p=>cameraPoint([p[0]+f*p[3],p[1]+f*p[4],p[2]])),screen=camera.map(project);
    const original=vertices.map(p=>project(cameraPoint(p.slice(0,3))));
    function line(points,close=true){ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));if(close)ctx.closePath();}
    // Undeformed wire outline is a reference overlay, not a second solid.
    ctx.setLineDash([4,5]);ctx.strokeStyle='rgba(153,180,171,.55)';ctx.lineWidth=1;
    for(const ids of edgeLoops){line(ids.map(i=>original[i]));ctx.stroke();}ctx.setLineDash([]);
    const sorted=faces.map(face=>({face,z:face.ids.reduce((s,i)=>s+camera[i][2],0)/face.ids.length})).sort((a,b)=>a.z-b.z);
    for(const {face} of sorted){const a=camera[face.ids[0]],b1=camera[face.ids[1]],c=camera[face.ids[2]],n=normal(a,b1,c);const centreFace=face.ids.reduce((s,i)=>s.map((v,k)=>v+camera[i][k]/face.ids.length),[0,0,0]);
      // Back-face culling uses the perspective camera position.
      if(n[0]*(-centreFace[0])+n[1]*(-centreFace[1])+n[2]*(distance-centreFace[2])<=0)continue;
      const light=.40+.60*Math.max(0,n[0]*(-.25)+n[1]*.45+n[2]*.857);
      const value=range?face.ids.reduce((sum,i)=>sum+Math.abs(vertices[i][stressKey])*phase,0)/face.ids.length:0;
      const base=range?stressColor(value,range.max):face.kind==='side'?[44,139,124]:[105,205,164];
      const shade=range ? .86+.14*light : light;
      ctx.fillStyle=`rgb(${base.map(v=>Math.round(v*shade)).join(',')})`;
      line(face.ids.map(i=>screen[i]));ctx.fill();ctx.strokeStyle=range?'rgba(17,47,48,.10)':face.kind==='side'?'rgba(99,193,161,.35)':'rgba(17,71,64,.28)';ctx.lineWidth=.5;ctx.stroke();
    }
    // Force arrow belongs to the same world coordinates as the specimen.
    const anchor=sample(data,b[1],0),beam=data.config.benchmark==='cantilever',span=(b[1]-b[0])*.11;
    const origin=[anchor[0]+f*anchor[2]+(beam?span*.3:span*.12),anchor[1]+f*anchor[3],thickness/2];
    const end=[origin[0]+(beam?0:span),origin[1]+(beam?span:0),origin[2]];
    const aa=project(cameraPoint(origin)),bb=project(cameraPoint(end)),dx=bb[0]-aa[0],dy=bb[1]-aa[1],len=Math.hypot(dx,dy)||1;
    ctx.strokeStyle='#e4eeb7';ctx.fillStyle='#e4eeb7';ctx.lineWidth=2;line([aa,bb],false);ctx.stroke();line([bb,[bb[0]-dx/len*9-dy/len*4,bb[1]-dy/len*9+dx/len*4],[bb[0]-dx/len*9+dy/len*4,bb[1]-dy/len*9-dx/len*4]]);ctx.fill();
    ctx.font='10px system-ui';ctx.fillText(`${Number((data.config.load_description.force_n*phase).toFixed(1)).toLocaleString()} N`,clamp(bb[0]+8,20,w-100),clamp(bb[1]-9,75,h-58));
    // Orientation gizmo: x/y are in-plane; z is the displayed thickness axis.
    const o=[w-64,h-66];for(const [axis,color,label] of [[[1,0,0],'#df9e84','x'],[[0,1,0],'#a7dba1','y'],[[0,0,1],'#8fc3e1','z']]){const r=rotate(axis);ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1.5;line([o,[o[0]+r[0]*26,o[1]-r[1]*26]],false);ctx.stroke();ctx.font='10px system-ui';ctx.fillText(label,o[0]+r[0]*34-3,o[1]-r[1]*34+3);}
  }
  return{render,connect,reset,front,zoom,stressRange,stressColor};
})();

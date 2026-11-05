"""Virtual lab: local by default, or --host 0.0.0.0 --no-browser for hosting."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
from copy import deepcopy
import os
from http.cookies import SimpleCookie
import shutil
import json
from pathlib import Path
import secrets
import subprocess
import threading
import time
import traceback
import urllib.parse
import webbrowser
import zipfile
import numpy as np
from lab_config import DEFAULTS, MATERIALS, build_config
from mechanics import Benchmark
from pipeline import run_experiment
from stress import invariants

ROOT=Path(__file__).resolve().parent
WEB=ROOT/'web'
RUNS=Path(os.environ.get('LAB_RUNS_DIR',str(ROOT/'outputs'/'interactive'))).resolve()
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.Lock()
SESSIONS={}
COOKIE_NAME='lab_session'
SESSION_TTL=6*60*60
MAX_SESSIONS=64
MAX_SAVED_RUNS=5
MAX_PENDING_JOBS=4
PENDING_JOBS=0

APP_VERSION='2026.11.05-stereo-previews'


def build_info():
    """Capture the running build at startup, including archive deployments."""
    revision=os.environ.get('LAB_BUILD_ID') or os.environ.get('RENDER_GIT_COMMIT')
    if not revision:
        try:
            result=subprocess.run(['git','rev-parse','--short=12','HEAD'],cwd=ROOT,
                                  capture_output=True,text=True,timeout=2,check=True)
            revision=result.stdout.strip()
        except (OSError,subprocess.SubprocessError):
            revision='source-archive'
    return dict(version=APP_VERSION,revision=str(revision)[:40])


BUILD_INFO=build_info()


def new_session():
    return dict(status='idle',stage='Ready',job_id=None,result=None,error=None,
                token=secrets.token_urlsafe(24),updated=time.monotonic(),runs=set())


def prune_sessions():
    # Called under LOCK. Active jobs cannot expire while queued or executing.
    cutoff=time.monotonic()-SESSION_TTL
    expired=[sid for sid,state in SESSIONS.items()
             if state['updated']<cutoff and state['status']!='running']
    for sid in expired:
        state=SESSIONS.pop(sid)
        for run_id in state['runs']: shutil.rmtree(RUNS/run_id,ignore_errors=True)



def clean_json(value):
    if isinstance(value,np.ndarray): return clean_json(value.tolist())
    if isinstance(value,dict): return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean_json(v) for v in value]
    if isinstance(value,(float,np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer): return int(value)
    return value


def stress_surface(model):
    """Exact analytical stress at display vertices, in MPa; never DIC input."""
    xmin,xmax,ymin,ymax=model.bounds
    if model.hole_radius:
        angles=list(np.arange(96)*2*np.pi/96)
        for x in (xmin,xmax):
            for y in (ymin,ymax):
                angle=np.arctan2(y,x)%(2*np.pi)
                if not any(abs(v-angle)<1e-10 for v in angles): angles.append(angle)
        angles=np.array(sorted(angles));ct,st=np.cos(angles),np.sin(angles)
        outer=np.minimum(np.where(ct>=0,xmax/np.maximum(ct,1e-12),xmin/np.minimum(ct,-1e-12)),
                         np.where(st>=0,ymax/np.maximum(st,1e-12),ymin/np.minimum(st,-1e-12)))
        radius=model.hole_radius+(outer-model.hole_radius)*np.arange(15)[:,None]/14
        x=(radius*ct).ravel();y=(radius*st).ravel()
    else:
        x,y=np.meshgrid(np.linspace(xmin,xmax,49),np.linspace(ymin,ymax,29))
        x=x.ravel();y=y.ravel()
    sx,sy,tau=model.stress(x,y)
    vm=np.sqrt(np.maximum(0,sx*sx-sx*sy+sy*sy+3*tau*tau))
    return np.column_stack((sx,sy,tau,vm))/1e6


def make_payload(b,run_id):
    c=b['config'];model=Benchmark(c);xmin,xmax,ymin,ymax=model.bounds
    rows,cols=29,49
    x,y=np.meshgrid(np.linspace(xmin,xmax,cols),np.linspace(ymin,ymax,rows))
    u,v=model.displacement(x,y);valid=model.material_mask(x,y)
    mesh=np.stack((x,y,u,v,valid),axis=-1)
    boundary=[]
    for xx,yy in [(np.linspace(xmin,xmax,100),np.full(100,ymin)),(np.full(100,xmax),np.linspace(ymin,ymax,100)),(np.linspace(xmax,xmin,100),np.full(100,ymax)),(np.full(100,xmin),np.linspace(ymax,ymin,100))]:
        uu,vv=model.displacement(xx,yy);boundary.extend(np.column_stack((xx,yy,uu,vv)).tolist())
    hole=[]
    if model.hole_radius:
        theta=np.linspace(0,2*np.pi,180);xx=model.hole_radius*np.cos(theta);yy=model.hole_radius*np.sin(theta)
        uu,vv=model.displacement(xx,yy);hole=np.column_stack((xx,yy,uu,vv))
    d=b['dic'];true_inv=invariants(b['true_stress'])
    fields={
        'u_mm':{'label':'Horizontal displacement u','unit':'mm','truth':b['true_disp'][:,0]*b['summary']['pixel_size_m'][0]*1000,'measured':d[:,2]*b['summary']['pixel_size_m'][0]*1000},
        'v_mm':{'label':'Vertical displacement v (up positive)','unit':'mm','truth':-b['true_disp'][:,1]*b['summary']['pixel_size_m'][1]*1000,'measured':-d[:,3]*b['summary']['pixel_size_m'][1]*1000},
        'displacement':{'label':'Displacement magnitude','unit':'px','truth':np.linalg.norm(b['true_disp'],axis=1),'measured':np.linalg.norm(d[:,2:4],axis=1)},
        'strain_xx':{'label':'Axial strain','unit':'με','truth':b['true_strain'][:,0]*1e6,'measured':b['strain'][:,0]*1e6},
        'strain_yy':{'label':'Transverse strain','unit':'με','truth':b['true_strain'][:,1]*1e6,'measured':b['strain'][:,1]*1e6},
        'shear':{'label':'Engineering shear strain','unit':'με','truth':b['true_strain'][:,2]*1e6,'measured':b['strain'][:,2]*1e6},
        'stress_xx':{'label':'Axial stress','unit':'MPa','truth':b['true_stress'][:,0]/1e6,'measured':b['stress'][:,0]/1e6},
        'stress_yy':{'label':'Transverse stress','unit':'MPa','truth':b['true_stress'][:,1]/1e6,'measured':b['stress'][:,1]/1e6},
        'tau':{'label':'Shear stress','unit':'MPa','truth':b['true_stress'][:,2]/1e6,'measured':b['stress'][:,2]/1e6},
        'principal':{'label':'Major in-plane principal stress','unit':'MPa','truth':true_inv[:,0]/1e6,'measured':b['invariants'][:,0]/1e6},
        'von_mises':{'label':'Von Mises stress','unit':'MPa','truth':true_inv[:,2]/1e6,'measured':b['invariants'][:,2]/1e6}}
    p=dict(run_id=run_id,asset_prefix=f'/runs/{run_id}/',config=c,summary=b['summary'],mesh=mesh,boundary=boundary,hole=hole,
           bounds=model.bounds,stress_surface=stress_surface(model),consistency=b.get('consistency'),dic=d,fields=fields,true_disp=b['true_disp'],x_m=b['x'],y_m=b['y'])
    return clean_json(p)


def execute(config,run_id,session_id):
    global PENDING_JOBS
    state=SESSIONS[session_id]
    try:
        started=time.perf_counter()
        with LOCK: state['stage']='Solving analytical shaft torsion…' if config.get('analysis_only') else 'Generating images and solving subpixel DIC…'
        directory=RUNS/run_id
        def progress(message):
            with LOCK: state['stage']=message
        if config.get('stereo'):
            from stereo_experiment import run_stereo
            payload=run_stereo(config,run_id,directory,progress)
        elif config.get('analysis_only'):
            from torsion import run_torsion
            payload=run_torsion(config,run_id,directory)
        else:
            b=run_experiment(config,directory,progress=progress)
            payload=make_payload(b,run_id)
            if config.get('compare_noise'):
                from noise_comparison import compare_payloads, save_comparison
                with LOCK: state['stage']='Running the identical specimen without added noise…'
                baseline_config=deepcopy(config)
                baseline_config['camera']['noise_std']=0
                baseline_config['user_inputs']['noise_std']=0
                baseline_config['compare_noise']=False
                baseline_config['user_inputs']['compare_noise']=False
                baseline=run_experiment(baseline_config,directory/'baseline',
                    progress=lambda stage:progress('No-added-noise comparison · '+stage))
                base_payload=make_payload(baseline,run_id)
                base_payload['asset_prefix']=f'/runs/{run_id}/baseline/'
                payload['baseline']=base_payload
                payload['noise_comparison']=compare_payloads(base_payload,payload)
                save_comparison(payload['noise_comparison'],directory)
        payload['elapsed_s']=round(time.perf_counter()-started,2)
        (directory/'interactive_result.json').write_text(
    json.dumps(payload, allow_nan=False),
    encoding='utf-8'
)
        with LOCK:
            state.update(status='done',stage='Experiment complete',result=payload,error=None,updated=time.monotonic())
            while len(state['runs'])>MAX_SAVED_RUNS:
                oldest=min(state['runs']-{run_id})
                state['runs'].remove(oldest)
                shutil.rmtree(RUNS/oldest,ignore_errors=True)
    except Exception as error:
        traceback.print_exc()
        with LOCK: state.update(status='error',stage='Experiment could not complete',error=str(error),updated=time.monotonic())
    finally:
        with LOCK: PENDING_JOBS-=1


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(WEB),**kwargs)
    def log_message(self,format,*args): pass
    def end_headers(self):
        if getattr(self,'new_cookie',None):
            self.send_header('Set-Cookie',self.new_cookie)
            self.new_cookie=None
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def session(self,create=False):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: pass
        item=cookie.get(COOKIE_NAME);sid=item.value if item else None
        with LOCK:
            prune_sessions()
            state=SESSIONS.get(sid)
            if state is None and create:
                if len(SESSIONS)>=MAX_SESSIONS: return None,None
                sid=secrets.token_urlsafe(32);state=new_session();SESSIONS[sid]=state
                secure='; Secure' if os.environ.get('LAB_COOKIE_SECURE')=='1' else ''
                self.new_cookie=f'{COOKIE_NAME}={sid}; Path=/; HttpOnly; SameSite=Lax{secure}'
            if state is not None: state['updated']=time.monotonic()
        return sid,state
    def do_HEAD(self):
        # Do not let the inherited file handler bypass run access checks.
        self.send_error(405)

    def json_response(self,data,status=200):
        raw=json.dumps(data,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/healthz': return self.json_response({'status':'ok'})
        if path.startswith('/api/'):
            sid,state=self.session(create=True)
            if state is None: return self.json_response({'error':'The lab is busy. Please try again later.'},503)
        if path=='/api/settings': return self.json_response(dict(defaults=DEFAULTS,materials=MATERIALS,token=state['token'],build=BUILD_INFO))
        if path=='/api/status':
            with LOCK: snapshot={k:state[k] for k in ('status','stage','job_id','error')}
            return self.json_response(snapshot)
        if path=='/api/result':
            with LOCK: payload=state['result']
            return self.json_response(payload)
        if path.startswith('/runs/'):
            parts=path.split('/')
            if len(parts) not in (4,5) or not all(ch.isalnum() or ch=='-' for ch in parts[2]): return self.send_error(404)
            sid,state=self.session()
            with LOCK: owned=state is not None and parts[2] in state['runs']
            if not owned: return self.send_error(404)
            folder=RUNS/parts[2]
            if len(parts)==5:
                if parts[3]!='baseline': return self.send_error(404)
                folder=folder/'baseline'
            filename=parts[-1]
            if filename=='download.zip' and len(parts)==4 and folder.is_dir():
                memory=io.BytesIO()
                with zipfile.ZipFile(memory,'w',zipfile.ZIP_DEFLATED) as z:
                    for f in folder.rglob('*'):
                        if f.is_file(): z.write(f,str(f.relative_to(folder)))
                raw=memory.getvalue();self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition',f'attachment; filename="experiment-{parts[2]}.zip"');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            allowed={'reference_smoothed.png','deformed_smoothed.png','reference.png','deformed.png','reference_mask.png','deformed_mask.png','images_and_error.png','field_comparison.png','report.html','config.json','summary.json','dic_displacements.csv','mechanical_fields.csv','errors.csv','noise_comparison.csv','noise_comparison.json','torsion_twist.csv','torsion_stress.csv','torsion_analysis.png'}
            allowed.update({f'{eye}_{phase}{suffix}.png' for eye in ('left','right') for phase in ('reference','deformed') for suffix in ('','_mask','_smoothed')})
            allowed.update({'dic_input_images.npz','stereo_fields.csv','stereo_correspondences.csv','camera_calibration.json'})
            if filename not in allowed or not (folder/filename).is_file(): return self.send_error(404)
            f=folder/filename;raw=f.read_bytes();self.send_response(200);self.send_header('Content-Type',self.guess_type(str(f)));self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if path not in ('/','/index.html','/style.css','/app.js','/model3d.js','/analysis.js','/experiments.js','/stereo.js','/stereo-previews.js','/presentation.js','/results.js'): return self.send_error(404)
        return super().do_GET()
    def do_POST(self):
        global PENDING_JOBS
        if self.path!='/api/run': return self.send_error(404)
        sid,state=self.session()
        if state is None or not secrets.compare_digest(self.headers.get('X-Lab-Token',''),state['token']): return self.json_response({'error':'Reload the lab page and try again.'},403)
        origin=self.headers.get('Origin')
        if origin and urllib.parse.urlparse(origin).netloc!=self.headers.get('Host'):
            return self.json_response({'error':'Request origin does not match this lab.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<20000: raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Settings must be a JSON object.')
            config=build_config(data)
        except (ValueError,TypeError,KeyError,UnicodeError) as error: return self.json_response({'error':str(error)},400)
        with LOCK:
            if state['status']=='running': return self.json_response({'error':'An experiment is already running.'},409)
            if PENDING_JOBS>=MAX_PENDING_JOBS: return self.json_response({'error':'The lab is busy. Please try again shortly.'},429)
            PENDING_JOBS+=1
            run_id=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
            state.update(status='running',stage='Queued for calculation…',job_id=run_id,error=None)
            state['runs'].add(run_id)
        POOL.submit(execute,config,run_id,sid)
        return self.json_response({'job_id':run_id},202)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8765')))
    parser.add_argument('--host',default='0.0.0.0' if os.environ.get('PORT') else '127.0.0.1')
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    RUNS.mkdir(parents=True,exist_ok=True)
    try: server=ThreadingHTTPServer((args.host,args.port),Handler)
    except OSError as error:
        parser.exit(1,f'Cannot open port {args.port}: {error}\nTry: python lab_server.py --port 8766\n')
    url=f'http://127.0.0.1:{server.server_address[1]}'
    print(f'Virtual Solid Mechanics Lab → {url}\nKeep this terminal open. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser and not os.environ.get('PORT'): threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nClosing lab. Waiting for any active experiment to finish…')
    finally: server.server_close();POOL.shutdown(wait=True)

if __name__=='__main__':main()

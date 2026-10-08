"""Local-only virtual lab. Run: python lab_server.py (opens your browser)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import secrets
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
RUNS=ROOT/'outputs'/'interactive'
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.Lock()
STATE={'status':'idle','stage':'Ready','job_id':None,'result':None,'error':None}
TOKEN=secrets.token_urlsafe(24)


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
        'displacement':{'label':'Displacement magnitude','unit':'px','truth':np.linalg.norm(b['true_disp'],axis=1),'measured':np.linalg.norm(d[:,2:4],axis=1)},
        'strain_xx':{'label':'Axial strain','unit':'με','truth':b['true_strain'][:,0]*1e6,'measured':b['strain'][:,0]*1e6},
        'strain_yy':{'label':'Transverse strain','unit':'με','truth':b['true_strain'][:,1]*1e6,'measured':b['strain'][:,1]*1e6},
        'shear':{'label':'Engineering shear strain','unit':'με','truth':b['true_strain'][:,2]*1e6,'measured':b['strain'][:,2]*1e6},
        'stress_xx':{'label':'Axial stress','unit':'MPa','truth':b['true_stress'][:,0]/1e6,'measured':b['stress'][:,0]/1e6},
        'stress_yy':{'label':'Transverse stress','unit':'MPa','truth':b['true_stress'][:,1]/1e6,'measured':b['stress'][:,1]/1e6},
        'tau':{'label':'Shear stress','unit':'MPa','truth':b['true_stress'][:,2]/1e6,'measured':b['stress'][:,2]/1e6},
        'principal':{'label':'Major in-plane principal stress','unit':'MPa','truth':true_inv[:,0]/1e6,'measured':b['invariants'][:,0]/1e6},
        'von_mises':{'label':'Von Mises stress','unit':'MPa','truth':true_inv[:,2]/1e6,'measured':b['invariants'][:,2]/1e6}}
    p=dict(run_id=run_id,config=c,summary=b['summary'],mesh=mesh,boundary=boundary,hole=hole,
           bounds=model.bounds,stress_surface=stress_surface(model),dic=d,fields=fields,true_disp=b['true_disp'],x_m=b['x'],y_m=b['y'])
    return clean_json(p)


def execute(config,run_id):
    try:
        started=time.perf_counter()
        with LOCK: STATE['stage']='Generating images and solving subpixel DIC…'
        directory=RUNS/run_id
        b=run_experiment(config,directory)
        payload=make_payload(b,run_id)
        payload['elapsed_s']=round(time.perf_counter()-started,2)
        (directory/'interactive_result.json').write_text(json.dumps(payload,allow_nan=False))
        with LOCK: STATE.update(status='done',stage='Experiment complete',result=payload,error=None)
    except Exception as error:
        traceback.print_exc()
        with LOCK: STATE.update(status='error',stage='Experiment could not complete',error=str(error))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(WEB),**kwargs)
    def log_message(self,format,*args): pass
    def json_response(self,data,status=200):
        raw=json.dumps(data,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/settings': return self.json_response(dict(defaults=DEFAULTS,materials=MATERIALS,token=TOKEN))
        if path=='/api/status':
            with LOCK: snapshot={k:v for k,v in STATE.items() if k!='result'}
            return self.json_response(snapshot)
        if path=='/api/result':
            with LOCK: payload=STATE['result']
            return self.json_response(payload)
        if path.startswith('/runs/'):
            parts=path.split('/')
            if len(parts)!=4 or not all(ch.isalnum() or ch=='-' for ch in parts[2]): return self.send_error(404)
            folder=RUNS/parts[2]
            if parts[3]=='download.zip' and folder.is_dir():
                memory=io.BytesIO()
                with zipfile.ZipFile(memory,'w',zipfile.ZIP_DEFLATED) as z:
                    for f in folder.iterdir():
                        if f.is_file(): z.write(f,f.name)
                raw=memory.getvalue();self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition',f'attachment; filename="experiment-{parts[2]}.zip"');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            allowed={'reference.png','deformed.png','reference_mask.png','deformed_mask.png','images_and_error.png','field_comparison.png','report.html','config.json','summary.json','dic_displacements.csv','mechanical_fields.csv','errors.csv'}
            if parts[3] not in allowed or not (folder/parts[3]).is_file(): return self.send_error(404)
            f=folder/parts[3];raw=f.read_bytes();self.send_response(200);self.send_header('Content-Type',self.guess_type(str(f)));self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/run': return self.send_error(404)
        if self.headers.get('X-Lab-Token')!=TOKEN: return self.json_response({'error':'Reload the lab page and try again.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<20000: raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(length));config=build_config(data)
        except (ValueError,TypeError,KeyError) as error: return self.json_response({'error':str(error)},400)
        with LOCK:
            if STATE['status']=='running': return self.json_response({'error':'An experiment is already running.'},409)
            run_id=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
            STATE.update(status='running',stage='Preparing the experiment…',job_id=run_id,error=None)
        POOL.submit(execute,config,run_id)
        return self.json_response({'job_id':run_id},202)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    RUNS.mkdir(parents=True,exist_ok=True)
    try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError as error:
        parser.exit(1,f'Cannot open port {args.port}: {error}\nTry: python lab_server.py --port 8766\n')
    url=f'http://127.0.0.1:{server.server_address[1]}'
    print(f'Virtual Solid Mechanics Lab → {url}\nKeep this terminal open. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser: threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nClosing lab. Waiting for any active experiment to finish…')
    finally: server.server_close();POOL.shutdown(wait=True)

if __name__=='__main__':main()

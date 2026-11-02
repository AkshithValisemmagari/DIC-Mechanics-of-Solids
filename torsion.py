"""Small-strain Saint-Venant torsion of a solid circular shaft (SI units)."""
import json
from pathlib import Path
import numpy as np


def build_torsion_config(data,E_gpa,nu,L,number,defaults,material_name):
    R=number(data,'radius_mm',.1,500)/1000
    T=number(data,'torque_nm',-1e6,1e6)
    if L/(2*R)<2: raise ValueError('Use a shaft length of at least four radii for the torsion model.')
    if not isinstance(data.get('compare_noise',False),bool): raise ValueError('compare_noise must be true or false.')
    if data.get('compare_noise',False): raise ValueError('Torsion is analytical only; noise comparison requires a flat DIC specimen.')
    E=E_gpa*1e9;G=E/(2*(1+nu));J=np.pi*R**4/2
    gamma=abs(T)*R/(G*J);theta=T*L/(G*J)
    if gamma>.02: raise ValueError('Predicted shear strain exceeds 2%. Reduce torque or increase radius/stiffness.')
    if abs(theta)>.35: raise ValueError('End twist exceeds 0.35 rad. Reduce torque for the small-twist analytical model.')
    return dict(benchmark='torsion',analysis_only=True,length_m=L,radius_m=R,torque_nm=T,
                material={'youngs_modulus_pa':E,'poisson_ratio':nu},
                user_inputs={**defaults,**data,'E_gpa':E_gpa,'nu':nu},
                load_description={'torque_nm':T,'material_name':material_name},
                warnings=['Analytical circular-shaft torsion only: no synthetic camera images or DIC recovery.',
                          'Uniform, isotropic, linearly elastic shaft. Local end effects, yielding and buckling are excluded.'])


def solve_torsion(config):
    L,R,T=config['length_m'],config['radius_m'],config['torque_nm']
    E=config['material']['youngs_modulus_pa'];nu=config['material']['poisson_ratio']
    G=E/(2*(1+nu));J=np.pi*R**4/2
    x=np.linspace(0,L,101);r=np.linspace(0,R,101)
    theta=T*x/(G*J);tau=T*r/J
    return dict(shear_modulus_pa=G,polar_moment_m4=J,twist_rate_rad_per_m=T/(G*J),
                end_twist_rad=float(theta[-1]),max_shear_pa=float(abs(tau[-1])),
                max_von_mises_pa=float(np.sqrt(3)*abs(tau[-1])),
                max_shear_strain=float(abs(tau[-1])/G),
                x_m=x.tolist(),twist_deg=np.degrees(theta).tolist(),
                r_m=r.tolist(),shear_mpa=(tau/1e6).tolist())


def run_torsion(config,run_id,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    answer=solve_torsion(config)
    payload=dict(run_id=run_id,config=config,analysis_only=True,torsion=answer,
                 bounds=[0,config['length_m'],-config['radius_m'],config['radius_m']])
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(answer,indent=2),encoding='utf-8')
    np.savetxt(out/'torsion_twist.csv',np.column_stack((answer['x_m'],answer['twist_deg'])),delimiter=',',header='x_m,twist_deg',comments='')
    np.savetxt(out/'torsion_stress.csv',np.column_stack((answer['r_m'],answer['shear_mpa'])),delimiter=',',header='radius_m,signed_shear_mpa',comments='')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    axes[0].plot(np.array(answer['x_m'])*1000,answer['twist_deg'],color='#086c58')
    axes[0].set(xlabel='Axial position (mm)',ylabel='Twist (degrees)',title='Analytical twist')
    axes[1].plot(np.array(answer['r_m'])*1000,answer['shear_mpa'],color='#ce6546')
    axes[1].set(xlabel='Radius (mm)',ylabel='Signed shear stress (MPa)',title='Radial stress distribution')
    for a in axes:a.grid(alpha=.2)
    fig.savefig(out/'torsion_analysis.png',dpi=150);plt.close(fig)
    import html
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Torsion report</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px}img{width:100%}pre{white-space:pre-wrap}</style><h1>Solid circular shaft: analytical torsion</h1><p>No DIC or camera-based measurement is performed. x is the shaft axis; positive torque rotates y toward z. Reference end: θ(0)=0.</p><p>G=E/[2(1+ν)], J=πR⁴/2, θ(x)=Tx/(GJ), τ(r)=Tr/J, σVM=√3|τ|. Curves use actual load, not visual magnification.</p><img src="torsion_analysis.png" alt="Analytical twist and radial shear stress"><pre>'+html.escape(json.dumps({k:v for k,v in answer.items() if not isinstance(v,list)},indent=2))+'</pre><p>'+html.escape(' '.join(config['warnings']))+'</p>',encoding='utf-8')
    return payload

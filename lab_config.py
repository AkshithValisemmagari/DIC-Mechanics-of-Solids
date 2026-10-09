"""Validated, user-facing experiment inputs and SI conversion."""
import numpy as np
from mechanics import Benchmark

MATERIALS = {
    'aluminium': {'name': 'Aluminium · illustrative', 'E_gpa': 70.0, 'nu': 0.33},
    'steel': {'name': 'Steel · illustrative', 'E_gpa': 200.0, 'nu': 0.30},
    'copper': {'name': 'Copper · illustrative', 'E_gpa': 110.0, 'nu': 0.34},
    'titanium': {'name': 'Titanium · illustrative', 'E_gpa': 110.0, 'nu': 0.34},
    'custom': {'name': 'Custom material', 'E_gpa': 70.0, 'nu': 0.30},
}
DEFAULTS = dict(benchmark='axial_bar', material='aluminium', E_gpa=70, nu=.33,
                length_mm=120, height_mm=40, thickness_mm=4, hole_radius_mm=10,
                force_n=40000, moment_nm=60, torque_nm=20, radius_mm=10, compare_noise=False, noise_std=0, blur_sigma=0, brightness_gain=1,
                subset_size=25, step=16, search_radius=12, fit_radius_px=36,
                speckle_radius_px=2.2, density=.4, seed=2039)


def number(data, key, low, high, integer=False):
    value = data.get(key, DEFAULTS[key])
    if isinstance(value, bool): raise ValueError(f'{key}: enter a number.')
    try: value = float(value)
    except (TypeError, ValueError): raise ValueError(f'{key}: enter a number.')
    if not np.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key}: must be between {low} and {high}.')
    if integer and not value.is_integer(): raise ValueError(f'{key}: must be an integer.')
    return int(value) if integer else value


def build_config(data):
    if not isinstance(data, dict): raise ValueError('Experiment inputs must be an object.')
    name=data.get('benchmark','axial_bar'); mat=data.get('material','aluminium')
    if name not in ('axial_bar','cantilever','plate_with_hole','pure_bending','torsion'): raise ValueError('Select a supported object.')
    if mat not in MATERIALS: raise ValueError('Select a supported material.')
    E=number(data,'E_gpa',.001,2000) if mat=='custom' else MATERIALS[mat]['E_gpa']
    nu=number(data,'nu',-.9,.49) if mat=='custom' else MATERIALS[mat]['nu']
    L=number(data,'length_mm',1,2000)/1000
    if name=='torsion':
        from torsion import build_torsion_config
        return build_torsion_config(data,E,nu,L,number,DEFAULTS,MATERIALS[mat]['name'])
    compare=data.get('compare_noise',False)
    if not isinstance(compare,bool): raise ValueError('compare_noise must be true or false.')
    H=number(data,'height_mm',1,2000)/1000
    t=number(data,'thickness_mm',.05,200)/1000
    if not .25 <= L/H <= 8: raise ValueError('Keep length/height between 0.25 and 8 for the camera view.')
    P=number(data,'force_n',0,2e7) if name!='pure_bending' else 0
    M=number(data,'moment_nm',-1e6,1e6) if name=='pure_bending' else 0
    a=number(data,'hole_radius_mm',.1,500)/1000 if name=='plate_with_hole' else 0
    if a and a >= min(L,H)*.38: raise ValueError('The hole radius must be less than 38% of the smaller plate dimension.')
    subset=number(data,'subset_size',17,41,True)
    if subset%2==0: raise ValueError('Subset size must be odd.')
    step=number(data,'step',8,32,True)
    radius=number(data,'fit_radius_px',20,100)
    if radius < 2.1*step: raise ValueError('Strain fit radius must be at least 2.1 times the grid spacing.')
    search=number(data,'search_radius',4,36,True)
    noise=number(data,'noise_std',0,.15);blur=number(data,'blur_sigma',0,2.5)
    if compare and noise<=0: raise ValueError('Select Gaussian noise above zero for a paired comparison.')
    gain=number(data,'brightness_gain',.5,1.4)
    seed=number(data,'seed',0,2147483647,True)
    shape=[max(160,min(448,int(round(384*H/L)))),384]
    c={'benchmark':name,'compare_noise':compare,'material':{'youngs_modulus_pa':E*1e9,'poisson_ratio':nu},
       'domain_m':[0,L,-H/2,H/2], 'remote_stress_pa':P/(H*t),
       'image':{'shape':shape,'speckle_radius_px':number(data,'speckle_radius_px',1,5),'density':number(data,'density',.15,.65),'seed':seed},
       'camera':{'noise_std':noise,'blur_sigma':blur,'brightness_gain':gain,'brightness_offset':0,'seed':seed+1},
       'dic':{'subset_size':subset,'step':step,'search_radius':search,'min_zncc':.75,'max_nfev':60,'gradient_bound':.12},
       'strain':{'fit_radius_px':radius},
       'user_inputs':{**DEFAULTS,**data,'E_gpa':E,'nu':nu},
       'load_description':{'force_n':P,'gross_area_m2':H*t,'material_name':MATERIALS[mat]['name']}}
    if name=='cantilever':
        c.pop('remote_stress_pa');c.update(length_m=L,height_m=H,thickness_m=t,force_n=P)
    elif name=='pure_bending':
        c.pop('remote_stress_pa');c.update(length_m=L,height_m=H,thickness_m=t,moment_nm=M)
        c['load_description']['moment_nm']=M
    elif name=='plate_with_hole':
        c['domain_m']=[-L/2,L/2,-H/2,H/2];c['hole_radius_m']=a
    warnings=[]
    if t/H > .2: warnings.append('Thickness is large relative to height. Plane stress may be a poor physical approximation.')
    if name=='cantilever': warnings.append('Saint-Venant end-loading model: local rigid-clamp effects are excluded.')
    if name=='plate_with_hole': warnings.append('Kirsch infinite-plate field shown in a finite observation window. Applied force is an equivalent nominal load, not a finite-plate boundary solution.')
    if name=='pure_bending': warnings.append('Equal and opposite end moments; constant internal moment and zero shear force. Reference motion removes rigid translation and rotation, not a rigid clamp.')
    warnings.append('Material presets are illustrative elastic constants; yielding and buckling are not modeled.')
    b=Benchmark(c)
    xx,yy=np.meshgrid(np.linspace(c['domain_m'][0],c['domain_m'][1],80),np.linspace(-H/2,H/2,80))
    m=b.material_mask(xx,yy);strain=np.stack(b.strain(xx,yy))
    if np.max(np.abs(strain[:,m])) > .02:
        raise ValueError('Predicted strain exceeds 2%. Reduce load or increase stiffness/dimensions for this small-strain lab.')
    u,v=b.displacement(xx,yy)
    max_px=float(max(np.max(np.abs(u[m]))/(L/(shape[1]-1)),np.max(np.abs(v[m]))/(H/(shape[0]-1))))
    if max_px > search-1:
        raise ValueError(f'Predicted motion is {max_px:.1f} px, beyond the selected search range. Increase Search radius or reduce load.')
    gx=np.gradient(u,L/79,axis=1);gy=np.gradient(u,H/79,axis=0)
    hx=np.gradient(v,L/79,axis=1);hy=np.gradient(v,H/79,axis=0)
    if max(np.max(np.abs(z[m])) for z in (gx,gy,hx,hy))>.08:
        raise ValueError('Deformation/rotation is too large for this local small-deformation solver. Reduce load.')
    if max_px < .1: warnings.append('Motion is below 0.1 pixel. Relative strain and stress errors may be large; increase load if appropriate.')
    c['warnings']=warnings
    return c

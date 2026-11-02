"""Square torsion experiment: generation, independent measurement, then validation."""
import csv
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image
from square_torsion import SquareTorsion
from stereo_camera import StereoRig, generate_images
from stereo_dic import reconstruct


def json_safe(value):
    if isinstance(value,np.ndarray):return json_safe(value.tolist())
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_safe(v) for v in value]
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer):return int(value)
    if isinstance(value,np.bool_):return bool(value)
    return value


def statistics(truth,measured):
    valid=np.isfinite(truth)&np.isfinite(measured);e=measured[valid]-truth[valid]
    return dict(n_valid=int(valid.sum()),rmse=float(np.sqrt(np.mean(e*e))) if len(e) else None,
                max_abs=float(np.max(abs(e))) if len(e) else None)


def run_stereo(config,run_id,directory,progress=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    model=SquareTorsion(config['length_m'],config['side_m'],config['material']['youngs_modulus_pa'],config['material']['poisson_ratio'],config['torque_nm'])
    rig=StereoRig(model.L,model.side)
    images,masks=generate_images(model,rig,config)
    for key,im in images.items():
        Image.fromarray(np.rint(im*255).astype('uint8')).save(directory/(key+'.png'))
        Image.fromarray((masks[key]*255).astype('uint8')).save(directory/(key+'_mask.png'))
    measured=reconstruct(images,masks,rig,config['dic'],config['strain']['fit_radius_px'],progress)
    matching_images=measured.pop('matching_images')
    preprocessing=measured['preprocessing']
    if preprocessing['kernel_radius_px']:
        for key,im in matching_images.items():
            # PNG is a display copy; DIC above used the full floating-point array.
            Image.fromarray(np.rint(np.clip(im,0,1)*65535).astype('uint16')).save(directory/(key+'_smoothed.png'))
        np.savez_compressed(directory/'dic_input_images.npz',**matching_images)
    # Validation begins ONLY after reconstruction. No model or true coordinates
    # have been supplied to reconstruct(). Anchors are reference-image pixels.
    xy=rig.reference_xy(measured['centres_px']);reference=np.column_stack((xy,np.full(len(xy),model.a)))
    true_displacement=model.position(xy[:,0],xy[:,1],model.a)-reference
    true_strain=model.face_strain(*xy.T)
    fields={}
    for j,(key,label) in enumerate([('u','Axial displacement u'),('v','Transverse displacement v'),('w','Depth displacement w')]):
        fields[key]=dict(label=label,unit='mm',truth=true_displacement[:,j]*1000,measured=measured['displacement_m'][:,j]*1000)
    fields['magnitude']=dict(label='Displacement magnitude',unit='mm',truth=np.linalg.norm(true_displacement,axis=1)*1000,measured=np.linalg.norm(measured['displacement_m'],axis=1)*1000)
    for j,(key,label) in enumerate([('exx','Surface strain Eₓₓ'),('eyy','Surface strain Eᵧᵧ'),('gamma','Surface shear 2Eₓᵧ')]):
        fields[key]=dict(label=label,unit='με',truth=true_strain[:,j]*1e6,measured=measured['strain'][:,j]*1e6)
    for field in fields.values():field['statistics']=statistics(field['truth'],field['measured'])
    valid=measured['valid'];err=(measured['displacement_m']-true_displacement)[valid]*1000
    summary=dict(candidate_subsets=len(valid),valid_displacement_subsets=int(valid.sum()),
        valid_strain_subsets=int(np.isfinite(measured['strain']).all(axis=1).sum()),
        displacement_vector_rmse_mm=float(np.sqrt(np.mean(np.sum(err*err,axis=1)))) if len(err) else None,
        displacement_component_rmse_mm=np.sqrt(np.mean(err*err,axis=0)) if len(err) else [None]*3,
        max_true_displacement_mm=float(np.linalg.norm(true_displacement,axis=1).max()*1000),
        status_counts=measured['status_counts'],thresholds=measured['thresholds'],preprocessing=preprocessing)
    warnings=list(config['warnings'])
    if summary['valid_strain_subsets']==0:warnings.append('No well-conditioned surface-strain fits. Use smaller grid spacing/subsets or a larger fit radius; no strain values have been fabricated.')
    if valid.sum()<.8*len(valid):warnings.append('Fewer than 80% of candidate points passed stereo checks. Inspect rejected points and quality metrics; low error on survivors does not imply full coverage.')
    payload=dict(stereo=True,run_id=run_id,asset_prefix=f'/runs/{run_id}/',config={**config,'warnings':warnings},
        bounds=[0,model.L,-model.a,model.a],torsion=model.summary(),square_solid=model.solid(),
        summary=summary,calibration=rig.metadata(),stereo_result=measured,fields=fields,x_m=xy[:,0],y_m=xy[:,1])
    payload=json_safe(payload)
    for filename,data in [('config.json',config),('summary.json',summary),('camera_calibration.json',rig.metadata())]:
        (directory/filename).write_text(json.dumps(json_safe(data),indent=2,allow_nan=False),encoding='utf-8')
    with (directory/'stereo_fields.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);keys=list(fields)
        writer.writerow(['x_m','y_m','valid_displacement','status']+[f'{k}_{kind}_{fields[k]["unit"]}' for k in keys for kind in ['truth','measured','error']])
        for i in range(len(xy)):
            values=[]
            for key in keys:
                t=fields[key]['truth'][i];v=fields[key]['measured'][i]
                values.extend([t,v if np.isfinite(v) else '',v-t if np.isfinite(v) else ''])
            writer.writerow([*xy[i],int(valid[i]),measured['status'][i],*values])
    with (directory/'stereo_correspondences.csv').open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['status']+[f'{k}_{a}_px' for k in ['L0','R0','L1','R1'] for a in ['column','row']]+['min_zncc','cycle_px','epipolar_px','reprojection_px']+[f'{state}_{axis}_m' for state in ['reference','deformed'] for axis in 'xyz'])
        for i in range(len(xy)):
            row=np.r_[measured['coordinates_px'][i].ravel(),measured['quality'][i],measured['reference_m'][i],measured['deformed_m'][i]]
            writer.writerow([measured['status'][i],*[v if np.isfinite(v) else '' for v in row]])
    rows=''.join(f'<tr><td>{html.escape(f["label"])}</td><td>{f["statistics"]["n_valid"]}</td><td>{f["statistics"]["rmse"]}</td><td>{f["unit"]}</td></tr>' for f in payload['fields'].values())
    pictures=''.join(f'<figure><figcaption>{k.replace("_"," ").title()}</figcaption><img src="{k}.png"></figure>' for k in images)
    filter_label=('Local Wiener (5 x 5 px)' if preprocessing['method']=='wiener' else f"Gaussian (sigma {preprocessing['sigma_px']} px)")
    preprocessing_note=(f'DIC denoising: {filter_label}, applied after capture to all four images. DIC uses floating-point filtered values; smoothed PNGs are 16-bit preview copies. Exact filtered arrays are in dic_input_images.npz. Original camera images are preserved.'
                        if preprocessing['kernel_radius_px'] else 'DIC denoising: Off. Matching uses the original captured images.')
    if preprocessing['kernel_radius_px']:
        pictures+=''.join(f'<figure><figcaption>{k.replace("_"," ").title()} · smoothed DIC input</figcaption><img src="{k}_smoothed.png"></figure>' for k in images)
    report=f'''<!doctype html><meta charset="utf-8"><title>Square torsion · stereo DIC</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#173b38}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}.images{{display:grid;grid-template-columns:1fr 1fr}}img{{width:100%}}pre{{white-space:pre-wrap}}</style><h1>Square torsion · stereo DIC</h1><p>Independent image matching → calibrated 3D reconstruction → surface strain → ground-truth validation.</p><p>Accepted {summary['valid_displacement_subsets']} / {len(valid)} candidate subsets. Vector displacement RMSE: {summary['displacement_vector_rmse_mm']} mm.</p><table><tr><th>Field</th><th>Valid points</th><th>RMSE</th><th>Unit</th></tr>{rows}</table><p>{preprocessing_note}</p><div class="images">{pictures}</div><h2>Model and measurement limits</h2><ul>{''.join('<li>'+html.escape(w)+'</li>' for w in warnings)}</ul><p>Affine subset correlation, independent stereo/temporal cycles, epipolar and reprojection checks, then local quadratic fitting of reference and deformed surfaces. Strains use Green–Lagrange surface metrics; a rigid rotation produces zero strain. Fit windows trade spatial resolution for noise suppression. Stress is analytical, not recovered from a single surface.</p><h2>Reproduce this run</h2><pre>{html.escape(json.dumps(json_safe(config),indent=2))}</pre><h2>Quality statistics</h2><pre>{html.escape(json.dumps(json_safe(summary),indent=2))}</pre>'''
    (directory/'report.html').write_text(report)
    return payload

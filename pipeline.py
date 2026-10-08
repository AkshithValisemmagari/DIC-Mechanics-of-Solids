"""End-to-end experiment orchestration and reproducible outputs."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from mechanics import Benchmark
from speckle import synthetic_pair, degrade_pair, save_image
from dic import run_dic, DIC_COLUMNS
from strain import recover_strain
from stress import plane_stress, invariants
from validation import summarize
from visualization import plot_experiment, write_report


def run_experiment(config, output_dir=None, make_plots=True):
    model = Benchmark(config)
    ref, deformed, mr, md, truth = synthetic_pair(model, config)
    camera = config.get('camera', {})
    ref, deformed = degrade_pair(ref, deformed, **camera)
    # Blurring can mix material/background at boundaries; exclude its footprint.
    erosion = int(np.ceil(3*camera.get('blur_sigma', 0)))
    if erosion:
        mr = binary_erosion(mr, iterations=erosion)
        md = binary_erosion(md, iterations=erosion)
    dic = run_dic(ref, deformed, mr, md, **config['dic'])
    xmin, xmax, ymin, ymax = model.bounds
    sx, sy = truth['sx'], truth['sy']
    x, y = xmin+dic[:, 0]*sx, ymax-dic[:, 1]*sy
    u, v = model.displacement(x, y)
    true_disp = np.column_stack((u/sx, -v/sy))
    true_strain = np.column_stack(model.strain(x, y))
    true_stress = np.column_stack(model.stress(x, y))
    in_material = model.material_mask(x, y)
    true_disp[~in_material] = np.nan
    true_strain[~in_material] = np.nan
    true_stress[~in_material] = np.nan
    hole_center = np.array([-xmin/sx, ymax/sy]) if model.hole_radius else None
    strain = recover_strain(dic, sx, sy, config['strain']['fit_radius_px'], hole_center, model.hole_radius/sx)
    stress = plane_stress(strain, model.E, model.nu)
    derived = invariants(stress)
    summary = summarize(dic, true_disp, strain, true_strain, stress, true_stress)
    summary['benchmark'] = model.name
    summary['pixel_size_m'] = [sx, sy]
    summary['max_ground_truth_displacement_px'] = float(np.nanmax(np.linalg.norm(true_disp, axis=1)))
    summary['stress_component_order'] = ['sigma_xx', 'sigma_yy', 'tau_xy']
    summary['strain_component_order'] = ['epsilon_xx', 'epsilon_yy', 'engineering_gamma_xy']
    if model.hole_radius:
        # Sampled interior maximum is NOT a recovered hole-edge Kt.
        valid = np.all(np.isfinite(stress), axis=1)
        S = config['remote_stress_pa']
        summary['hole_concentration'] = {
            'analytical_edge_Kt': 3.0,
            'analytical_sampled_sigma_xx_ratio': float(np.max(true_stress[valid, 0]/S)) if valid.any() and S != 0 else None,
            'dic_sampled_sigma_xx_ratio': float(np.max(stress[valid, 0]/S)) if valid.any() and S != 0 else None,
            'note': 'Subset centres do not reach the hole edge. Sampled ratios are not edge Kt estimates.'}
    bundle = dict(config=config, reference=ref, deformed=deformed, mask_reference=mr,
                  mask_deformed=md, dic=dic, x=x, y=y, true_disp=true_disp,
                  strain=strain, stress=stress, true_strain=true_strain,
                  true_stress=true_stress, invariants=derived, summary=summary)
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out/'config.json').write_text(json.dumps(config, indent=2)+'\n')
        (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
        save_image(out/'reference.png', ref); save_image(out/'deformed.png', deformed)
        save_image(out/'reference_mask.png', mr); save_image(out/'deformed_mask.png', md)
        np.savez_compressed(out/'ground_truth.npz', **truth, reference_support_mask=mr)
        np.savetxt(out/'dic_displacements.csv', dic, delimiter=',', header=DIC_COLUMNS, comments='')
        measured_m = dic[:, 2:4]*[sx, -sy]
        measured_m[~dic[:, 9].astype(bool)] = np.nan
        true_m = true_disp*[sx, -sy]
        table = np.column_stack((x, y, dic[:, 9], measured_m, true_m, strain, true_strain, stress, true_stress, derived))
        np.savetxt(out/'mechanical_fields.csv', table, delimiter=',', comments='',
                   header='x_m,y_m,valid_dic,u_m,v_m,true_u_m,true_v_m,exx,eyy,gamma_xy,true_exx,true_eyy,true_gamma_xy,sxx_pa,syy_pa,txy_pa,true_sxx_pa,true_syy_pa,true_txy_pa,inplane_s1_pa,inplane_s2_pa,von_mises_pa')
        errors = np.column_stack((x, y, dic[:, 2:4]-true_disp, strain-true_strain, stress-true_stress))
        errors[~dic[:, 9].astype(bool), 2:] = np.nan
        np.savetxt(out/'errors.csv', errors, delimiter=',', comments='',
                   header='x_m,y_m,error_u_px,error_v_px,error_exx,error_eyy,error_gamma_xy,error_sxx_pa,error_syy_pa,error_txy_pa')
        if make_plots:
            plot_experiment(bundle, out)
            write_report(bundle, out)
    return bundle

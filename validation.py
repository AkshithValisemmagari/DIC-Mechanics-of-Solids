"""Comparison only: analytical information is never passed to DIC."""
import numpy as np


def field_errors(measured, truth, valid):
    measured = np.asarray(measured)
    truth = np.asarray(truth)
    valid = (np.asarray(valid, bool)
             & np.all(np.isfinite(measured), axis=1)
             & np.all(np.isfinite(truth), axis=1))
    if not valid.any():
        return {'n_valid': 0, 'component_rmse': None, 'vector_rmse': None, 'max_vector_error': None}
    e = measured[valid]-truth[valid]
    return {'n_valid': int(valid.sum()), 'component_rmse': np.sqrt(np.mean(e*e, axis=0)).tolist(),
            'vector_rmse': float(np.sqrt(np.mean(np.sum(e*e, axis=1)))),
            'max_vector_error': float(np.max(np.linalg.norm(e, axis=1)))}


def summarize(dic, displacement_truth_px, recovered_strain, strain_truth, recovered_stress, stress_truth):
    valid = dic[:, 9].astype(bool)
    eligible = dic[:, -1] != 1
    count = int(eligible.sum())
    return {'candidate_subsets': len(dic), 'eligible_reference_subsets': count,
            'valid_displacement_subsets': int(valid.sum()),
            'coverage_fraction': float(valid.mean()),
            'eligible_match_coverage_fraction': float(valid.sum()/count) if count else None,
            'eligible_match_failure_fraction': float(1-valid.sum()/count) if count else None,
            'status_counts': {str(int(i)): int((dic[:, -1] == i).sum()) for i in np.unique(dic[:, -1])},
            'displacement_px': field_errors(dic[:, 2:4], displacement_truth_px, valid),
            'strain': field_errors(recovered_strain, strain_truth, valid),
            'stress_pa': field_errors(recovered_stress, stress_truth, valid)}

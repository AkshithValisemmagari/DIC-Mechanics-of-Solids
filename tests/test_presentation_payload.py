"""Presentation metadata/progress must leave all numerical results unchanged."""
import unittest
import numpy as np
from lab_config import build_config
from pipeline import run_experiment
from lab_server import make_payload, BUILD_INFO


class PresentationPayloadTests(unittest.TestCase):
    def test_progress_observer_preserves_every_numeric_result(self):
        config=build_config(dict(benchmark='axial_bar',noise_std=.02,denoise_sigma=1,step=24,fit_radius_px=55))
        config['image']['shape']=[100,140]
        baseline=run_experiment(config,make_plots=False)
        stages=[]
        observed=run_experiment(config,make_plots=False,progress=stages.append)
        for field in ['reference','deformed','dic','strain','stress','true_disp','true_strain','true_stress','invariants']:
            np.testing.assert_array_equal(observed[field],baseline[field],err_msg=field)
        self.assertEqual(observed['summary'],baseline['summary'])
        self.assertEqual(stages[0],'Generating synthetic camera images…')
        self.assertTrue(any('verifying reverse matches' in value for value in stages))
        self.assertTrue(any('Recovering strain and stress' in value for value in stages))

    def test_payload_exposes_existing_reverse_diagnostics(self):
        config=build_config(dict(benchmark='axial_bar',force_n=0,step=24,fit_radius_px=55))
        config['image']['shape']=[100,140]
        bundle=run_experiment(config,make_plots=False)
        original=bundle['dic'].copy();payload=make_payload(bundle,'presentation-check')
        self.assertEqual(payload['consistency']['tolerance_px'],.3)
        self.assertEqual(len(payload['consistency']['points']),len(bundle['dic']))
        for actual,expected in zip(payload['consistency']['points'],bundle['consistency']['points']):
            self.assertEqual(actual['reverse_status'],expected['reverse_status'])
            for key in ['round_trip_error_px','reverse_zncc']:
                self.assertEqual(actual[key],expected[key] if np.isfinite(expected[key]) else None)
        np.testing.assert_array_equal(bundle['dic'],original)
        self.assertTrue(BUILD_INFO['version']);self.assertTrue(BUILD_INFO['revision'])


if __name__=='__main__':unittest.main()

"""Interactive configuration and methods-review regression tests."""
import unittest
import numpy as np
from lab_config import build_config
from mechanics import Benchmark
from pipeline import run_experiment
from lab_server import make_payload, clean_json
from validation import field_errors, summarize
import json


class LabConfigurationTests(unittest.TestCase):
    def test_force_to_stress_and_material_preset(self):
        c=build_config(dict(material='steel',force_n=1000,length_mm=120,height_mm=40,thickness_mm=4,E_gpa=7))
        self.assertEqual(c['material']['youngs_modulus_pa'],200e9)
        self.assertAlmostEqual(c['remote_stress_pa'],1000/(.04*.004))

    def test_custom_material_and_beam_load(self):
        c=build_config(dict(benchmark='cantilever',material='custom',E_gpa=100,nu=.27,force_n=500))
        self.assertEqual(c['force_n'],500)
        self.assertNotIn('remote_stress_pa',c)
        self.assertEqual(c['material']['youngs_modulus_pa'],100e9)

    def test_invalid_inputs_rejected(self):
        cases=[dict(force_n=float('nan')),dict(hole_radius_mm=39,benchmark='plate_with_hole',length_mm=80,height_mm=80),dict(subset_size=20),dict(material='unknown'),dict(length_mm=0),dict(material='custom',nu=.5),dict(force_n=2e7),dict(step=32,fit_radius_px=36)]
        for data in cases:
            with self.subTest(data=data),self.assertRaises(ValueError):build_config(data)

    def test_zero_force_hole_and_non_square_pixels(self):
        c=build_config(dict(benchmark='plate_with_hole',force_n=0,length_mm=100,height_mm=60,hole_radius_mm=8))
        c['image']['shape']=[120,180]
        c['dic'].update(step=20,search_radius=4,subset_size=17)
        c['strain']['fit_radius_px']=45
        b=run_experiment(c,make_plots=False)
        self.assertIsNone(b['summary']['hole_concentration']['dic_sampled_sigma_xx_ratio'])
        self.assertLess(b['summary']['displacement_px']['vector_rmse'],1e-5)
        self.assertGreater(b['summary']['strain']['n_valid'],0)
        payload=make_payload(b,'test')
        json.dumps(payload,allow_nan=False)

    def test_rectangle_hole_physics_still_matches(self):
        c=build_config(dict(benchmark='plate_with_hole',length_mm=100,height_mm=60,hole_radius_mm=8,force_n=3000))
        b=Benchmark(c);x=np.array([.018,.025]);y=np.array([.012,-.02]);h=1e-7
        up,vp=b.displacement(x+h,y);um,vm=b.displacement(x-h,y)
        np.testing.assert_allclose((up-um)/(2*h),b.strain(x,y)[0],rtol=1e-7)

    def test_benchmark_rejects_non_finite_geometry(self):
        hole=build_config(dict(benchmark='plate_with_hole'))
        hole['hole_radius_m']=float('nan')
        with self.assertRaisesRegex(ValueError,'hole_radius_m'):
            Benchmark(hole)
        beam=build_config(dict(benchmark='cantilever',force_n=1000))
        beam['thickness_m']=float('inf')
        with self.assertRaisesRegex(ValueError,'Beam dimensions'):
            Benchmark(beam)

    def test_validation_excludes_non_finite_truth_and_reports_eligible_coverage(self):
        errors=field_errors([[1,2],[3,4]],[[1,2],[float('nan'),4]],[True,True])
        self.assertEqual(errors['n_valid'],1)
        self.assertEqual(errors['vector_rmse'],0)

        dic=np.zeros((3,11));dic[:,9]=[1,0,0];dic[:,10]=[0,1,4]
        fields=np.zeros((3,3))
        summary=summarize(dic,np.zeros((3,2)),fields,fields,fields,fields)
        self.assertAlmostEqual(summary['coverage_fraction'],1/3)
        self.assertAlmostEqual(summary['eligible_match_coverage_fraction'],1/2)
        self.assertAlmostEqual(summary['eligible_match_failure_fraction'],1/2)

    def test_non_finite_json_becomes_null(self):
        self.assertEqual(clean_json(np.array([1,np.nan,np.inf])),[1,None,None])

if __name__=='__main__':unittest.main()

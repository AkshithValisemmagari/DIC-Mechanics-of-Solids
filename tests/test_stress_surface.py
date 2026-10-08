"""Stress-colour data comes directly from the existing analytical solution."""
import unittest
import numpy as np
from lab_config import build_config
from mechanics import Benchmark
from lab_server import stress_surface


class StressSurfaceTests(unittest.TestCase):
    def test_bar_uniform_von_mises(self):
        model=Benchmark(build_config(dict(benchmark='axial_bar',force_n=1000)))
        values=stress_surface(model)
        self.assertEqual(values.shape,(29*49,4))
        np.testing.assert_allclose(values[:,0],model.c['remote_stress_pa']/1e6)
        np.testing.assert_allclose(values[:,3],values[:,0])
        np.testing.assert_allclose(values[:,1:3],0)

    def test_beam_values_and_vertex_order(self):
        model=Benchmark(build_config(dict(benchmark='cantilever',force_n=500)))
        x,y=np.meshgrid(np.linspace(model.bounds[0],model.bounds[1],49),
                        np.linspace(model.bounds[2],model.bounds[3],29))
        expected=np.column_stack([v.ravel() for v in model.stress(x,y)])/1e6
        np.testing.assert_allclose(stress_surface(model)[:,:3],expected)

    def test_hole_boundary_peak_is_three_times_nominal(self):
        model=Benchmark(build_config(dict(benchmark='plate_with_hole',force_n=3000,length_mm=100,height_mm=60)))
        values=stress_surface(model)
        self.assertEqual(values.shape,(15*100,4))
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertAlmostEqual(values[:,3].max(),3*model.c['remote_stress_pa']/1e6)

    def test_zero_load_all_objects(self):
        for name in ('axial_bar','cantilever','plate_with_hole'):
            model=Benchmark(build_config(dict(benchmark=name,force_n=0)))
            np.testing.assert_array_equal(stress_surface(model),0)

if __name__=='__main__':unittest.main()

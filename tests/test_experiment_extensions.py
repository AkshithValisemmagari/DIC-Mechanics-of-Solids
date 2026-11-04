"""Independent mechanics and common-centre validation for added experiments."""
import copy
import unittest
import numpy as np
from lab_config import build_config
from mechanics import Benchmark
from torsion import solve_torsion
from noise_comparison import compare_payloads

def trapezoid(y, x, **kwargs):
    integrate = getattr(np, 'trapezoid', None)
    if integrate is None:
        integrate = getattr(np, 'trapz')
    return integrate(y, x, **kwargs)


class NewMechanicsTests(unittest.TestCase):
    def test_pure_bending_kinematics_and_resultants(self):
        for moment in (60, -60, 0):
            c=build_config(dict(benchmark='pure_bending',length_mm=120,height_mm=30,thickness_mm=6,moment_nm=moment))
            b=Benchmark(c);x=np.array([.02,.06,.1]);y=np.array([-.01,0,.01]);delta=1e-7
            up,vp=b.displacement(x+delta,y);um,vm=b.displacement(x-delta,y)
            uq,vq=b.displacement(x,y+delta);un,vn=b.displacement(x,y-delta)
            measured=((up-um)/(2*delta),(vq-vn)/(2*delta),(uq-un+vp-vm)/(2*delta))
            np.testing.assert_allclose(measured,b.strain(x,y),atol=1e-12)
            y=np.linspace(-b.h/2,b.h/2,10001);sx,sy,tau=b.stress(0,y)
            self.assertAlmostEqual(float(trapezoid(sx,y)*c['thickness_m']),0,places=8)
            self.assertAlmostEqual(float(-trapezoid(y*sx,y)*c['thickness_m']),moment,places=5)
            np.testing.assert_array_equal(sy,0);np.testing.assert_array_equal(tau,0)
            np.testing.assert_allclose(b.displacement(np.array([0,b.L]),0)[1],0,atol=1e-15)

    def test_torsion_equilibrium_and_kinematics(self):
        for torque in (20,-20,0):
            c=build_config(dict(benchmark='torsion',length_mm=200,radius_mm=10,torque_nm=torque,material='steel'))
            t=solve_torsion(c);G=200e9/2.6;R=.01;J=np.pi*R**4/2
            self.assertAlmostEqual(t['end_twist_rad'],torque*.2/(G*J),places=14)
            self.assertAlmostEqual(t['max_shear_pa'],abs(torque)*R/J,places=7)
            np.testing.assert_allclose(np.gradient(np.radians(t['twist_deg']),t['x_m']),torque/(G*J),atol=1e-12)
            r=np.linspace(0,R,10001);tau=torque*r/J
            self.assertAlmostEqual(float(trapezoid(tau*2*np.pi*r*r,r)),torque,places=5)
            self.assertAlmostEqual(t['max_von_mises_pa'],np.sqrt(3)*t['max_shear_pa'])

    def test_invalid_extension_inputs(self):
        for data in [dict(benchmark='torsion',torque_nm=float('nan')),dict(benchmark='torsion',radius_mm=0),dict(benchmark='torsion',length_mm=10,radius_mm=10),dict(benchmark='torsion',torque_nm=1e6),dict(benchmark='torsion',compare_noise=True),dict(benchmark='pure_bending',moment_nm=float('inf')),dict(compare_noise=True,noise_std=0),dict(compare_noise='yes')]:
            with self.subTest(data=data),self.assertRaises(ValueError):build_config(data)

    def test_noise_common_centres_exclude_rejections_and_missing_values(self):
        base=dict(dic=[[i,0,0,0,0,0,0,0,1,1] for i in range(4)],fields={'u':dict(truth=[1,2,3,4],measured=[1,2.5,None,40],label='u',unit='mm')})
        noisy=copy.deepcopy(base);noisy['fields']['u']['measured']=[2,2,3,4];noisy['dic'][3][9]=0
        c=compare_payloads(base,noisy)['u']
        self.assertEqual((c['common_count'],c['baseline_valid'],c['noisy_valid']),(2,3,3))
        self.assertAlmostEqual(c['baseline']['rmse'],np.sqrt(.25/2));self.assertAlmostEqual(c['noisy']['rmse'],np.sqrt(.5))
        self.assertEqual(c['baseline']['max_abs'],.5)
        for d in noisy['dic']:d[9]=0
        c=compare_payloads(base,noisy)['u'];self.assertEqual(c['common_count'],0);self.assertIsNone(c['noisy']['rmse'])
        noisy['dic'][0][0]=99
        with self.assertRaises(ValueError):compare_payloads(base,noisy)

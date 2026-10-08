import copy
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.ndimage import shift
from mechanics import Benchmark
from speckle import generate_speckles, degrade_pair, synthetic_pair
from dic import run_dic
from strain import recover_strain
from stress import plane_stress, invariants

ROOT=Path(__file__).resolve().parents[1]


class PhysicsTests(unittest.TestCase):
    def test_displacement_derivatives_match_independent_stress_formulas(self):
        for name in ['axial_bar_dic','cantilever','plate_with_hole']:
            b=Benchmark(json.loads((ROOT/'configs'/f'{name}.json').read_text()))
            x=np.array([.022,.026,.031]);y=np.array([.011,-.012,.019]);h=1e-7
            ux,vx=b.displacement(x+h,y);um,vm=b.displacement(x-h,y)
            uy,vy=b.displacement(x,y+h);un,vn=b.displacement(x,y-h)
            e=np.column_stack(((ux-um)/(2*h),(vy-vn)/(2*h),(uy-un+vx-vm)/(2*h)))
            truth=np.column_stack(b.stress(x,y))
            np.testing.assert_allclose(plane_stress(e,b.E,b.nu),truth,rtol=1e-7,atol=.1,err_msg=name)

    def test_hole_free_traction_and_edge_peak(self):
        b=Benchmark(json.loads((ROOT/'configs/plate_with_hole.json').read_text()))
        theta=np.linspace(0,2*np.pi,65);c=np.cos(theta);s=np.sin(theta)
        sx,sy,t=b.stress(b.hole_radius*c,b.hole_radius*s)
        np.testing.assert_allclose(sx*c+t*s,0,atol=1e-6)
        np.testing.assert_allclose(t*c+sy*s,0,atol=1e-6)
        hoop=sx*s*s+sy*c*c-2*t*s*c
        self.assertAlmostEqual(hoop.max()/b.c['remote_stress_pa'],3)

    def test_beam_resultant_and_free_surfaces(self):
        b=Benchmark(json.loads((ROOT/'configs/cantilever.json').read_text()))
        y=np.linspace(-b.h/2,b.h/2,1001)
        sx,sy,t=b.stress(np.zeros_like(y),y)
        # Trapezoidal integration is deliberately independent of displacement.
        integrate=getattr(np,'trapezoid',None)
        if integrate is None: integrate=np.trapz
        self.assertAlmostEqual(integrate(t,y)*b.c['thickness_m']/b.c['force_n'],1,places=5)
        self.assertAlmostEqual(integrate(sx*y,y)*b.c['thickness_m']/(-b.c['force_n']*b.L),1,places=5)
        np.testing.assert_allclose(t[[0,-1]],0,atol=1e-8)

    def test_plane_stress_invariants(self):
        np.testing.assert_allclose(invariants([[100,0,0]]),[[100,0,100]])
        np.testing.assert_allclose(invariants([[0,0,10]]),[[10,-10,np.sqrt(3)*10]])


class ImageAndDICTests(unittest.TestCase):
    def test_hole_inverse_map_and_mask(self):
        c=json.loads((ROOT/'configs/plate_with_hole.json').read_text())
        c['image']['shape']=[100,100]
        b=Benchmark(c)
        ref,deformed,mr,md,t=synthetic_pair(b,c)
        self.assertTrue(np.all(np.isfinite(deformed)))
        self.assertFalse(mr[50,50])
        self.assertFalse(md[50,50])
        self.assertGreater(md.mean(),.7)

    def test_subpixel_translation_and_brightness(self):
        image=generate_speckles((100,120),2,0.4,4)
        deformed=shift(image,shift=(-1.35,2.37),order=3,mode='constant',cval=.5)
        ref,deformed=degrade_pair(image,deformed,brightness_gain=.85,brightness_offset=.05)
        d=run_dic(ref,deformed,subset_size=21,step=20,search_radius=5)
        good=d[:,9].astype(bool)
        self.assertGreater(good.mean(),.9)
        error=d[good,2:4]-[2.37,-1.35]
        self.assertLess(np.sqrt(np.mean(np.sum(error**2,axis=1))),.06)

    def test_flat_image_rejected(self):
        d=run_dic(np.ones((80,80)),np.ones((80,80)),step=20)
        self.assertFalse(d[:,9].any())
        self.assertTrue(np.all(d[:,-1]==2))

    def test_independent_noise_and_reproducibility(self):
        a=np.ones((50,50))*.5
        p=degrade_pair(a,a,noise_std=.02,seed=8)
        q=degrade_pair(a,a,noise_std=.02,seed=8)
        np.testing.assert_array_equal(p[0],q[0])
        self.assertFalse(np.array_equal(p[0],p[1]))

    def test_strain_units_and_image_y_sign(self):
        x,y=np.meshgrid(np.arange(0,100,10),np.arange(0,100,10))
        d=np.zeros((x.size,11));d[:,0]=x.ravel();d[:,1]=y.ravel();d[:,9]=1
        # Physical u=0.01*x+0.02*y, v=0.03*x-0.004*y;
        # sx=2, sy=3; image v sign is opposite physical v.
        d[:,2]=.01*d[:,0]-.02*3/2*d[:,1]
        d[:,3]=-.03*2/3*d[:,0]-.004*d[:,1]
        e=recover_strain(d,2,3,25)
        good=np.all(np.isfinite(e),axis=1)
        self.assertGreater(good.sum(),80)
        np.testing.assert_allclose(e[good],np.tile([.01,-.004,.05],(good.sum(),1)),atol=1e-12)

    def test_affine_axial_recovery(self):
        c=json.loads((ROOT/'configs/axial_bar_dic.json').read_text())
        c['image']['shape']=[100,140]
        b=Benchmark(c);ref,deformed,mr,md,t=synthetic_pair(b,c)
        ref,deformed=degrade_pair(ref,deformed)
        d=run_dic(ref,deformed,mr,md,subset_size=21,step=20,search_radius=4)
        good=d[:,9].astype(bool)
        xmin,_,_,ymax=b.bounds
        u,v=b.displacement(xmin+d[:,0]*t['sx'],ymax-d[:,1]*t['sy'])
        truth=np.column_stack((u/t['sx'],-v/t['sy']))
        self.assertGreater(good.mean(),.8)
        self.assertLess(np.sqrt(np.mean(np.sum((d[good,2:4]-truth[good])**2,axis=1))),.06)


if __name__=='__main__':unittest.main()

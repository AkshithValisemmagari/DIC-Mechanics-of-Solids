"""Physics, independent camera reconstruction, and rigid-motion invariance."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from lab_config import build_config
from square_torsion import SquareTorsion
from stereo_camera import StereoRig, generate_images
from stereo_dic import reconstruct, surface_strain
from stereo_experiment import run_stereo


class SquareMechanicsTests(unittest.TestCase):
    def test_torque_resultant_warping_and_boundary(self):
        m=SquareTorsion(.16,.02,70e9,.33,100)
        self.assertAlmostEqual(m.J/m.side**4,.140577,places=6)
        y,z=np.meshgrid(np.linspace(-m.a,m.a,301),np.linspace(-m.a,m.a,301));t1,t2=m.stress(y,z)
        integrate=getattr(np,'trapezoid',np.trapz)
        torque=integrate(integrate(y*t2-z*t1,y[0],axis=1),z[:,0])
        self.assertLess(abs(torque-100),.01)
        q=np.linspace(-.009,.009,101)
        self.assertLess(abs(m.stress(m.a,q)[0]).max()/m.summary()['max_shear_pa'],.001)
        self.assertLess(abs(m.stress(q,m.a)[1]).max(),1e-6)
        x=np.array([.02,.08,.14]);y=np.array([-.006,.001,.005]);h=1e-7
        pos,tx,ty=m.face(x,y)
        np.testing.assert_allclose((m.face(x+h,y)[0]-m.face(x-h,y)[0])/(2*h),tx,atol=1e-9)
        np.testing.assert_allclose((m.face(x,y+h)[0]-m.face(x,y-h)[0])/(2*h),ty,atol=2e-8)
        self.assertGreater(np.max(abs(pos[:,0]-x)),1e-7)

    def test_middle_reference_preserves_stress_strain_and_total_twist(self):
        for torque in (100,-100,0):
            m=SquareTorsion(.16,.02,70e9,.33,torque)
            x=np.array([0,m.L/2,m.L]);y=np.full(3,.006);z=np.full(3,.003)
            for phase in (0,.5,1):
                p=m.position(x,y,z,phase)
                angle=np.arctan2(p[:,2],p[:,1])-np.arctan2(z,y)
                expected=m.rate*phase*(x-m.L/2)
                np.testing.assert_allclose(angle,expected,atol=1e-14)
                np.testing.assert_allclose(p[1,1:],[y[1],z[1]],atol=1e-15)
                self.assertAlmostEqual(angle[2]-angle[0],m.rate*m.L*phase)
            # Changing only the rotational datum is a rigid rotation about x.
            x=np.linspace(.01,.15,13);y=np.linspace(-.008,.008,13)
            p,tx,ty=m.face(x,y);strain=m.face_strain(x,y);stress=m.stress(y,m.a)
            m.rotation_reference=0
            q,qx,qy=m.face(x,y);a=-m.rate*m.L/2
            R=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
            np.testing.assert_allclose(p,q@R.T,atol=1e-15)
            np.testing.assert_allclose(tx,qx@R.T,atol=1e-15)
            np.testing.assert_allclose(ty,qy@R.T,atol=1e-15)
            np.testing.assert_allclose(strain,m.face_strain(x,y),atol=1e-14)
            np.testing.assert_allclose(stress,m.stress(y,m.a),atol=1e-10)
            t=SquareTorsion(.16,.02,70e9,.33,torque).summary()
            self.assertAlmostEqual(t['twist_deg'][50],0)
            self.assertAlmostEqual(t['twist_deg'][0],-t['twist_deg'][-1])
            self.assertAlmostEqual(t['right_end_rotation_rad']-t['left_end_rotation_rad'],t['total_twist_rad'])

    def test_pinhole_triangulation_and_projection_matrices(self):
        rig=StereoRig(.16,.02);p=np.array([[.03,-.008,.01],[.13,.004,.0101],[.08,.002,-.006]])
        pixels=[rig.project(p,i) for i in (0,1)]
        np.testing.assert_allclose(rig.triangulate(*pixels),p,atol=1e-14)
        for i in (0,1):
            q=np.column_stack((p,np.ones(len(p))))@rig.cameras[i]['P'].T
            np.testing.assert_allclose(q[:,:2]/q[:,2,None],pixels[i],atol=1e-10)

    def test_surface_strain_is_rigid_motion_invariant(self):
        x,y=np.meshgrid(np.arange(9)*8,np.arange(7)*8);centres=np.column_stack((x.ravel(),y.ravel()))
        ref=np.column_stack((centres[:,0]/1000,-centres[:,1]/1000,np.sin(centres[:,0]/30)*.0001))
        a=.4;rot=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
        defo=ref@rot.T+[.003,-.002,.004]
        strain=surface_strain(ref,defo,centres,np.ones(len(ref),bool),24)
        self.assertGreater(np.isfinite(strain[:,0]).sum(),30)
        np.testing.assert_allclose(strain[np.isfinite(strain).all(axis=1)],0,atol=1e-12)

    def test_input_validation(self):
        for changes in [dict(side_mm=0),dict(length_mm=10),dict(torque_nm=1e6),dict(compare_noise=True),dict(subset_size=18)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                build_config(dict(benchmark='square_torsion',**changes))


class StereoImageTests(unittest.TestCase):
    def measure(self,torque=0,noise=0,rotation=None,translation=None):
        c=build_config(dict(benchmark='square_torsion',length_mm=120,side_mm=20,torque_nm=torque,noise_std=noise,step=12,fit_radius_px=30,subset_size=17))
        m=SquareTorsion(.12,.02,70e9,.33,torque);rig=StereoRig(.12,.02,width=480)
        images,masks=generate_images(m,rig,c,rotation,translation)
        r=reconstruct(images,masks,rig,c['dic'],30)
        xy=rig.reference_xy(r['centres_px']);p0=np.column_stack((xy,np.full(len(xy),m.a)));p1=m.position(*xy.T,m.a)
        if rotation is not None:p1=p1@rotation.T
        if translation is not None:p1=p1+translation
        good=r['valid'];error=r['displacement_m'][good]-(p1-p0)[good]
        coverage=float(good.mean());rmse=float(np.sqrt(np.mean(np.sum(error**2,axis=1))))
        print(f'  stereo torque={torque}, noise={noise}: coverage={coverage:.3f}, vector RMSE={rmse*1000:.6f} mm')
        return r,coverage,rmse

    def test_zero_load_and_rigid_translation(self):
        r,coverage,rmse=self.measure()
        self.assertGreater(coverage,.9);self.assertLess(rmse,1e-10)
        r,coverage,rmse=self.measure(translation=np.array([.00017,-.00012,.00013]))
        self.assertGreater(coverage,.8);self.assertLess(rmse,2e-5)

    def test_rigid_rotation_images(self):
        a=.035;rot=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
        r,coverage,rmse=self.measure(rotation=rot)
        self.assertGreater(coverage,.8);self.assertLess(rmse,2e-5)
        strain=r['strain'];self.assertGreater(np.isfinite(strain[:,0]).sum(),10)
        self.assertLess(np.nanmax(abs(strain)),.004)

    def test_positive_negative_torque_and_noise(self):
        for torque,noise in [(100,0),(-100,0),(100,.015)]:
            with self.subTest(torque=torque,noise=noise):
                r,coverage,rmse=self.measure(torque,noise)
                self.assertGreater(coverage,.7);self.assertLess(rmse,3e-5)

    def test_export_and_failed_measurements(self):
        c=build_config(dict(benchmark='square_torsion',length_mm=160,torque_nm=100,noise_std=.15,speckle_radius_px=1,step=24,fit_radius_px=55))
        with tempfile.TemporaryDirectory() as directory:
            p=run_stereo(c,'test-stereo',directory)
            json.dumps(p,allow_nan=False)
            self.assertLess(p['summary']['valid_displacement_subsets'],p['summary']['candidate_subsets'])
            for file in ['report.html','stereo_fields.csv','stereo_correspondences.csv','camera_calibration.json','left_deformed.png']:
                self.assertTrue((Path(directory)/file).is_file())
            self.assertNotIn('stress_xx',p['fields'])

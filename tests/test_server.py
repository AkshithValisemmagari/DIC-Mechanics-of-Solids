"""Exercise the real HTTP workflow without requiring a browser."""
import io
import http.cookiejar
import json
from pathlib import Path
import threading
import time
import unittest
import urllib.request
import urllib.error
import zipfile
from http.server import ThreadingHTTPServer
import lab_server


class ServerWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),lab_server.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(self,path):
        with self.client.open(self.base+path,timeout=10) as response:return response.read()
    def post(self,data,token):
        request=urllib.request.Request(self.base+'/api/run',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Lab-Token':token})
        return json.load(self.client.open(request,timeout=10))
    def test_reject_bad_request_without_running(self):
        settings=json.loads(self.get('/api/settings'))
        with self.assertRaises(urllib.error.HTTPError) as error:self.post({},'wrong')
        self.assertEqual(error.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as error:self.post({'length_mm':0},settings['token'])
        self.assertEqual(error.exception.code,400)
    def test_selected_objects_and_export(self):
        settings=json.loads(self.get('/api/settings'))
        requests=[dict(benchmark='axial_bar',material='steel',force_n=50000),dict(benchmark='cantilever',material='custom',E_gpa=90,nu=.28,height_mm=30,thickness_mm=6,force_n=1000,noise_std=.01),dict(benchmark='plate_with_hole',length_mm=80,height_mm=80,force_n=30000)]
        for data in requests:
            with self.subTest(object=data['benchmark']):
                job=self.post(data,settings['token'])
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    status=json.loads(self.get('/api/status'))
                    if status['status']!='running':break
                    time.sleep(.1)
                self.assertEqual(status['status'],'done',status)
                payload=json.loads(self.get('/api/result'))
                self.assertEqual(payload['run_id'],job['job_id'])
                self.assertEqual(payload['config']['benchmark'],data['benchmark'])
                self.assertGreater(payload['summary']['valid_displacement_subsets'],0)
                self.assertTrue(self.get(f"/runs/{job['job_id']}/reference.png").startswith(b'\x89PNG'))
                raw=self.get(f"/runs/{job['job_id']}/download.zip")
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertIn('mechanical_fields.csv',archive.namelist())
                    self.assertIn('interactive_result.json',archive.namelist())
                self.assertIn(b'DIC Studio', self.get('/'))

    def wait_result(self):
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            state=json.loads(self.get('/api/status'))
            if state['status']!='running':break
            time.sleep(.1)
        self.assertEqual(state['status'],'done',state)
        return json.loads(self.get('/api/result'))

    def test_paired_bending_and_analytical_torsion_exports(self):
        settings=json.loads(self.get('/api/settings'))
        self.post(dict(benchmark='pure_bending',length_mm=120,height_mm=30,thickness_mm=6,moment_nm=60,noise_std=.025,compare_noise=True),settings['token'])
        data=self.wait_result();base=data['baseline'];path='/runs/'+data['run_id']+'/'
        self.assertEqual(base['config']['camera']['noise_std'],0)
        self.assertEqual(data['config']['camera']['noise_std'],.025)
        for key in ('image','dic','strain','material','moment_nm','domain_m'):
            self.assertEqual(base['config'][key],data['config'][key])
        self.assertLess(base['summary']['displacement_px']['vector_rmse'],.15)
        self.assertGreater(data['noise_comparison']['u_mm']['common_count'],0)
        self.assertNotEqual(self.get(path+'baseline/reference.png'),self.get(path+'reference.png'))
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base+path+'baseline/reference.png')
        self.assertEqual(error.exception.code,404)
        with zipfile.ZipFile(io.BytesIO(self.get(path+'download.zip'))) as archive:
            self.assertIsNone(archive.testzip())
            for name in ('noise_comparison.csv','noise_comparison.json','baseline/reference.png','baseline/mechanical_fields.csv','baseline/report.html'):
                self.assertIn(name,archive.namelist())
        for asset in ('/analysis.js','/experiments.js'):
            self.assertTrue(self.get(asset))
        self.post(dict(benchmark='torsion',length_mm=200,radius_mm=10,torque_nm=20),settings['token'])
        shaft=self.wait_result();self.assertTrue(shaft['analysis_only']);self.assertNotIn('dic',shaft)
        path='/runs/'+shaft['run_id']+'/'
        with zipfile.ZipFile(io.BytesIO(self.get(path+'download.zip'))) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('torsion_twist.csv',archive.namelist());self.assertIn('torsion_stress.csv',archive.namelist())
            self.assertNotIn('dic_displacements.csv',archive.namelist());self.assertNotIn('reference.png',archive.namelist())
        self.assertIn(b'No DIC',self.get(path+'report.html'))

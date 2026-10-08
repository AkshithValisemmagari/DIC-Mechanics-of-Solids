"""Exercise the real HTTP workflow without requiring a browser."""
import io
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
    def get(self,path):
        with urllib.request.urlopen(self.base+path,timeout=10) as response:return response.read()
    def post(self,data,token):
        request=urllib.request.Request(self.base+'/api/run',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Lab-Token':token})
        return json.load(urllib.request.urlopen(request,timeout=10))
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
                self.assertIn(b'Fieldlab',self.get('/'))

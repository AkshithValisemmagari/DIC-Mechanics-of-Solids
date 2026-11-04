"""Exercise real CLI files, including export under an ASCII default locale."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLIExportTests(unittest.TestCase):
    def test_axial_summary_is_saved_and_matches_console(self):
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run([sys.executable, str(ROOT/'run_axial_1d.py'),
                                  '--output-dir', folder], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            output = Path(folder)
            summary = (output/'summary.txt').read_text(encoding='utf-8')
            self.assertIn('Stress: 1 MPa', summary)
            self.assertIn('End displacement: 0.005 mm', summary)
            self.assertTrue(run.stdout.startswith(summary))
            self.assertEqual(json.loads((output/'parameters.json').read_text(encoding='utf-8')),
                             json.loads((ROOT/'configs/axial_bar.json').read_text(encoding='utf-8')))
            self.assertTrue((output/'analytical_fields.csv').exists())
            self.assertTrue((output/'analytical_fields.png').read_bytes().startswith(b'\x89PNG'))

    def test_batch_index_is_utf8_under_ascii_default_locale(self):
        with tempfile.TemporaryDirectory() as folder:
            # Keep the real CLI config/index-writing path; isolate it from the
            # expensive DIC solve so this test diagnoses export encoding only.
            script = """
import sys
from pathlib import Path
import run_project

def experiment(config, output):
    output.mkdir(parents=True)
    (output/'report.html').write_text('report', encoding='utf-8')
    return {'summary': {'benchmark': config['benchmark']}}

run_project.run_experiment = experiment
sys.argv = ['run_project.py', '--benchmark', 'axial_bar', '--output-dir', sys.argv[1]]
run_project.main()
"""
            env = dict(os.environ, LC_ALL='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0',
                       PYTHONIOENCODING='utf-8')
            run = subprocess.run([sys.executable, '-c', script, folder], cwd=ROOT,
                                 env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            page = (Path(folder)/'index.html').read_bytes().decode('utf-8')
            self.assertIn('Analytical ground truth · Synthetic imaging', page)
            self.assertIn('axial_bar_dic/report.html', page)
            self.assertEqual(json.loads((Path(folder)/'benchmark_summary.json').read_text(encoding='utf-8')),
                             [{'benchmark': 'axial_bar'}])


if __name__ == '__main__':
    unittest.main()

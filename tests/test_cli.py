import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from vlm_eval.providers import Ollama
import test_core


class CLITests(unittest.TestCase):
    def test_endpoint_validation(self):
        for url in ('http://remote.example', 'https://user:secret@example.org', 'http://127.0.0.1/?token=x'):
            with self.assertRaises(ValueError):
                Ollama('fixture', url)

    def test_installed_cli_http(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body = json.dumps({'model': 'fixture-returned', 'done': True,
                                   'message': {'content': '{"color":"red"}'}, 'eval_count': 9}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        with HTTPServer(('127.0.0.1', 0), Handler) as server, tempfile.TemporaryDirectory() as d:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                root = Path(d)
                dataset, _ = test_core.CoreTests().setup_data(root)
                template = Path(__file__).resolve().parents[1] / 'examples/dataset.template.json'
                dataset.write_text(template.read_text())
                (root / 'photo.png').rename(root / 'object.png')
                output = root / 'report.json'
                env = {**os.environ, 'VLM_EVAL_BASE_URL': f'http://127.0.0.1:{server.server_port}'}
                command = [sys.executable, '-m', 'vlm_eval', 'run', str(dataset), '--model', 'fixture', '--out', str(output)]
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(output.read_text())
                self.assertEqual(report['summary']['color']['rate'], 1)
                self.assertEqual(report['rows'][0]['provider_metrics']['eval_count'], 9)
                self.assertEqual(requests[0][0], '/api/chat')
                self.assertNotIn('truth', json.dumps(requests[0][1]))
                self.assertTrue(requests[0][1]['messages'][0]['images'])
                # Existing results must never be overwritten or trigger another call.
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(len(requests), 1)
            finally:
                server.shutdown()
                thread.join()

if __name__ == '__main__':
    unittest.main()

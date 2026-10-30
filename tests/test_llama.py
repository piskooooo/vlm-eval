import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from vlm_eval import providers
from vlm_eval.dataset import load_dataset
from vlm_eval.runner import run
import test_core


class LlamaTests(unittest.TestCase):
    def test_endpoint_and_payload(self):
        cls = getattr(providers, 'LlamaCpp', None)
        self.assertIsNotNone(cls)
        with self.assertRaises(ValueError):
            cls('model', 'http://example.org', api_key='fixture')
        provider = cls('model', 'http://127.0.0.1:12345', api_key='fixture')
        with patch.object(provider, '_request', return_value={}) as request:
            provider.generate('Read the shape', [{'bytes': b'\x89PNG\r\n\x1a\nfixture'}])
        payload = request.call_args.args[0]
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['max_tokens'], 512)
        self.assertEqual(payload['messages'][0]['content'][1]['type'], 'image_url')
        self.assertTrue(payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
        self.assertNotIn('fixture', json.dumps(provider.metadata))

    def test_raw_response_and_failure_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            path, _ = test_core.CoreTests().setup_data(Path(d))
            raw = {'model': 'model', 'choices': [{'message': {'content': '{"color":"red"}'}, 'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': 10, 'completion_tokens': 4, 'total_tokens': 14}}
            class Fixture:
                metadata = {'interface': 'llama-cpp-chat'}
                def generate(self, *args):
                    return raw
            report = run(load_dataset(path), Fixture())
            self.assertEqual(report['summary']['color']['pass'], 1)
            self.assertEqual(report['rows'][0]['raw'], raw)
            self.assertEqual(report['rows'][0]['provider_metrics']['completion_tokens'], 4)
            for choices in ([], [raw['choices'][0], raw['choices'][0]], [{'message': {'content': '{"color":"red"}'}, 'finish_reason': 'length'}]):
                raw['choices'] = choices
                report = run(load_dataset(path), Fixture())
                self.assertEqual(report['rows'][0]['status'], 'invalid_response')
                self.assertEqual(report['summary']['color']['fail'], 1)

    def test_cli_transport(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((self.path, self.headers.get('Authorization'), json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'choices': [{'message': {'content': '{"color":"red"}'}, 'finish_reason': 'stop'}]}).encode())
            def log_message(self, *args):
                pass
        with HTTPServer(('127.0.0.1', 0), Handler) as server, tempfile.TemporaryDirectory() as d:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                path, _ = test_core.CoreTests().setup_data(Path(d))
                env = {**os.environ, 'VLM_EVAL_BASE_URL': f'http://127.0.0.1:{server.server_port}', 'VLM_EVAL_API_KEY': 'test-placeholder'}
                result = subprocess.run([sys.executable, '-m', 'vlm_eval', 'run', str(path), '--provider', 'llama-cpp', '--model', 'fixture', '--out', str(Path(d)/'report.json')], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(received[0][0], '/v1/chat/completions')
                self.assertEqual(received[0][1], 'Bearer test-placeholder')
                self.assertNotIn('truth', received[0][2])
            finally:
                server.shutdown()
                thread.join()

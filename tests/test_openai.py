"""No-network Responses API contract and CLI tests; no real credentials used."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch, MagicMock

from vlm_eval.__main__ import main
from vlm_eval.dataset import load_dataset
from vlm_eval.openai_provider import OpenAI
from vlm_eval.runner import run

ROOT = Path(__file__).resolve().parents[1]
KEY = 'unit-test-placeholder-only'
MODEL = 'gpt-5.4-mini-2026-03-17'


def response(text='{"color":"red","shape":"circle"}'):
    return {'id': 'resp_fixture', 'model': MODEL, 'status': 'completed', 'error': None,
            'output': [{'type': 'reasoning', 'summary': []},
                       {'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': text, 'annotations': []}]}],
            'usage': {'input_tokens': 30, 'output_tokens': 12, 'total_tokens': 42,
                      'input_tokens_details': {'cached_tokens': 0},
                      'output_tokens_details': {'reasoning_tokens': 2}}}


class OpenAITests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch('socket.socket.connect', side_effect=AssertionError('network disabled')).start()
        patch.dict(os.environ, {'OPENAI_API_KEY': KEY}, clear=True).start()
        self.dataset = load_dataset(ROOT / 'examples/shapes/dataset.json')
        self.single = {**self.dataset, 'manifest': {**self.dataset['manifest'], 'items': self.dataset['manifest']['items'][:1]}}
        self.opener = MagicMock()
        self.build = patch('urllib.request.build_opener', return_value=self.opener).start()
        self.set_response(response())

    def set_response(self, raw):
        self.opener.open.side_effect = None
        self.opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(raw).encode()

    def provider(self, **kwargs):
        return OpenAI(MODEL, **kwargs)

    def evaluate(self, raw=None):
        if raw is not None:
            self.set_response(raw)
        return run(self.single, self.provider(), max_requests=1)

    def test_image_request_schema_and_credential_destination(self):
        report = self.evaluate()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + KEY)
        self.assertEqual(self.opener.open.call_args.kwargs['timeout'], 120)
        payload = json.loads(request.data)
        self.assertFalse(payload['store'])
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['max_output_tokens'], 512)
        self.assertNotIn('seed', payload)
        self.assertNotIn('temperature', payload)
        content = payload['input'][0]['content']
        self.assertEqual(content[0], {'type': 'input_text', 'text': self.dataset['manifest']['prompt']})
        image = content[1]['image_url']
        self.assertTrue(image.startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(image.split(',')[1]), self.dataset['images']['001'][0]['bytes'])
        schema = payload['text']['format']['schema']
        self.assertTrue(payload['text']['format']['strict'])
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['properties'], {'color': {'type': ['string', 'null']}, 'shape': {'type': ['string', 'null']}})
        self.assertEqual(set(schema['required']), {'color', 'shape'})
        self.assertNotIn('truth', json.dumps(payload))
        self.assertNotIn('"red"', json.dumps(payload))
        self.assertNotIn(KEY, json.dumps(report))
        self.assertEqual(report['rows'][0]['prediction'], {'color': 'red', 'shape': 'circle'})
        self.assertEqual(report['rows'][0]['raw']['model'], MODEL)
        self.assertEqual(report['rows'][0]['provider_metrics']['input_tokens'], 30)
        self.assertEqual(report['rows'][0]['provider_metrics']['reasoning_tokens'], 2)
        self.assertEqual(report['max_requests'], 1)
        handlers = self.build.call_args.args
        self.assertTrue(any(isinstance(h, urllib.request.ProxyHandler) and not h.proxies for h in handlers))
        redirect = next(h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
        with self.assertRaises(ValueError):
            redirect.redirect_request(request, None, 302, '', {}, 'https://elsewhere.example/')

    def test_truth_values_and_states_never_change_request(self):
        self.evaluate()
        first = self.opener.open.call_args.args[0].data
        altered = copy.deepcopy(self.single)
        altered['manifest']['items'][0]['truth'] = {'color': {'state': 'unknown'}, 'shape': {'state': 'absent'}}
        run(altered, self.provider(), max_requests=1)
        self.assertEqual(first, self.opener.open.call_args.args[0].data)

    def test_refusal_incomplete_and_malformed_output(self):
        refusal = response()
        refusal['output'][1]['content'] = [{'type': 'refusal', 'refusal': 'Cannot comply.'}]
        incomplete = response()
        incomplete.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
        failed = response()
        failed.update(status='failed', error={'message': 'private endpoint and secret'}, output=[])
        samples = [refusal, incomplete, failed, response('not JSON'), response('{"color":"red"}'),
                   response('{"color":false,"shape":"circle"}'), response('{"color":"red","shape":"circle","extra":"x"}'),
                   response('{"color":"red","color":"blue","shape":"circle"}'), {'status': 'completed', 'output': None}]
        for raw in samples:
            with self.subTest(raw=raw):
                report = self.evaluate(raw)
                self.assertEqual(report['rows'][0]['status'], 'invalid_response')
                self.assertEqual(report['summary']['color']['fail'], 1)
                self.assertNotIn('private endpoint and secret', json.dumps(report))
        self.assertEqual(self.evaluate(refusal)['rows'][0]['error_code'], 'refusal')
        self.assertEqual(self.evaluate(incomplete)['rows'][0]['error_code'], 'incomplete')

    def test_http_errors_transport_no_retries_no_error_body(self):
        for code in (400, 401, 403, 429, 500, 302):
            with self.subTest(code=code):
                error = urllib.error.HTTPError('https://api.openai.com/v1/responses', code, 'sensitive message', {}, io.BytesIO(b'sensitive body'))
                self.opener.open.side_effect = error
                before = self.opener.open.call_count
                report = self.evaluate()
                self.assertEqual(self.opener.open.call_count - before, 1)
                self.assertEqual(report['rows'][0]['status'], 'request_error')
                self.assertIsNone(report['rows'][0]['raw'])
                self.assertNotIn('sensitive', json.dumps(report))
        for error in (TimeoutError('sensitive'), urllib.error.URLError('sensitive')):
            self.opener.open.side_effect = error
            self.assertEqual(self.evaluate()['rows'][0]['status'], 'request_error')

    def test_missing_key_and_unsupported_settings_fail_before_request(self):
        for kwargs in ({'seed': 0}, {'temperature': 0}, {'max_tokens': 0}, {'max_tokens': 15}, {'timeout': float('nan')}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.provider(**kwargs)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            OpenAI(MODEL)
        self.opener.open.assert_not_called()

    def test_request_limit_fails_before_any_network(self):
        for limit in (None, 0, 2):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                run(self.dataset, self.provider(), max_requests=limit)
        self.opener.open.assert_not_called()

    def test_raw_projection_excludes_envelope_secrets(self):
        raw = response()
        raw.update(metadata={'secret': KEY}, error={'message': KEY}, input='private input', endpoint='private endpoint')
        raw['error'] = None
        raw['output'][1]['content'][0]['annotations'] = [{'url': 'private endpoint'}]
        report = self.evaluate(raw)
        self.assertNotIn(KEY, json.dumps(report))
        self.assertNotIn('private endpoint', json.dumps(report))
        self.assertNotIn('private input', json.dumps(report))
        raw = response(json.dumps({'color': KEY, 'shape': 'circle'}))
        self.assertNotIn(KEY, json.dumps(self.evaluate(raw)))

    def test_cli_shapes_workflow_and_local_env_is_ignored(self):
        self.opener.open.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(response(json.dumps({'color': color, 'shape': shape}))).encode()
            for color, shape in [('red', 'circle'), ('green', 'square'), ('blue', 'triangle')]]
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'VLM_EVAL_BASE_URL': 'http://private.invalid', 'VLM_EVAL_API_KEY': 'wrong-key'}), patch('sys.stdout', new_callable=io.StringIO):
            path = Path(d) / 'report.json'
            code = main(['run', str(ROOT / 'examples/shapes/dataset.json'), '--provider', 'openai', '--model', MODEL,
                         '--max-requests', '3', '--max-tokens', '512', '--timeout', '60', '--out', str(path)])
            self.assertEqual(code, 0)
            report = json.loads(path.read_text())
            self.assertEqual(report['summary']['shape']['pass'], 3)
            self.assertEqual(self.opener.open.call_count, 3)
            for call in self.opener.open.call_args_list:
                self.assertEqual(call.args[0].get_header('Authorization'), 'Bearer ' + KEY)
                self.assertEqual(call.args[0].full_url, 'https://api.openai.com/v1/responses')


    def test_malformed_envelope_and_oversized_responses(self):
        for body in (b'not JSON with sensitive body', b'{"usage":1e999}', b'[]', b'x' * (4 * 1024 * 1024 + 1)):
            with self.subTest(size=len(body)):
                self.opener.open.return_value.__enter__.return_value.read.return_value = body
                report = self.evaluate()
                self.assertEqual(report['rows'][0]['status'], 'request_error')
                self.assertIsNone(report['rows'][0]['raw'])
                self.assertNotIn('sensitive body', json.dumps(report))

    def test_missing_multiple_and_incomplete_messages(self):
        samples = []
        for output in ([], [None], [{'type': 'function_call'}]):
            raw = response()
            raw['output'] = output
            samples.append(raw)
        raw = response()
        raw['output'].append(copy.deepcopy(raw['output'][1]))
        samples.append(raw)
        raw = response()
        raw['output'][1]['status'] = 'incomplete'
        samples.append(raw)
        raw = response()
        raw['output'][1]['content'].append({'type': 'output_text', 'text': '{}'})
        samples.append(raw)
        for raw in samples:
            with self.subTest(raw=raw):
                self.assertEqual(self.evaluate(raw)['rows'][0]['status'], 'invalid_response')

    def test_cli_rejects_unsupported_flags_without_creating_report(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'report.json'
            base = ['run', str(ROOT / 'examples/shapes/dataset.json'), '--provider', 'openai', '--model', MODEL, '--out', str(output)]
            for extra in (['--max-requests', '3', '--seed', '0'], ['--max-requests', '3', '--temperature', '0'], ['--max-requests', '2'], []):
                with patch('sys.stderr', new_callable=io.StringIO) as stderr:
                    self.assertEqual(main(base + extra), 2)
                    self.assertNotIn(KEY, stderr.getvalue())
                    if '--seed' in extra or '--temperature' in extra:
                        self.assertIn('omit both', stderr.getvalue())
                self.assertFalse(output.exists())
            self.opener.open.assert_not_called()

    def test_unknown_truth_skips_while_absence_fails_on_refusal(self):
        self.single['manifest']['items'][0]['truth'] = {'color': {'state': 'unknown'}, 'shape': {'state': 'absent'}}
        raw = response()
        raw['output'][1]['content'] = [{'type': 'refusal', 'refusal': 'Cannot comply.'}]
        report = self.evaluate(raw)
        self.assertEqual(report['summary']['color']['skip'], 1)
        self.assertEqual(report['summary']['shape']['fail'], 1)


    def test_local_defaults_and_openai_key_is_not_sent_to_local_providers(self):
        for name, raw in [('ollama', {'message': {'content': '{"color":"red","shape":"circle"}'}}),
                          ('llama-cpp', {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"color":"red","shape":"circle"}'}}]})]:
            with self.subTest(provider=name), tempfile.TemporaryDirectory() as d, patch('sys.stdout', new_callable=io.StringIO):
                self.set_response(raw)
                code = main(['run', str(ROOT / 'examples/shapes/dataset.json'), '--provider', name,
                             '--model', 'local-fixture', '--out', str(Path(d) / 'report.json')])
                self.assertEqual(code, 0)
                request = self.opener.open.call_args.args[0]
                self.assertIsNone(request.get_header('Authorization'))
                payload = json.loads(request.data)
                settings = payload['options'] if name == 'ollama' else payload
                self.assertEqual(settings['temperature'], 0)
                self.assertEqual(settings['seed'], 0)

    def test_invalid_images_and_serialized_request_cap_never_send(self):
        provider = self.provider()
        with self.assertRaises(RuntimeError):
            provider.generate('prompt', [{'bytes': b'not an image'}], fields=('color',))
        with patch('vlm_eval.openai_provider.MAX_REQUEST_BYTES', 10), self.assertRaises(RuntimeError):
            provider.generate('prompt', self.dataset['images']['001'], fields=('color',))
        self.opener.open.assert_not_called()

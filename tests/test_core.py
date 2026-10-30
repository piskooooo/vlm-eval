import json
from pathlib import Path
import tempfile
import unittest
from vlm_eval.dataset import load_dataset
from vlm_eval.scoring import TruthField, TruthState, score_truth_field, score_exact
from vlm_eval.runner import run


class CoreTests(unittest.TestCase):
    def test_normalized_exact(self):
        self.assertTrue(score_exact(' Red  Circle ', 'red circle')['pass'])
        self.assertFalse(score_exact('red', 'red circle')['pass'])
        self.assertFalse(score_exact('red', None)['pass'])

    def test_truth_states(self):
        self.assertIsNone(score_truth_field(TruthField(TruthState.UNKNOWN), 'x', score_exact))
        for state in (TruthState.ABSENT, TruthState.NOT_APPLICABLE):
            self.assertTrue(score_truth_field(TruthField(state), None, score_exact)['pass'])
            self.assertFalse(score_truth_field(TruthField(state), '', score_exact)['pass'])

    def setup_data(self, root):
        # Transport fixture only; not a real image or model accuracy evidence.
        (root / 'photo.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        data = {'schema_version': 1, 'dataset_id': 'test', 'version': '1',
                'prompt': 'Return a JSON object with color.', 'items': [
                    {'id': 'one', 'images': ['photo.png'], 'truth': {
                        'color': {'state': 'value', 'value': 'red'}}}]}
        path = root / 'dataset.json'
        path.write_text(json.dumps(data))
        return path, data

    def test_dataset_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, data = self.setup_data(root)
            first = load_dataset(path)
            self.assertEqual(first['manifest']['version'], '1')
            (root / 'photo.png').write_bytes(b'\x89PNG\r\n\x1a\nchanged')
            self.assertNotEqual(first['images']['one'][0]['sha256'], load_dataset(path)['images']['one'][0]['sha256'])
            for images in (['../outside.png'], ['/tmp/photo.png'], []):
                data['items'][0]['images'] = images
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load_dataset(path)

    def test_duplicate_ids_and_invalid_truth(self):
        with tempfile.TemporaryDirectory() as d:
            path, data = self.setup_data(Path(d))
            data['items'].append(data['items'][0])
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_dataset(path)
            data['items'] = data['items'][:1]
            data['items'][0]['truth']['color'] = {'state': 'value', 'value': 42}
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_dataset(path)

    def test_workflow_and_invalid_response_penalty(self):
        with tempfile.TemporaryDirectory() as d:
            path, data = self.setup_data(Path(d))
            dataset = load_dataset(path)
            class Provider:
                metadata = {'interface': 'fixture', 'model': 'fixture-only', 'settings': {}}
                def generate(self, prompt, images):
                    self.prompt = prompt
                    return {'message': {'content': '{"color":"red"}'}}
            provider = Provider()
            report = run(dataset, provider)
            self.assertEqual(report['summary']['color']['rate'], 1)
            self.assertNotIn('truth', provider.prompt)
            data['items'][0]['truth']['color'] = {'state': 'absent'}
            path.write_text(json.dumps(data))
            provider.generate = lambda *args: {'message': {'content': 'not json'}}
            report = run(load_dataset(path), provider)
            self.assertEqual(report['summary']['color']['fail'], 1)
            self.assertEqual(report['rows'][0]['status'], 'invalid_response')
            self.assertEqual(report['rows'][0]['raw']['message']['content'], 'not json')

if __name__ == '__main__':
    unittest.main()

class FailureTests(unittest.TestCase):
    def test_incomplete_http_preserves_failure_report(self):
        import http.client
        with tempfile.TemporaryDirectory() as d:
            path, _ = CoreTests().setup_data(Path(d))
            class Provider:
                metadata = {'interface': 'fixture'}
                def generate(self, *args):
                    raise http.client.IncompleteRead(b'', 20)
            report = run(load_dataset(path), Provider())
            self.assertEqual(report['rows'][0]['status'], 'request_error')
            self.assertEqual(report['summary']['color']['fail'], 1)

    def test_overflow_json_is_rejected(self):
        from vlm_eval.dataset import parse_json
        with self.assertRaises(ValueError):
            parse_json('{"total_duration":1e999}')

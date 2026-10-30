"""Ollama and llama.cpp transports; no model installation or service control."""
import base64
import json
import math
import urllib.request
from urllib.parse import urlsplit

from .dataset import parse_json


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('provider redirects are disabled')


class Ollama:
    def __init__(self, model, base_url='http://127.0.0.1:11434', *, api_key=None,
                 temperature=0.0, seed=0, max_tokens=512, timeout=120.0):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {'', '/'}):
            raise ValueError('expected a bare HTTP(S) provider origin without credentials')
        if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('non-loopback providers require HTTPS')
        if api_key and parsed.scheme != 'https':
            raise ValueError('credentials require HTTPS')
        if not model.strip() or not math.isfinite(temperature) or temperature < 0 or max_tokens <= 0 or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('invalid model or generation settings')
        self.url = base_url.rstrip('/') + '/api/chat'
        self.api_key, self.timeout = api_key, timeout
        self.metadata = {'interface': 'ollama-chat', 'model': model,
                         'settings': {'temperature': temperature, 'seed': seed, 'num_predict': max_tokens},
                         'timeout_seconds': timeout, 'retries': 0,
                         'format': 'json', 'stream': False,
                         'endpoint_recorded': False}

    def generate(self, prompt, images):
        payload = {'model': self.metadata['model'], 'format': 'json', 'stream': False,
                   'options': self.metadata['settings'],
                   'messages': [{'role': 'user', 'content': prompt,
                                 'images': [base64.b64encode(image['bytes']).decode('ascii') for image in images]}]}
        return self._request(payload)

    def _request(self, payload):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        # No environment proxies and no redirects: image destination is explicit.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=self.timeout) as response:
            body = response.read(4 * 1024 * 1024 + 1)
        if len(body) > 4 * 1024 * 1024:
            raise ValueError('provider response exceeds 4 MiB')
        return parse_json(body)


class LlamaCpp(Ollama):
    """Native llama.cpp chat interface with unmodified response retention."""
    def __init__(self, model, base_url='http://127.0.0.1:8080', *, api_key=None, **kwargs):
        super().__init__(model, base_url, api_key=None, **kwargs)
        parsed = urlsplit(base_url)
        if api_key and parsed.scheme != 'https' and parsed.hostname not in {'127.0.0.1', '::1'}:
            raise ValueError('credentials require HTTPS or literal loopback')
        self.api_key = api_key
        self.url = base_url.rstrip('/') + '/v1/chat/completions'
        self.metadata['interface'] = 'llama-cpp-chat'
        self.metadata['settings']['max_tokens'] = self.metadata['settings'].pop('num_predict')
        self.metadata['format'] = {'type': 'json_object'}

    def generate(self, prompt, images):
        content = [{'type': 'text', 'text': prompt}]
        for image in images:
            mime = 'image/png' if image['bytes'].startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg'
            encoded = base64.b64encode(image['bytes']).decode('ascii')
            content.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{encoded}'}})
        return self._request({'model': self.metadata['model'], 'stream': False,
                              'response_format': self.metadata['format'],
                              **self.metadata['settings'],
                              'messages': [{'role': 'user', 'content': content}]})

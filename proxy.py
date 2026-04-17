#!/usr/bin/env python3
"""
통합 프록시 서버 — wallet-analyzer 전용 (포트 8080)
=====================================================
  /arkham/* → https://api.arkhamintelligence.com/*  (Cloudflare 우회)
  /surf/*   → https://api.asksurf.ai/*              (Surf API CORS 우회)

사용법: python3 proxy.py [포트]
기본 포트: 8080
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, ssl, gzip, zlib, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

ARKHAM_BASE = 'https://api.arkhamintelligence.com'
SURF_BASE   = 'https://api.asksurf.ai'

CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'API-Key, Authorization, Content-Type',
}

BROWSER_HEADERS = {
    'User-Agent':         'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept':             'application/json, text/plain, */*',
    'Accept-Language':    'en-US,en;q=0.9',
    'Origin':             'https://intel.arkm.com',
    'Referer':            'https://intel.arkm.com/',
    'sec-ch-ua':          '"Chromium";v="124", "Google Chrome";v="124"',
    'sec-ch-ua-mobile':   '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest':     'empty',
    'sec-fetch-mode':     'cors',
    'sec-fetch-site':     'same-site',
}

def decompress(data, encoding):
    if encoding == 'gzip':    return gzip.decompress(data)
    if encoding == 'deflate': return zlib.decompress(data)
    return data

def send_resp(handler, status, body, ct='application/json'):
    handler.send_response(status)
    handler.send_header('Content-Type', ct)
    for k, v in CORS.items(): handler.send_header(k, v)
    handler.end_headers()
    if isinstance(body, str): body = body.encode()
    handler.wfile.write(body)

class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        self._route('GET', None)

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n) if n else None
        self._route('POST', body)

    def _route(self, method, body):
        if self.path.startswith('/surf'):
            # /surf/gateway/v1/... → api.asksurf.ai/gateway/v1/...
            self._proxy_surf(method, self.path[5:] or '/', body)
        else:
            # /* → api.arkhamintelligence.com/*
            self._proxy_arkham(self.path)

    def _proxy_arkham(self, path):
        url = ARKHAM_BASE + path
        req = urllib.request.Request(url)
        for k, v in BROWSER_HEADERS.items(): req.add_header(k, v)
        req.add_header('Accept-Encoding', 'gzip, deflate')
        api_key = self.headers.get('API-Key', '')
        if api_key: req.add_header('API-Key', api_key)
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                body = decompress(r.read(), r.headers.get('Content-Encoding', ''))
            send_resp(self, 200, body)
        except urllib.error.HTTPError as e:
            body = decompress(e.read(), e.headers.get('Content-Encoding', ''))
            send_resp(self, e.code, body)
        except Exception as e:
            send_resp(self, 500, '{"error":"' + str(e) + '"}')

    def _proxy_surf(self, method, path, body):
        url = SURF_BASE + path
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ('host', 'origin', 'referer', 'content-length')}
        if body: hdrs['Content-Length'] = str(len(body))
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                send_resp(self, r.status, r.read())
        except urllib.error.HTTPError as e:
            send_resp(self, e.code, e.read())
        except Exception as e:
            send_resp(self, 502, '{"error":"' + str(e) + '"}')

    def log_message(self, fmt, *args):
        tag = 'Surf  ' if self.path.startswith('/surf') else 'Arkham'
        print(f'  [{tag}] {fmt % args}')

if __name__ == '__main__':
    print(f'프록시 시작: 0.0.0.0:{PORT}')
    print(f'  /* (GET)  → {ARKHAM_BASE}')
    print(f'  /surf/*   → {SURF_BASE}')
    HTTPServer(('0.0.0.0', PORT), ProxyHandler).serve_forever()

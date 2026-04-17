#!/usr/bin/env python3
"""
통합 프록시 서버 — wallet-analyzer 전용
========================================
  포트 8080 → Arkham API  (Cloudflare 우회 + gzip 해제)
  포트 8765 → Surf API    (CORS 우회 + Authorization 전달)

사용법: python3 proxy.py
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, ssl, gzip, zlib, threading, sys

# ── Arkham ────────────────────────────────────────────────────────
ARKHAM_PORT = 8080
ARKHAM_BASE = 'https://api.arkhamintelligence.com'
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

CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'API-Key, Authorization, Content-Type',
}

class ArkhamProxy(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        url = ARKHAM_BASE + self.path
        req = urllib.request.Request(url)
        for k, v in BROWSER_HEADERS.items(): req.add_header(k, v)
        req.add_header('Accept-Encoding', 'gzip, deflate')
        api_key = self.headers.get('API-Key', '')
        if api_key: req.add_header('API-Key', api_key)

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                body = decompress(r.read(), r.headers.get('Content-Encoding', ''))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = decompress(e.read(), e.headers.get('Content-Encoding', ''))
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        print(f'  [Arkham] {fmt % args}')


# ── Surf ──────────────────────────────────────────────────────────
SURF_PORT = 8765
SURF_BASE = 'https://api.asksurf.ai'

class SurfProxy(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        self._proxy('GET', None)

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n) if n else None
        self._proxy('POST', body)

    def _proxy(self, method, body):
        url = SURF_BASE + self.path
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ('host', 'origin', 'referer', 'content-length')}
        if body:
            hdrs['Content-Length'] = str(len(body))
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() == 'content-type':
                        self.send_header(k, v)
                for k, v in CORS.items(): self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(('{"error":"' + str(e) + '"}').encode())

    def log_message(self, fmt, *args):
        print(f'  [Surf]   {fmt % args}')


# ── 실행 ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    servers = [
        (ARKHAM_PORT, ArkhamProxy, 'Arkham', ARKHAM_BASE),
        (SURF_PORT,   SurfProxy,   'Surf',   SURF_BASE),
    ]
    threads = []
    for port, handler, name, target in servers:
        srv = HTTPServer(('localhost', port), handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        threads.append(t)
        print(f'  ✅ {name:7} http://localhost:{port} → {target}')

    print()
    print('  종료: Ctrl+C')
    try:
        for t in threads: t.join()
    except KeyboardInterrupt:
        print('\n  프록시 종료')

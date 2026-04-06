#!/usr/bin/env python3
"""
Arkham API 프록시 서버 — Cloudflare 우회 버전
브라우저처럼 보이는 헤더를 추가해 차단을 방지합니다.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, ssl, sys

PORT   = 8080
ARKHAM = 'https://api.arkhamintelligence.com'
CORS   = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'API-Key, Content-Type',
}
BROWSER_HEADERS = {
    'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept':           'application/json, text/plain, */*',
    'Accept-Language':  'en-US,en;q=0.9',
    'Accept-Encoding':  'gzip, deflate, br',
    'Origin':           'https://intel.arkm.com',
    'Referer':          'https://intel.arkm.com/',
    'sec-ch-ua':        '"Chromium";v="124", "Google Chrome";v="124"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest':   'empty',
    'sec-fetch-mode':   'cors',
    'sec-fetch-site':   'same-site',
}

class Proxy(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        url = ARKHAM + self.path
        req = urllib.request.Request(url)
        for k, v in BROWSER_HEADERS.items(): req.add_header(k, v)
        api_key = self.headers.get('API-Key', '')
        if api_key: req.add_header('API-Key', api_key)

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                body = r.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
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
        print(f'[{self.address_string()}] {fmt % args}')

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print(f'프록시 서버 시작: 0.0.0.0:{port}')
    HTTPServer(('0.0.0.0', port), Proxy).serve_forever()

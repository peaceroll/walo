#!/usr/bin/env python3
"""
Arkham API 프록시 서버
브라우저 CORS 제한을 우회해 Arkham API를 호출합니다.

실행: python3 proxy.py
접속: http://[서버IP]:[포트]
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, ssl, sys

PORT    = 8080
ARKHAM  = 'https://api.arkhamintelligence.com'
CORS    = {'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Methods': 'GET, OPTIONS',
           'Access-Control-Allow-Headers': 'API-Key, Content-Type'}

class Proxy(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k,v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        url = ARKHAM + self.path
        req = urllib.request.Request(url)
        api_key = self.headers.get('API-Key', '')
        if api_key: req.add_header('API-Key', api_key)

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                body = r.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            for k,v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            for k,v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            for k,v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, fmt, *args):
        print(f'[{self.address_string()}] {fmt % args}')

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print(f'프록시 서버 시작: 0.0.0.0:{port}')
    print(f'브라우저에서 프록시 URL: http://[서버IP]:{port}')
    HTTPServer(('0.0.0.0', port), Proxy).serve_forever()

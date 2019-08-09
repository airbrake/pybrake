import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

from .test_celery import getException

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        global notice
        notice = json.loads(post_data)

        self.send_response(200)
        self.wfile.write('{"id":"1"}'.encode('utf-8'))

def test_celery_integration():
    server_address = ('', 8080)
    server = HTTPServer(server_address, Handler)

    httpd_thread = threading.Thread(target=server.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()

    getException.apply()

    errors = notice["errors"]
    assert len(errors) == 1

    error = errors[0]
    assert error["type"] == "ValueError"
    assert error["message"] == "Test"

    backtrace = error["backtrace"]
    assert len(backtrace) == 2

    frame = backtrace[0]
    assert frame["file"] == "/PROJECT_ROOT/pybrake/test_celery.py"
    assert frame["function"] == "getException"
    assert frame["line"] == 13

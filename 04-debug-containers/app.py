import html
import json
import os
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GREETING = os.environ["GREETING"]
DIRECTORY = Path(os.environ.get("DATA_DIR", "/data"))
FILE = DIRECTORY / "counter.json"
LOCK = threading.Lock()

def count():
    return json.loads(FILE.read_text())["count"] if FILE.exists() else 0

class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type="text/html; charset=utf-8"):
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def page(self, message=""):
        with LOCK:
            value = count()
        return f"""<!doctype html><meta charset=utf-8><title>Docker debugging 101</title>
<style>body{{background:#101923;color:#edf4f8;font:27px system-ui;max-width:1000px;margin:65px auto}}h1{{color:#31ceb2}}button{{font:25px system-ui;padding:12px;background:#31ceb2;border:0}}small{{display:block;margin:24px 0;color:#aebfc9}}</style>
<h1>{html.escape(GREETING)}</h1><p>Saved count: <strong>{value}</strong></p>
<form method=post action=/increment><button>Add one</button></form>
<p>{html.escape(message)}</p><small>Container: {html.escape(os.environ.get("HOSTNAME", "local"))}</small>
<small>Saved file: {html.escape(str(FILE))}</small>"""

    def do_GET(self):
        if self.path == "/healthz":
            return self.send(200, "server running", "text/plain")
        if self.path != "/":
            return self.send(404, "not found", "text/plain")
        return self.send(200, self.page())

    def do_POST(self):
        if self.path != "/increment":
            return self.send(404, "not found", "text/plain")
        try:
            with LOCK:
                value = count() + 1
                DIRECTORY.mkdir(parents=True, exist_ok=True)
                temporary = FILE.with_suffix(".tmp")
                with temporary.open("w") as output:
                    json.dump({"count": value}, output)
                    output.flush()
                    os.fsync(output.fileno())
                temporary.replace(FILE)
        except OSError as error:
            print(f"Save failed: {type(error).__name__}: {error}", flush=True)
            return self.send(500, self.page("Save failed: " + str(error)))
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Content-Length", "0")
        self.end_headers()

print("Starting Docker debugging app on 0.0.0.0:8000", flush=True)
ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

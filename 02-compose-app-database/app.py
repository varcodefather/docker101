"""Small notes app for disposable Compose lab; no authentication."""
import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import psycopg

HOST = os.environ.get("PGHOST", "db")
def connect():
    return psycopg.connect(host=HOST, dbname=os.environ.get("PGDATABASE", "notes"),
        user=os.environ.get("PGUSER", "demo"), password=os.environ["PGPASSWORD"],
        connect_timeout=3)

class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type="text/html; charset=utf-8"):
        body=body.encode();self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":return self.send(200,"ok","text/plain")
        if self.path not in ("/","/api"):return self.send(404,"not found","text/plain")
        try:
            with connect() as conn:
                rows=conn.execute("SELECT id, body FROM notes ORDER BY id").fetchall()
        except psycopg.Error as error:
            print("Database connection failed:",type(error).__name__,str(error),flush=True)
            return self.send(503,self.page("Database connection failed",
                "<p>Check web logs and database hostname or credentials.</p>"))
        if self.path == "/api":return self.send(200,json.dumps({"notes":[{"id":i,"body":b} for i,b in rows]}),"application/json")
        items="".join(f"<li>{html.escape(body)}</li>" for _,body in rows)
        return self.send(200,self.page("Notes saved in PostgreSQL",f"<ul>{items}</ul>"))

    def page(self,title,content):
        return f"""<!doctype html><meta charset=utf-8><title>Compose notes</title>
<style>body{{background:#101923;color:#edf4f8;font:24px system-ui;max-width:1000px;margin:55px auto}}h1{{color:#31ceb2}}input,button{{font:24px system-ui;padding:10px}}button{{background:#31ceb2;border:0}}small{{display:block;margin:30px 0;color:#aebfc9}}li{{margin:18px 0}}</style>
<h1>{title}</h1><form method=post action=/notes><input name=body maxlength=200 placeholder="Write a note" required><button>Save note</button></form>
{content}<small>Database host: {html.escape(HOST)} · App container: {html.escape(os.environ.get('HOSTNAME','local'))}</small>"""

    def do_POST(self):
        if self.path != "/notes":return self.send(404,"not found","text/plain")
        try:
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=2048:raise ValueError("invalid body size")
            body=parse_qs(self.rfile.read(length).decode()).get("body",[""])[0].strip()
            if not 0<len(body)<=200:raise ValueError("note must contain 1 to 200 characters")
        except (ValueError,UnicodeError) as error:return self.send(400,str(error),"text/plain")
        try:
            with connect() as conn:conn.execute("INSERT INTO notes (body) VALUES (%s)",(body,))
        except psycopg.Error as error:
            print("Database insert failed:",type(error).__name__,str(error),flush=True)
            return self.send(503,self.page("Database connection failed","<p>Note was not saved.</p>"))
        self.send_response(303);self.send_header("Location","/");self.send_header("Content-Length","0");self.end_headers()

ThreadingHTTPServer(("0.0.0.0",8000),Handler).serve_forever()

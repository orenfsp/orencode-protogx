"""Fictional local webhook receiver; no third-party credentials or personal data.

Set FSP_DEMO_WEBHOOK_SECRET to the one-time client signing secret. Run with the
project venv: python scripts/demo_integration_consumer.py. Receipts are persisted
in tmp/demo-webhook-receipts.sqlite3; signatures cover exact bytes and delivery ID.
"""
import hashlib
import hmac
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def verify(secret,delivery,timestamp,body,signature):
    try:
        if abs(time.time()-int(timestamp))>300:
            return False
    except (ValueError,TypeError):
        return False
    expected="sha256="+hmac.new(secret.encode(),timestamp.encode()+b"."+delivery.encode()+b"."+body,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)


def main():
    secret=os.environ["FSP_DEMO_WEBHOOK_SECRET"]
    directory=Path(__file__).resolve().parent.parent/"tmp"
    directory.mkdir(exist_ok=True)
    database=sqlite3.connect(directory/"demo-webhook-receipts.sqlite3")
    database.execute("CREATE TABLE IF NOT EXISTS receipts (delivery TEXT PRIMARY KEY, received_at INTEGER)")
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path!="/webhook" or int(self.headers.get("Content-Length",0))>65536:
                self.send_error(400)
                return
            body=self.rfile.read(int(self.headers.get("Content-Length",0)))
            delivery=self.headers.get("X-FSP-Delivery","")
            if not verify(secret,delivery,self.headers.get("X-FSP-Timestamp",""),body,self.headers.get("X-FSP-Signature","")):
                self.send_error(401)
                return
            database.execute("INSERT OR IGNORE INTO receipts VALUES (?,?)",(delivery,int(time.time())))
            database.commit()
            self.send_response(204)
            self.end_headers()
        def log_message(self,*args):
            pass
    HTTPServer(("127.0.0.1",9011),Handler).serve_forever()


if __name__=="__main__":
    main()

"""Portable browser-based desktop launcher. Read-only development build."""
import json
import secrets
import sys
import threading
import tkinter as tk
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from install import Device, inspect, plan, validate_bundle

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
TOKEN = secrets.token_urlsafe(32)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, content, kind='application/json'):
        if not isinstance(content, bytes):
            content = json.dumps(content).encode()
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.headers.get('Host') != '127.0.0.1:%d' % self.server.server_port:
            return self.reply(403, {'error':'Invalid host'})
        if self.path not in ('/', '/ui.html'):
            return self.reply(404, {'error':'Not found'})
        page = (ROOT/'ui.html').read_text(encoding='utf-8')
        page = page.replace('</head>', '<script>window.INSTALLER_TOKEN='+json.dumps(TOKEN)+'</script></head>', 1)
        self.reply(200, page.encode(), 'text/html; charset=utf-8')

    def do_POST(self):
        origin = 'http://127.0.0.1:%d' % self.server.server_port
        if self.headers.get('Origin') != origin or self.headers.get('X-Installer-Token') != TOKEN:
            return self.reply(403, {'error':'Invalid local request'})
        if self.path != '/api/check':
            return self.reply(404, {'error':'Only read-only inspection is available'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024:
                raise ValueError('Invalid request size')
            address = json.loads(self.rfile.read(size))['address']
            manifest = json.loads((ROOT/'manifest.json').read_text())
            validate_bundle(ROOT, manifest)
            result = plan(inspect(Device(address)), manifest)
            self.reply(200, result)
        except (OSError, ValueError, KeyError) as error:
            self.reply(400, {'error':str(error)})

def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d/' % server.server_port
    window = tk.Tk()
    window.title('Stereopsis · Contributor Installer')
    window.geometry('450x205')
    window.configure(bg='#101217')
    tk.Label(window,text='Stereopsis',font=('Segoe UI',23),fg='#e4ed8b',bg='#101217').pack(pady=(18,4))
    tk.Label(window,text='By Mark / FreeMark · Contributions by TBSmike\nRead-only development build. No installation enabled.',fg='#c4c8d0',bg='#101217').pack(pady=5)
    tk.Button(window,text='Open installer',command=lambda:webbrowser.open(url)).pack(pady=12)
    window.after(400, lambda:webbrowser.open(url))
    window.mainloop()
    server.shutdown()

if __name__ == '__main__':
    main()

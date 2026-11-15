# Serves the release zip and the avatar on 127.0.0.1 only, for 15 minutes, so the
# CurseForge page in the browser can pick them up for upload. Nothing is exposed
# to the network: the server listens on the loopback address.
import http.server, os, sys, threading
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {"/avatar.png": os.path.join(root, "icons", "wrc-curseforge-avatar-400.png")}
for f in os.listdir(os.path.join(root, "release")):
    if f.endswith(".zip"):
        FILES["/" + f] = os.path.join(root, "release", f)

class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "https://authors.curseforge.com")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        path = FILES.get(self.path)
        if not path:
            self.send_response(404); self._cors(); self.end_headers(); return
        data = open(path, "rb").read()
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("127.0.0.1", 8765), H)
threading.Timer(900, srv.shutdown).start()
print("serving", sorted(FILES)); sys.stdout.flush()
srv.serve_forever()

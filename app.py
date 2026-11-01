import os, socket, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.environ.get("DATA_DIR", "/data")
LOG = os.path.join(DATA_DIR, "visitas.log")
HOST = socket.gethostname()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, "ok\n")

        if self.path == "/carga":
            fim = time.time() + 0.5
            while time.time() < fim:
                pass
            return self._send(200, f"carga gerada em {HOST}\n")

        try:
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {HOST}\n")
            with open(LOG) as f:
                linhas = f.readlines()
        except OSError as e:
            return self._send(500, f"erro ao acessar {DATA_DIR}: {e}\n")

        self._send(200, f"Pod: {HOST}\nVisitas persistidas: {len(linhas)}\n"
                        f"Ultimas:\n{''.join(linhas[-5:])}")

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

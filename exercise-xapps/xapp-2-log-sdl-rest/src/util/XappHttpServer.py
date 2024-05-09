
# Imports from OSC libraries
from mdclogpy import Level
from mdclogpy import Logger
from ricxappframe.xapp_frame import Xapp

# Imports from other libraries
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, xapp:Xapp, logger:Logger, **kwargs):
        self._xapp = xapp
        self.logger = logger
        super().__init__(*args, **kwargs)

    # Overrides BaseHTTPRequestHandler method for handling HTTP GET requests
    def do_GET(self):
        self.logger.info(f"Received GET request: {self.path}")
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/ric/v1/config":
            self.handle_config()
        elif parsed_path.path == "/ric/v1/health/alive":
            self.handle_alive()

    def handle_config(self):
        self.logger.info("Handling /ric/v1/config: sending the xApp config-file")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self._xapp._config_data).encode())

    def handle_alive(self):
        self.logger.info("Handling /ric/v1/health/alive: sending {\"status\": \"alive\"}")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "alive"}).encode())

class XappHttpServer():
    def __init__(self, logger: Logger, xapp: Xapp):
        self.logger = logger
        self._xapp = xapp
        self._server = None
        self._thread = None

    def start(self, port:int):
        self.logger.info(f"Starting HTTP server on port {port}")
        self._server = HTTPServer(("0.0.0.0", port), lambda *args, **kwargs: RequestHandler(*args, xapp=self._xapp, logger=self.logger, **kwargs))
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.start()
        self.logger.info("HTTP server started")

    def stop(self):
        self.logger.info("Stopping HTTP server")
        if self._server:
            self._server.shutdown()
            self._thread.join()
            self._server = None
            self._thread = None
        self.logger.info("HTTP server stopped")
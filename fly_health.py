#!/usr/bin/env python3
"""Лёгкий HTTP 200 на порту PORT — health check для Render (и др.) в Docker."""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()

    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

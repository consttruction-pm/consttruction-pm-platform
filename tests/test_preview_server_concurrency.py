from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Thread
from urllib.request import urlopen

from construction_pm.preview.server import (
    PreviewRequestHandler,
    PreviewThreadingWSGIServer,
)


def test_preview_server_serves_parallel_asset_requests_without_serial_socket_blocking() -> None:
    both_requests_entered = Barrier(2)

    def application(environ, start_response):
        # A single-threaded HTTP server cannot reach this barrier for the
        # second request. The threaded preview server must allow both handlers
        # to enter before either one can finish.
        both_requests_entered.wait(timeout=5)
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]

    class QuietRequestHandler(PreviewRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass

    server = PreviewThreadingWSGIServer(("127.0.0.1", 0), QuietRequestHandler)
    server.set_app(application)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{server.server_port}/asset.js"

    def fetch() -> bytes:
        with urlopen(url, timeout=7) as response:
            assert response.status == 200
            return response.read()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: fetch(), range(2)))
        assert responses == [b"ok", b"ok"]
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)
        assert not server_thread.is_alive()

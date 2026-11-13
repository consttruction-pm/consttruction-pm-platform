from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from construction_pm.document_scan import (
    DocumentScanError,
    DocumentScanUnavailable,
    ReferenceDocumentScanner,
    ScanVerdict,
)
from construction_pm.document_scan_http import (
    HttpDocumentScanner,
    scanner_from_environment,
)


class _Recorder:
    def __init__(self) -> None:
        self.body = b""
        self.headers: dict[str, str] = {}
        self.path = ""
        self.status = 200
        self.response = b"{}"
        self.redirect_to = ""

    def reset(self) -> None:
        self.__init__()


RECORDER = _Recorder()


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        RECORDER.body = self.rfile.read(length)
        RECORDER.headers = {key.lower(): value for key, value in self.headers.items()}
        RECORDER.path = self.path
        if RECORDER.redirect_to:
            self.send_response(302)
            self.send_header("Location", RECORDER.redirect_to)
            self.end_headers()
            return
        self.send_response(RECORDER.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(RECORDER.response)))
        self.end_headers()
        self.wfile.write(RECORDER.response)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="module")
def scanner_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/scan"
    finally:
        server.shutdown()
        server.server_close()


def _verdict(**payload: object) -> bytes:
    body = {
        "status": "clean",
        "engine": "operational-engine",
        "engine_version": "4.2.1",
        **payload,
    }
    return json.dumps(body).encode("utf-8")


def _scanner(endpoint: str, **kwargs: object) -> HttpDocumentScanner:
    options = {"allow_insecure": True, "timeout": 2.0}
    options.update(kwargs)
    return HttpDocumentScanner(endpoint, **options)  # type: ignore[arg-type]


def test_clean_verdict_posts_bytes_and_identity(scanner_server: str) -> None:
    RECORDER.reset()
    RECORDER.response = _verdict()
    scanner = _scanner(scanner_server, token="scan-token")
    verdict = scanner.scan(b"hello", content_type="text/plain")
    assert verdict == ScanVerdict(
        status="clean",
        engine="operational-engine",
        engine_version="4.2.1",
        detail="",
    )
    assert RECORDER.body == b"hello"
    assert RECORDER.path == "/scan"
    assert RECORDER.headers["authorization"] == "Bearer scan-token"
    assert RECORDER.headers["x-document-content-type"] == "text/plain"
    assert RECORDER.headers["content-type"] == "application/octet-stream"


def test_infected_and_failed_verdicts_are_reported(scanner_server: str) -> None:
    RECORDER.reset()
    RECORDER.response = _verdict(status="infected", detail="signature match")
    assert _scanner(scanner_server).scan(b"bad", content_type="text/plain").status == "infected"

    RECORDER.reset()
    RECORDER.response = _verdict(status="error", detail="engine restart")
    failed = _scanner(scanner_server).scan(b"x", content_type="text/plain")
    assert failed.status == "failed"
    assert failed.detail == "engine restart"


def test_transport_and_status_failures_fail_closed(scanner_server: str) -> None:
    RECORDER.reset()
    RECORDER.status = 503
    RECORDER.response = b'{"status":"clean"}'
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_HTTP_503"):
        _scanner(scanner_server).scan(b"x", content_type="text/plain")

    RECORDER.reset()
    RECORDER.response = b"not json"
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_RESPONSE_INVALID"):
        _scanner(scanner_server).scan(b"x", content_type="text/plain")

    RECORDER.reset()
    RECORDER.response = b'{"status":"clean","engine":"e"}'
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_RESPONSE_INCOMPLETE"):
        _scanner(scanner_server).scan(b"x", content_type="text/plain")

    RECORDER.reset()
    RECORDER.response = _verdict()
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_RESPONSE_TOO_LARGE"):
        _scanner(scanner_server, max_response_bytes=16).scan(
            b"x", content_type="text/plain"
        )


def test_redirects_are_refused(scanner_server: str) -> None:
    RECORDER.reset()
    RECORDER.redirect_to = scanner_server
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_HTTP_302"):
        _scanner(scanner_server).scan(b"x", content_type="text/plain")


def test_unreachable_scanner_is_unavailable() -> None:
    with pytest.raises(DocumentScanUnavailable, match="SCANNER_UNAVAILABLE"):
        _scanner("http://127.0.0.1:9/scan", timeout=0.5).scan(
            b"x", content_type="text/plain"
        )


def test_payload_limits_and_endpoint_validation() -> None:
    with pytest.raises(DocumentScanError, match="SCANNER_ENDPOINT_REQUIRES_HTTPS"):
        HttpDocumentScanner("http://scanner.example/scan")
    with pytest.raises(DocumentScanError, match="INVALID_SCANNER_ENDPOINT"):
        HttpDocumentScanner("ftp://scanner.example/scan", allow_insecure=True)
    with pytest.raises(DocumentScanError, match="INVALID_SCANNER_ENDPOINT"):
        HttpDocumentScanner("https:///scan")
    with pytest.raises(DocumentScanError, match="INVALID_SCANNER_TOKEN"):
        HttpDocumentScanner("https://scanner.example/scan", token="  ")
    with pytest.raises(DocumentScanError, match="INVALID_SCANNER_TIMEOUT"):
        HttpDocumentScanner("https://scanner.example/scan", timeout=0)
    scanner = _scanner("http://scanner.example/scan", max_payload_bytes=2)
    with pytest.raises(DocumentScanError, match="DOCUMENT_SCAN_PAYLOAD_TOO_LARGE"):
        scanner.scan(b"abc", content_type="text/plain")
    with pytest.raises(DocumentScanError, match="INVALID_DOCUMENT_SCAN_PAYLOAD"):
        scanner.scan(b"", content_type="text/plain")


def test_scanner_identity_never_leaks_the_token(scanner_server: str) -> None:
    RECORDER.reset()
    RECORDER.status = 500
    RECORDER.response = b'{"status":"clean","token":"super-secret"}'
    with pytest.raises(DocumentScanUnavailable) as captured:
        _scanner(scanner_server, token="super-secret").scan(
            b"x", content_type="text/plain"
        )
    assert "super-secret" not in str(captured.value)


def test_concurrent_scans_return_independent_verdicts(scanner_server: str) -> None:
    import concurrent.futures

    RECORDER.reset()
    RECORDER.response = _verdict()
    scanner = _scanner(scanner_server)
    payloads = [f"payload-{index}".encode() for index in range(8)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        verdicts = list(
            pool.map(
                lambda payload: scanner.scan(payload, content_type="text/plain"),
                payloads,
            )
        )
    assert [verdict.status for verdict in verdicts] == ["clean"] * len(payloads)


def test_scanner_factory_from_environment() -> None:
    reference = scanner_from_environment({"CONSTRUCTION_PM_SCANNER": "reference"})
    assert isinstance(reference, ReferenceDocumentScanner)

    external = scanner_from_environment(
        {
            "CONSTRUCTION_PM_SCANNER": "external",
            "CONSTRUCTION_PM_SCANNER_ENDPOINT": "https://scanner.example/scan",
            "CONSTRUCTION_PM_SCANNER_TOKEN": "token",
            "CONSTRUCTION_PM_SCANNER_TIMEOUT_SECONDS": "4.5",
        }
    )
    assert isinstance(external, HttpDocumentScanner)
    assert external.endpoint == "https://scanner.example/scan"

    with pytest.raises(DocumentScanError, match="UNCONFIGURED_SCANNER"):
        scanner_from_environment({})
    with pytest.raises(DocumentScanError, match="MISSING_SCANNER_ENDPOINT"):
        scanner_from_environment({"CONSTRUCTION_PM_SCANNER": "external"})
    with pytest.raises(DocumentScanError, match="INVALID_SCANNER_TIMEOUT"):
        scanner_from_environment(
            {
                "CONSTRUCTION_PM_SCANNER": "external",
                "CONSTRUCTION_PM_SCANNER_ENDPOINT": "https://scanner.example/scan",
                "CONSTRUCTION_PM_SCANNER_TIMEOUT_SECONDS": "soon",
            }
        )

"""Read-only live smoke checks for the Render approval API.

Only GET requests are made. No credentials are sent and no proposal is created,
reviewed, or executed. Expected auth response is 401 (credentials configured)
or 503 (service deliberately fails closed while auth is unconfigured).
"""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://ai-employee-approval-api-test.onrender.com"
REQUEST_TIMEOUT_SECONDS = 45
NETWORK_ATTEMPTS = 2


def get(path: str):
    """GET with one retry for transient network/cold-start timeouts."""
    last_error = None
    for attempt in range(NETWORK_ATTEMPTS):
        request = Request(f"{BASE_URL}{path}", method="GET")
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < NETWORK_ATTEMPTS:
                time.sleep(2)
    raise RuntimeError(
        f"GET {path} failed after {NETWORK_ATTEMPTS} attempts: {last_error}"
    )


def main() -> int:
    try:
        status, body = get("/health")
        assert status == 200, f"/health returned HTTP {status}"
        health = json.loads(body)
        assert health.get("status") == "ok", f"Unexpected health payload: {health}"
        assert health.get("execution") == "disabled", (
            f"External execution is not confirmed disabled: {health}"
        )
        print("PASS: /health is 200 and execution is disabled")

        status, _ = get("/proposals")
        assert status in (401, 503), (
            f"Unauthenticated GET /proposals returned unexpected HTTP {status}; "
            "expected 401 (auth configured) or 503 (fail-closed configuration)"
        )
        print(f"PASS: unauthenticated GET /proposals denied with HTTP {status}")

        status, _ = get("/docs")
        assert status == 404, f"/docs should be disabled, got HTTP {status}"
        print("PASS: API docs route is disabled (404)")
        print("PASS: read-only live smoke checks complete; no records were changed")
        return 0
    except (AssertionError, URLError, TimeoutError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: live smoke check: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

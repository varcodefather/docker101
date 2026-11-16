import sys
import time
import urllib.request

address = sys.argv[1]
deadline = time.monotonic() + 20
last_error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(address, timeout=2) as response:
            body = response.read().decode()
            assert response.status == 200 and "Hello from CI" in body, "App returned unexpected content"
            assert "Request ID:" in body, "App response missing request identity"
            print("Smoke check passed: expected greeting and request identity")
            break
    except (OSError, AssertionError) as error:
        last_error = error
        time.sleep(.5)
else:
    raise SystemExit(f"Smoke check failed: {last_error}")

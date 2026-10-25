"""
Verifies frontend assets, element IDs, HTML/JS cross-references, and server endpoints.
"""
import urllib.request
import re
import json

BASE = "http://127.0.0.1:8000"

def test_frontend():
    print("Testing Frontend Asset Delivery and Integration...")

    # 1. Test index.html
    req = urllib.request.urlopen(f"{BASE}/")
    assert req.status == 200, f"Index failed: {req.status}"
    html = req.read().decode("utf-8")
    assert "DataWise | Event Registration Data Quality Hub" in html, "Title missing in HTML"
    assert "config.js" in html, "config.js reference missing in index.html"
    assert "app.js" in html, "app.js reference missing in index.html"
    print("✓ index.html delivered and contains proper asset references")

    # 2. Test static css & js
    req_css = urllib.request.urlopen(f"{BASE}/styles.css")
    assert req_css.status == 200, "styles.css failed"
    css = req_css.read().decode("utf-8")
    assert len(css) > 1000, "styles.css appears empty"
    print("✓ styles.css delivered (200 OK)")

    req_cfg = urllib.request.urlopen(f"{BASE}/config.js")
    assert req_cfg.status == 200, "config.js failed"
    print("✓ config.js delivered (200 OK)")

    req_js = urllib.request.urlopen(f"{BASE}/app.js")
    assert req_js.status == 200, "app.js failed"
    js = req_js.read().decode("utf-8")
    assert len(js) > 1000, "app.js appears empty"
    print("✓ app.js delivered (200 OK)")

    # 3. Check that IDs referenced by $('...') in app.js exist in index.html
    # Extract $('...') calls from app.js
    id_calls = set(re.findall(r"\$\(['\"]([a-zA-Z0-9_\-]+)['\"]\)", js))
    
    # Extract IDs defined in index.html
    html_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', html))
    
    # We check if critical IDs from app.js are in index.html
    critical_ids = [
        "total", "clean", "review", "invalid",
        "cleanRateBadge", "reviewRateBadge", "invalidRateBadge",
        "side-total-badge", "side-clean-badge", "side-review-badge", "side-invalid-badge",
        "tabAllBadge", "tabCleanBadge", "tabReviewBadge", "tabInvalidBadge",
        "heroCleanScore", "heroGradeBadge", "heroProgressBar",
        "run", "headerRunBtn", "emptyStateRunBtn", "clearBtn",
        "sample320Btn", "templateBtn", "file",
        "backendStatusPill", "apiModal", "apiModalCloseBtn", "backendUrlInput",
        "apiTestBtn", "apiSaveBtn", "apiResetLocalBtn",
        "downloadCleanBtn", "downloadReviewBtn", "downloadInvalidBtn", "downloadSummaryBtn",
        "body", "tableInfo", "prevPageBtn", "nextPageBtn",
        "recordModal", "modalCloseBtn", "modalRegId", "modalFullName", "modalEventName"
    ]

    missing_ids = []
    for cid in critical_ids:
        if cid not in html_ids:
            missing_ids.append(cid)
    
    if missing_ids:
        print(f"✗ Missing element IDs in index.html: {missing_ids}")
        assert False, f"Missing IDs: {missing_ids}"
    else:
        print(f"✓ All {len(critical_ids)} critical element IDs confirmed present in index.html!")

    # 4. Check API response headers & format from live server
    for endpoint, method in [
        ("/api/summary", "GET"),
        ("/api/records?type=all", "GET"),
        ("/api/health", "GET"),
    ]:
        req_api = urllib.request.Request(f"{BASE}{endpoint}", method=method)
        with urllib.request.urlopen(req_api) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, f"Expected JSON, got {ct}"
            cors = resp.headers.get("Access-Control-Allow-Origin", "")
            assert cors == "*", f"Expected CORS header, got {cors}"
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("ok") is True, f"Response ok flag is not True: {data}"
            print(f"✓ {method} {endpoint} returned 200 OK with application/json and CORS header")

    print("\nALL FRONTEND INTEGRATION CHECKS PASSED!")

if __name__ == "__main__":
    test_frontend()

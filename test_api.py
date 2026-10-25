"""
DataWise Quality Hub - Backend API Test Suite
Tests all endpoints, HTTP methods, status codes, CORS headers, error conditions, and CSV exports.
"""

import threading
import time
import urllib.request
import urllib.error
import json
from pathlib import Path
from http.server import ThreadingHTTPServer
from server import H

SERVER_PORT = 8089
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"

def run_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", SERVER_PORT), H)
    httpd.serve_forever()

def request(method, path, body=None, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = headers or {}
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"
        elif isinstance(body, str):
            data = body.encode("utf-8")
        elif isinstance(body, bytes):
            data = body
    
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            is_json = "application/json" in content_type
            parsed = json.loads(raw.decode("utf-8")) if is_json else raw
            return resp.status, resp.headers, parsed
    except urllib.error.HTTPError as err:
        content_type = err.headers.get("Content-Type", "")
        raw = err.read()
        is_json = "application/json" in content_type
        parsed = json.loads(raw.decode("utf-8")) if is_json else raw
        return err.code, err.headers, parsed

def run_all_tests():
    print("=" * 70)
    print(" STARTING DATAWISE API TEST SUITE")
    print("=" * 70)

    # Start server in background thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)

    tests_run = 0
    tests_passed = 0
    tests_failed = 0

    def assert_test(name, condition, details=""):
        nonlocal tests_run, tests_passed, tests_failed
        tests_run += 1
        if condition:
            tests_passed += 1
            print(f"  [PASS] {name}")
        else:
            tests_failed += 1
            print(f"  [FAIL] {name} - {details}")

    # 1. Health Endpoint
    status, headers, body = request("GET", "/api/health")
    assert_test("GET /api/health returns 200 OK with JSON", status == 200 and body.get("ok") is True)
    assert_test("Health endpoint includes CORS header", headers.get("Access-Control-Allow-Origin") == "*")

    # 2. CORS Preflight (OPTIONS)
    status, headers, _ = request("OPTIONS", "/api/upload", headers={
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    })
    assert_test("OPTIONS /api/upload returns 204 No Content", status == 204)
    assert_test("OPTIONS returns CORS methods and headers", 
                "POST" in headers.get("Access-Control-Allow-Methods", "") and
                "Content-Type" in headers.get("Access-Control-Allow-Headers", ""))

    # 3. GET /api/summary (Dashboard Initialization)
    status, headers, body = request("GET", "/api/summary")
    assert_test("GET /api/summary returns 200 OK", status == 200)
    assert_test("GET /api/summary returns valid JSON with ok=True", body.get("ok") is True)
    assert_test("Summary JSON contains total_records field", "total_records" in body)

    # 4. POST /api/load_sample?type=320 (Load 320-record CSV)
    status, headers, body = request("POST", "/api/load_sample?type=320")
    assert_test("POST /api/load_sample?type=320 returns 200 OK", status == 200)
    assert_test("Load sample returned ok=True", body.get("ok") is True)
    sum_data = body.get("summary", {})
    assert_test("320 dataset has total_records == 320", sum_data.get("total_records") == 320, f"Got {sum_data.get('total_records')}")
    assert_test("320 dataset clean_records > 0", sum_data.get("clean_records", 0) > 0)
    assert_test("320 dataset review_records > 0", sum_data.get("review_records", 0) > 0)
    assert_test("320 dataset invalid_records > 0", sum_data.get("invalid_records", 0) > 0)

    # 5. GET /api/records?type=all
    status, headers, body = request("GET", "/api/records?type=all&limit=50000")
    assert_test("GET /api/records?type=all returns 200 OK", status == 200)
    assert_test("Records type=all has total == 320", body.get("total") == 320, f"Got {body.get('total')}")
    assert_test("Records rows list has 320 items", len(body.get("rows", [])) == 320)

    # 6. GET /api/records for individual types
    st_clean, _, b_clean = request("GET", "/api/records?type=clean")
    st_rev, _, b_rev = request("GET", "/api/records?type=review")
    st_inv, _, b_inv = request("GET", "/api/records?type=invalid")
    assert_test("GET /api/records?type=clean returns 200 OK", st_clean == 200 and len(b_clean.get("rows", [])) == 306)
    assert_test("GET /api/records?type=review returns 200 OK", st_rev == 200 and len(b_rev.get("rows", [])) == 8)
    assert_test("GET /api/records?type=invalid returns 200 OK", st_inv == 200 and len(b_inv.get("rows", [])) == 6)

    # 7. POST /api/process (Run Quality Audit)
    status, headers, body = request("POST", "/api/process")
    assert_test("POST /api/process returns 200 OK", status == 200)
    assert_test("Process audit returned ok=True", body.get("ok") is True)
    assert_test("Process audit returned summary with 320 records", body.get("summary", {}).get("total_records") == 320)

    # 8. POST /api/upload (CSV Upload)
    sample_upload = (
        "registration_id,person_id,full_name,email,phone,event_name\n"
        "UP001,P9001,Test User One,test1@example.com,9876543210,AI Seminar\n"
        "UP002,P9002,Test User Two,test2@example.com,9876543211,Python Workshop\n"
    )
    status, headers, body = request("POST", "/api/upload", body=sample_upload, headers={"Content-Type": "text/csv;charset=utf-8"})
    assert_test("POST /api/upload returns 200 OK", status == 200)
    assert_test("Upload returned uploaded count == 2", body.get("uploaded") == 2, f"Got {body.get('uploaded')}")
    assert_test("Upload summary total_records == 2", body.get("summary", {}).get("total_records") == 2)

    # 9. POST /api/clear (Clear Records)
    status, headers, body = request("POST", "/api/clear")
    assert_test("POST /api/clear returns 200 OK", status == 200)
    assert_test("Clear returned ok=True", body.get("ok") is True)
    assert_test("Clear summary total_records == 0", body.get("summary", {}).get("total_records") == 0)

    # Verify records endpoint returns 0 after clear
    status, headers, body = request("GET", "/api/records?type=all")
    assert_test("GET /api/records after clear returns 0 total", body.get("total") == 0)

    # 10. Reload 320 sample dataset for exports
    status, _, _ = request("POST", "/api/load_sample?type=320")
    assert_test("Reload 320 sample dataset succeeds", status == 200)

    # 11. GET /api/download/<file> (Exports)
    for fn in ["clean_records.csv", "review_list.csv", "invalid_records.csv", "summary.json"]:
        status, headers, body = request("GET", f"/api/download/{fn}")
        expected_ct = "application/json" if fn.endswith(".json") else "text/csv"
        assert_test(f"Download {fn} returns 200 OK with correct Content-Type", 
                    status == 200 and expected_ct in headers.get("Content-Type", ""),
                    f"Status: {status}, Content-Type: {headers.get('Content-Type')}")
        assert_test(f"Download {fn} includes Content-Disposition attachment", 
                    f'attachment; filename="{fn}"' in headers.get("Content-Disposition", ""))

    # 12. Error Handling & Consistent JSON format on all error cases
    # 12a. Unknown GET endpoint
    status, headers, body = request("GET", "/api/unknown_route")
    assert_test("Unknown GET /api/* returns 404 Not Found", status == 404)
    assert_test("Unknown GET /api/* returns JSON, NOT HTML", isinstance(body, dict) and body.get("ok") is False)

    # 12b. Unknown POST endpoint
    status, headers, body = request("POST", "/api/unknown_action")
    assert_test("Unknown POST /api/* returns 404 Not Found", status == 404)
    assert_test("Unknown POST /api/* returns JSON, NOT HTML", isinstance(body, dict) and body.get("ok") is False)

    # 12c. Invalid type in /api/records
    status, headers, body = request("GET", "/api/records?type=invalid_type_name")
    assert_test("Invalid records type returns 400 Bad Request JSON", status == 400 and body.get("ok") is False)

    # 12d. Nonexistent download file
    status, headers, body = request("GET", "/api/download/secrets.env")
    assert_test("Unauthorized/nonexistent download returns 404 JSON", status == 404 and body.get("ok") is False)

    # 12e. Empty upload
    status, headers, body = request("POST", "/api/upload", body="")
    assert_test("Empty upload returns 400 Bad Request JSON", status == 400 and body.get("ok") is False)

    print("=" * 70)
    print(f" TEST RESULTS: {tests_passed}/{tests_run} PASSED ({tests_failed} FAILED)")
    print("=" * 70)

    if tests_failed > 0:
        exit(1)

if __name__ == "__main__":
    run_all_tests()

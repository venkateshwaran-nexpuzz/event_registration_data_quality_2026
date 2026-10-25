from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from io import StringIO
import sys
import os
import csv
import json
import re

ROOT = Path(__file__).resolve().parent
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from src.g11_tool import read_csv, process_file  # type: ignore # noqa: E402
except ImportError:
    from g11_tool import read_csv, process_file  # type: ignore # noqa: E402

OUT = ROOT / "outputs"
DATA = ROOT / "data"
WEB = ROOT / "web"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
WEB.mkdir(exist_ok=True)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def sendjson(self, obj, status=200):
        b = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)

        if p.path == "/api/health":
            self.sendjson({"ok": True, "status": "healthy", "service": "datawise-api"}, 200)
            return

        if p.path == "/api/summary":
            f = OUT / "summary.json"
            if f.exists():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        data["ok"] = True
                    self.sendjson(data, 200)
                    return
                except Exception as e:
                    self.sendjson({"ok": False, "error": f"Failed to read summary file: {str(e)}"}, 500)
                    return

            reg_file = DATA / "registrations.csv"
            if reg_file.exists() and reg_file.stat().st_size > 65:
                try:
                    summary = process_file(reg_file, OUT)
                    summary["ok"] = True
                    self.sendjson(summary, 200)
                    return
                except Exception as e:
                    self.sendjson({"ok": False, "error": str(e)}, 500)
                    return

            empty_summary = {
                "ok": True,
                "total_records": 0,
                "valid_records": 0,
                "invalid_records": 0,
                "review_records": 0,
                "clean_records": 0,
                "similar_name_pairs": 0,
                "clean_rate": 0,
                "events": {},
                "issues": {},
                "dimensions": {
                    "completeness": 100,
                    "validity": 100,
                    "uniqueness": 100,
                    "consistency": 100.0
                },
                "readiness": {
                    "badge_ready": 0,
                    "email_ready": 0,
                    "sms_ready": 0,
                    "duplicate_risk": "Low"
                },
                "message": "No records loaded. Load a sample dataset or upload a CSV."
            }
            self.sendjson(empty_summary, 200)
            return

        if p.path == "/api/records":
            qs = parse_qs(p.query)
            typ = qs.get("type", ["all"])[0]
            lim_str = qs.get("limit", [None])[0]
            lim = int(lim_str) if lim_str and lim_str.isdigit() else 50000

            if typ == "all":
                all_rows = []
                for st, fn in [("clean", "clean_records.csv"), ("review", "review_list.csv"), ("invalid", "invalid_records.csv")]:
                    target = OUT / fn
                    if target.exists():
                        for row in read_csv(target):
                            row["_status"] = st
                            all_rows.append(row)
                self.sendjson({"ok": True, "type": "all", "rows": all_rows[:lim], "total": len(all_rows)}, 200)
                return

            file_map = {
                "clean": "clean_records.csv",
                "review": "review_list.csv",
                "invalid": "invalid_records.csv"
            }
            if typ not in file_map:
                self.sendjson({"ok": False, "error": f"Invalid type '{typ}'. Must be 'clean', 'review', 'invalid', or 'all'."}, 400)
                return

            fn = file_map[typ]
            target = OUT / fn
            if not target.exists():
                self.sendjson({"ok": True, "type": typ, "rows": [], "total": 0}, 200)
                return

            rows = read_csv(target)
            for row in rows:
                row["_status"] = typ
            self.sendjson({"ok": True, "type": typ, "rows": rows[:lim], "total": len(rows)}, 200)
            return

        if p.path.startswith("/api/download/"):
            name = p.path.rsplit("/", 1)[-1]
            allowed_files = {
                "clean_records.csv": "text/csv; charset=utf-8",
                "review_list.csv": "text/csv; charset=utf-8",
                "invalid_records.csv": "text/csv; charset=utf-8",
                "summary.json": "application/json; charset=utf-8"
            }
            if name not in allowed_files or not (OUT / name).exists():
                self.sendjson({"ok": False, "error": f"Download file '{name}' not found. Run quality audit first."}, 404)
                return

            b = (OUT / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", allowed_files[name])
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(b)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b)
            return

        if p.path.startswith("/api/"):
            self.sendjson({"ok": False, "error": f"API endpoint not found: GET {p.path}"}, 404)
            return

        if p.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        p = urlparse(self.path)

        if p.path == "/api/load_sample":
            try:
                sample_type = "320"
                qs = parse_qs(p.query)
                if "type" in qs:
                    sample_type = qs["type"][0]
                elif "sample" in qs:
                    sample_type = qs["sample"][0]
                else:
                    n = int(self.headers.get("Content-Length", 0))
                    if n > 0:
                        try:
                            body = json.loads(self.rfile.read(n).decode("utf-8"))
                            sample_type = str(body.get("type") or body.get("sample") or sample_type)
                        except Exception:
                            pass

                candidates = [
                    DATA / f"registrations_{sample_type}.csv",
                    DATA / f"registrations_{sample_type}_backup.csv",
                    DATA / "registrations_320.csv" if sample_type == "320" else None,
                    DATA / "registrations_320_backup.csv" if sample_type == "320" else None,
                    DATA / "registrations_3000.csv" if sample_type == "3000" else None,
                ]
                src_file = None
                for cand in candidates:
                    if cand and cand.exists():
                        src_file = cand
                        break

                if not src_file:
                    self.sendjson({"ok": False, "error": f"Sample dataset '{sample_type}' not found on server."}, 404)
                    return

                (DATA / "registrations.csv").write_bytes(src_file.read_bytes())
                summary = process_file(DATA / "registrations.csv", OUT)
                summary["ok"] = True
                self.sendjson({"ok": True, "type": sample_type, "summary": summary}, 200)
            except Exception as e:
                self.sendjson({"ok": False, "error": f"Failed to load sample: {str(e)}"}, 500)
            return

        if p.path == "/api/clear":
            try:
                header = "registration_id,person_id,full_name,email,phone,event_name\n"
                (DATA / "registrations.csv").write_text(header, encoding="utf-8")
                summary = process_file(DATA / "registrations.csv", OUT)
                summary["ok"] = True
                self.sendjson({"ok": True, "message": "Records cleared successfully", "summary": summary}, 200)
            except Exception as e:
                self.sendjson({"ok": False, "error": f"Failed to clear records: {str(e)}"}, 500)
            return

        if p.path == "/api/process":
            try:
                reg_file = DATA / "registrations.csv"
                if not reg_file.exists():
                    if (DATA / "registrations_320.csv").exists():
                        (DATA / "registrations.csv").write_bytes((DATA / "registrations_320.csv").read_bytes())
                    else:
                        (DATA / "registrations.csv").write_text("registration_id,person_id,full_name,email,phone,event_name\n", encoding="utf-8")
                summary = process_file(DATA / "registrations.csv", OUT)
                summary["ok"] = True
                self.sendjson({"ok": True, "message": "Quality audit completed successfully", "summary": summary}, 200)
            except Exception as e:
                self.sendjson({"ok": False, "error": f"Audit process failed: {str(e)}"}, 500)
            return

        if p.path == "/api/upload":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n == 0:
                    self.sendjson({"ok": False, "error": "Empty upload payload."}, 400)
                    return
                if n > 15 * 1024 * 1024:
                    self.sendjson({"ok": False, "error": "Maximum upload size is 15 MB."}, 413)
                    return

                raw_bytes = self.rfile.read(n)
                content_type = self.headers.get("Content-Type", "")

                raw_text = None
                if "multipart/form-data" in content_type:
                    boundary = None
                    for part in content_type.split(";"):
                        part = part.strip()
                        if part.startswith("boundary="):
                            boundary = part.split("=", 1)[1].strip('"').encode()
                            break
                    if boundary:
                        parts = raw_bytes.split(b"--" + boundary)
                        for part in parts:
                            if b"filename=" in part:
                                header_end = part.find(b"\r\n\r\n")
                                if header_end != -1:
                                    file_data = part[header_end + 4:].rstrip(b"\r\n--")
                                    for enc in ("utf-8-sig", "utf-8", "latin1"):
                                        try:
                                            raw_text = file_data.decode(enc)
                                            break
                                        except Exception:
                                            pass
                                    break
                if raw_text is None:
                    for enc in ("utf-8-sig", "utf-8", "latin1"):
                        try:
                            raw_text = raw_bytes.decode(enc)
                            break
                        except Exception:
                            pass
                if raw_text is None:
                    raw_text = raw_bytes.decode("utf-8-sig", errors="replace")

                reader = csv.DictReader(StringIO(raw_text))
                if not reader.fieldnames:
                    self.sendjson({"ok": False, "error": "Uploaded file appears empty or is not a valid CSV."}, 400)
                    return

                def clean_k(k):
                    return re.sub(r"[\s_\-]+", "", str(k or "").lower())

                aliases = {
                    "registration_id": ["registrationid", "regid", "ticketid", "orderid", "id", "bookingid", "regno"],
                    "person_id": ["personid", "participantid", "userid", "attendeeid", "pid", "memberid"],
                    "full_name": ["fullname", "name", "attendeename", "participantname", "studentname", "attendee"],
                    "email": ["email", "emailaddress", "mail", "electronicmail", "emailid"],
                    "phone": ["phone", "phonenumber", "mobile", "mobilenumber", "contact", "contactnumber", "telephone", "cell"],
                    "event_name": ["eventname", "event", "track", "workshop", "session", "conference"]
                }
                header_map = {}
                for orig in reader.fieldnames:
                    if orig is None:
                        continue
                    ck = clean_k(orig)
                    for std, alist in aliases.items():
                        if ck == clean_k(std) or ck in alist:
                            header_map[orig] = std
                            break

                rows = []
                for idx, row in enumerate(reader):
                    item = {}
                    for orig, val in row.items():
                        if orig in header_map:
                            std_key = header_map[orig]
                            item[std_key] = (val or "").strip()
                    if not item.get("registration_id"):
                        item["registration_id"] = f"R{idx+1:04d}"
                    if not item.get("person_id"):
                        item["person_id"] = f"P{idx+1:04d}"
                    if not item.get("full_name"):
                        item["full_name"] = ""
                    if not item.get("email"):
                        item["email"] = ""
                    if not item.get("phone"):
                        item["phone"] = ""
                    if not item.get("event_name"):
                        item["event_name"] = "General Event"
                    rows.append(item)

                if not rows:
                    self.sendjson({"ok": False, "error": "No data rows found in uploaded CSV file."}, 400)
                    return

                fieldnames = ["registration_id", "person_id", "full_name", "email", "phone", "event_name"]
                with open(DATA / "registrations.csv", "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    w.writerows(rows)

                summary = process_file(DATA / "registrations.csv", OUT)
                summary["ok"] = True
                self.sendjson({"ok": True, "uploaded": len(rows), "summary": summary}, 200)
            except Exception as e:
                self.sendjson({"ok": False, "error": f"Upload failed: {str(e)}"}, 500)
            return

        if p.path.startswith("/api/"):
            self.sendjson({"ok": False, "error": f"API endpoint not found: POST {p.path}"}, 404)
            return

        self.sendjson({"ok": False, "error": f"Unknown endpoint: {p.path}"}, 404)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0" if (os.environ.get("PORT") or os.environ.get("RENDER")) else "127.0.0.1")
    print(f"G11 DataWise running at http://{host}:{port}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()

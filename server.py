from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from io import StringIO
import sys,csv,json,re
ROOT=Path(__file__).resolve().parent
for p in (ROOT, ROOT/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
try:
    from src.g11_tool import read_csv, process_file  # type: ignore # noqa: E402
except ImportError:
    from g11_tool import read_csv, process_file  # type: ignore # noqa: E402
OUT=ROOT/"outputs";DATA=ROOT/"data";WEB=ROOT/"web";OUT.mkdir(exist_ok=True)
class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(WEB),**kw)
 def sendjson(self,obj,status=200):
  b=json.dumps(obj).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  p=urlparse(self.path)
  if p.path=="/api/summary":
   f=OUT/"summary.json";self.sendjson(json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"message":"Run analysis to begin."});return
  if p.path=="/api/records":
   qs=parse_qs(p.query);typ=qs.get("type",["clean"])[0];lim_str=qs.get("limit",[None])[0]
   lim=int(lim_str) if lim_str and lim_str.isdigit() else 50000
   if typ=="all":
    all_rows=[]
    for st,fn in [("clean","clean_records.csv"),("review","review_list.csv"),("invalid","invalid_records.csv")]:
     if (OUT/fn).exists():
      for row in read_csv(OUT/fn):
       row["_status"]=st;all_rows.append(row)
    self.sendjson({"rows":all_rows[:lim],"total":len(all_rows)});return
   name={"clean":"clean_records.csv","review":"review_list.csv","invalid":"invalid_records.csv"}.get(typ)
   if not name or not (OUT/name).exists():self.sendjson({"rows":[],"total":0});return
   r=read_csv(OUT/name)
   for row in r:row["_status"]=typ
   self.sendjson({"rows":r[:lim],"total":len(r)});return
  if p.path.startswith("/api/download/"):
   name=p.path.rsplit("/",1)[-1]
   if name not in {"clean_records.csv","review_list.csv","invalid_records.csv","summary.json"} or not (OUT/name).exists():self.sendjson({"error":"Run analysis first."},404);return
   b=(OUT/name).read_bytes();self.send_response(200);self.send_header("Content-Disposition",f'attachment; filename="{name}"');self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b);return
  if p.path=="/":self.path="/index.html"
  super().do_GET()
 def do_POST(self):
  p=urlparse(self.path)
  if p.path=="/api/load_sample":
   try:
    qs=parse_qs(p.query);sample_type=qs.get("type",["3000"])[0]
    src_file=DATA/f"registrations_{sample_type}.csv" if (DATA/f"registrations_{sample_type}.csv").exists() else (DATA/"registrations_320_backup.csv" if sample_type=="320" else DATA/"registrations_3000.csv")
    if src_file.exists():
     (DATA/"registrations.csv").write_bytes(src_file.read_bytes())
    self.sendjson({"ok":True,"type":sample_type,"summary":process_file(DATA/"registrations.csv",OUT)})
   except Exception as e:self.sendjson({"ok":False,"error":str(e)},500)
   return
  if p.path=="/api/clear":
   try:
    (DATA/"registrations.csv").write_text("registration_id,person_id,full_name,email,phone,event_name\n",encoding="utf-8")
    self.sendjson({"ok":True,"summary":process_file(DATA/"registrations.csv",OUT)})
   except Exception as e:self.sendjson({"ok":False,"error":str(e)},500)
   return
  if p.path=="/api/process":
   try:self.sendjson({"ok":True,"summary":process_file(DATA/"registrations.csv",OUT)})
   except Exception as e:self.sendjson({"ok":False,"error":str(e)},500)
   return
  if p.path=="/api/upload":
   try:
    n=int(self.headers.get("Content-Length","0"))
    if n>8000000:self.sendjson({"error":"Maximum upload is 8 MB."},413);return
    raw_text=self.rfile.read(n).decode("utf-8-sig")
    reader=csv.DictReader(StringIO(raw_text))
    if not reader.fieldnames:
     self.sendjson({"error":"Uploaded file appears empty or is not a valid CSV."},400);return

    def clean_k(k):return re.sub(r"[\s_\-]+","",str(k or "").lower())
    aliases={
     "registration_id":["registrationid","regid","ticketid","orderid","id","bookingid","regno"],
     "person_id":["personid","participantid","userid","attendeeid","pid","memberid"],
     "full_name":["fullname","name","attendeename","participantname","studentname","attendee"],
     "email":["email","emailaddress","mail","electronicmail","emailid"],
     "phone":["phone","phonenumber","mobile","mobilenumber","contact","contactnumber","telephone","cell"],
     "event_name":["eventname","event","track","workshop","session","conference"]
    }
    header_map={}
    for orig in reader.fieldnames:
     ck=clean_k(orig)
     for std,alist in aliases.items():
      if ck==clean_k(std) or ck in alist:
       header_map[orig]=std;break

    rows=[]
    for idx,row in enumerate(reader):
     item={}
     for orig,val in row.items():
      std_key=header_map.get(orig)
      if std_key:item[std_key]=(val or "").strip()
     if not item.get("registration_id"):item["registration_id"]=f"R{idx+1:04d}"
     if not item.get("person_id"):item["person_id"]=f"P{idx+1:04d}"
     if not item.get("full_name"):item["full_name"]=""
     if not item.get("email"):item["email"]=""
     if not item.get("phone"):item["phone"]=""
     if not item.get("event_name"):item["event_name"]="General Event"
     rows.append(item)

    fieldnames=["registration_id","person_id","full_name","email","phone","event_name"]
    with open(DATA/"registrations.csv","w",newline="",encoding="utf-8") as f:
     w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(rows)
    self.sendjson({"ok":True,"uploaded":len(rows),"summary":process_file(DATA/"registrations.csv",OUT)})
   except Exception as e:self.sendjson({"error":str(e)},500)
   return
  self.sendjson({"error":"Unknown endpoint"},404)
if __name__=="__main__":
 print("G11 DataWise running at http://127.0.0.1:8000");print("Press Ctrl+C to stop.")
 ThreadingHTTPServer(("127.0.0.1",8000),H).serve_forever()

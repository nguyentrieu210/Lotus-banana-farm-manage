"""Lotus attendance file bridge (optional farm-side adapter).

Read a CSV file exported by a clock and send event-only data to the secure
Lotus endpoint. Configure API credentials in environment variables, never in
this script. Idempotent: re-running a file does not duplicate punches. Does
NOT fetch/store fingerprint or facial templates and does NOT approve workdays.

CSV headers: device_user_id,punched_at,log_type,source_event_id
Run on the farm computer (with Python 3): python lotus_attendance_bridge.py log.csv
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REQUIRED=("LOTUS_URL","LOTUS_API_KEY","LOTUS_API_SECRET",
          "LOTUS_COMPANY","LOTUS_DEVICE")

def send(csv_path):
    config={key:os.getenv(key,"").strip() for key in REQUIRED}
    missing=[key for key,value in config.items() if not value]
    if missing:raise ValueError("Chưa cài biến môi trường: "+", ".join(missing))
    host=config["LOTUS_URL"].rstrip("/")
    if not host.startswith("https://"):
        raise ValueError("Chỉ gửi qua HTTPS.")
    with open(csv_path,"r",encoding="utf-8-sig",newline="") as fp:
        reader=csv.DictReader(fp)
        required={"device_user_id","punched_at"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Thiếu cột device_user_id hoặc punched_at.")
        values=[{
            "device_user_id":row["device_user_id"].strip(),
            "punched_at":row["punched_at"].strip(),
            "log_type":(row.get("log_type") or "").strip(),
            "source_event_id":(row.get("source_event_id") or "").strip()
        } for row in reader if (row.get("device_user_id") or "").strip()]
    if not values:
        return {"created":0,"duplicate":0}
    summary={"created":0,"duplicate":0}
    endpoint=host+"/api/method/lotus_farm.hr_operations.ingest_device_events"
    token=config["LOTUS_API_KEY"]+":"+config["LOTUS_API_SECRET"]
    for start in range(0,len(values),500):
        payload={
            "company":config["LOTUS_COMPANY"],
            "device":config["LOTUS_DEVICE"],
            "events":values[start:start+500]
        }
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        req=urllib.request.Request(endpoint,data=data,headers={
            "Authorization":"token "+token,
            "Content-Type":"application/json",
            "Accept":"application/json"
        },method="POST")
        try:
            with urllib.request.urlopen(req,timeout=45) as response:
                reply=json.loads(response.read())
        except urllib.error.HTTPError as err:
            raise RuntimeError("HTTP "+str(err.code)+
                               ": server refused the batch; no local data deleted.") from None
        result=reply.get("message")
        if not isinstance(result,dict):
            raise RuntimeError("Máy chủ trả kết quả không hợp lệ.")
        summary["created"]+=int(result.get("created",0))
        summary["duplicate"]+=int(result.get("duplicate",0))
    return summary

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python lotus_attendance_bridge.py log.csv")
    try:
        print(json.dumps(send(sys.argv[1]),ensure_ascii=False))
    except Exception as e:
        raise SystemExit("Lỗi đồng bộ: "+str(e))

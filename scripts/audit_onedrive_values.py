"""Read-only audit of connector-extracted OneDrive values, NOT original XLSX bytes."""
import csv, io, json, hashlib, os, re
from pathlib import Path
from decimal import Decimal, InvalidOperation
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"audit-output"
OUT.mkdir(exist_ok=True)
def parts(name):
    text=(ROOT/"tests/fixtures/onedrive-values"/(name+".csv")).read_text()
    return [list(csv.reader(io.StringIO(p))) for p in text.split("\f")]
def table(name, index, required):
    records=parts(name)[index]
    for i,row in enumerate(records):
        if set(required)<=set(row):
            assert len(row)==len(set(row)), "Duplicate extraction headers"
            headers=row[1:]
            return [dict(zip(headers,r[1:])) for r in records[i+1:] if any(r[1:])]
    raise AssertionError("Expected headers missing: "+name)
def num(v):
    if v is None or not v.strip() or v.strip()=="-": return None
    try:
        n=Decimal(v)
        return n if n.is_finite() else None
    except InvalidOperation: return None
def example(row, fields):
    return {f:row.get(f) for f in fields}
issues=[]
def flag(code,count,examples=None):
    if count: issues.append(dict(code=code,count=count,examples=examples or []))
labor=table("labor",2,["NGÀY","NÔNG TRƯỜNG","HẠNG MỤC","HIỆN HỮU CUỐI NGÀY","ĐI LÀM","VẮNG"])
detail=[r for r in labor if r.get("NGÀY") and r.get("NÔNG TRƯỜNG") and not r.get("HẠNG MỤC","").strip().casefold().startswith("tổng")]
fields=["NGÀY","XÍ NGHIỆP","NÔNG TRƯỜNG","HẠNG MỤC","HIỆN HỮU CUỐI NGÀY","ĐI LÀM","VẮNG"]
neg=[]; imbalance=[]; incomplete=[]
for r in detail:
    values=[num(r.get(f)) for f in ["HIỆN HỮU CUỐI NGÀY","ĐI LÀM","VẮNG"]]
    if any(v is not None and v<0 for v in values):neg.append(r)
    if all(v is not None for v in values) and abs(values[0]-values[1]-values[2])>Decimal("0.000001"):imbalance.append(r)
    if any(v is None for v in values):incomplete.append(r)
keys=Counter(tuple(r.get(f,"").strip() for f in fields[:4]) for r in detail)
duplicates=sum(v-1 for v in keys.values() if v>1)
limit=int(re.search(r"MAX_ROWS\s*=\s*(\d+)",(ROOT/"lotus_farm/extraction.py").read_text()).group(1))
flag("LABOR_EXCEEDS_IMPORT_SHEET_LIMIT",len(labor) if len(labor)>limit else 0)
flag("LABOR_NEGATIVE_HEADCOUNT",len(neg),[example(r,fields) for r in neg[:5]])
flag("LABOR_HEADCOUNT_BALANCE",len(imbalance),[example(r,fields) for r in imbalance[:5]])
flag("LABOR_BLANK_COUNT_NEEDS_REVIEW",len(incomplete),[example(r,fields) for r in incomplete[:3]])
flag("LABOR_DUPLICATE_BUSINESS_KEYS",duplicates)
combined=[r for r in detail if "&" in r["NÔNG TRƯỜNG"]]
flag("LABOR_COMBINED_FARM_REQUIRES_MAPPING",len(combined),[example(r,fields[:4]) for r in combined[:3]])
plots=table("plots",6,["ID","Nông trường","Lô","Thửa","Tình trạng","Số cây HH"])
plot_detail=[r for r in plots if r.get("ID") and r.get("Thửa")]
fractional=[r for r in plot_detail if num(r.get("Số cây HH")) is not None and num(r["Số cây HH"])!=num(r["Số cây HH"]).to_integral_value()]
flag("PLOT_FRACTIONAL_PLANT_COUNT",len(fractional),[example(r,["ID","Nông trường","Thửa","Tình trạng","Số cây HH"]) for r in fractional[:5]])
plotkeys=Counter((r.get("Nông trường"),r.get("Thửa"),r.get("Thứ tự trồng")) for r in plot_detail)
flag("PLOT_DUPLICATE_SCOPE_CYCLE_KEYS",sum(v-1 for v in plotkeys.values() if v>1))
materials=table("materials",15,["Nông trường","Giai đoạn","Vật tư","Đvt_BC","Năm","Tháng","Số lượng VT"])
material_detail=[r for r in materials if r.get("Nông trường") and r.get("Vật tư")]
materialkeys=Counter(tuple(r.get(f,"").strip() for f in ["Nông trường","Giai đoạn","Vật tư","Đvt_BC","Năm","Tháng"]) for r in material_detail)
flag("MATERIAL_DUPLICATE_SCOPE_PERIOD_ITEM_KEYS",sum(v-1 for v in materialkeys.values() if v>1))
badqty=[r for r in material_detail if num(r.get("Số lượng VT")) is None or num(r["Số lượng VT"])<0]
flag("MATERIAL_MISSING_OR_NEGATIVE_QUANTITY",len(badqty),[example(r,["Nông trường","Vật tư","Số lượng VT"]) for r in badqty[:3]])
totals={}
for r in material_detail:
    n=num(r.get("Số lượng VT"))
    if n is not None:totals[r["Đvt_BC"]]=totals.get(r["Đvt_BC"],Decimal(0))+n
reasons=table("reasons",2,["Xí nghiệp","Nông trường","Lô","Thửa","Tổng buồng"])
reason_rows=[r for r in reasons if r.get("Nông trường")]
reason_bad=[]
for r in reason_rows:
    cats=[v for k,v in r.items() if k not in ["","Unnamed: 0","Xí nghiệp","Nông trường","Lô","Thửa","Tổng buồng"]]
    vals=[num(v) for v in cats]
    if any(v is None for v in vals) or sum(v for v in vals if v is not None)!=num(r["Tổng buồng"]):reason_bad.append(r)
flag("CANCELLATION_CATEGORY_TOTAL_MISMATCH",len(reason_bad),reason_bad[:3])
import_text=(ROOT/"lotus_farm/importing.py").read_text()
flag("CANCELLATION_REASON_MASTER_IMPORT_UNSUPPORTED",1 if "'Defect Reason':" not in import_text else 0)
onedrive=(ROOT/"lotus_farm/onedrive.py").read_text()
report=dict(scope="Four connector-extracted OneDrive workbooks; no original XLSX download, formulas or live app-to-Graph authentication verified",
    sources=[dict(file=k+".csv",sha256=hashlib.sha256((ROOT/"tests/fixtures/onedrive-values"/(k+".csv")).read_bytes()).hexdigest(),sections=len(parts(k))) for k in ["labor","plots","materials","reasons"]],
    labor=dict(rows=len(labor),detail_rows=len(detail),import_row_limit=limit,negative_rows=len(neg),imbalance_rows=len(imbalance),blank_count_rows=len(incomplete),duplicate_keys=duplicates),
    plots=dict(rows=len(plot_detail),fractional_plant_count_rows=len(fractional)),
    materials=dict(rows=len(material_detail),totals_by_source_unit={k:str(v) for k,v in totals.items()}),
    cancellation=dict(rows=len(reason_rows),category_total_mismatch_rows=len(reason_bad)),
    authentication=dict(app_uses_client_credentials="client_credentials" in onedrive,delegated_connector_access_verified=True,live_app_feed_tested=False),
    ready=False,issues=issues,
    exclusions=["Original XLSX bytes could not be downloaded (HTTP 403). Extracted values omit original formulas and sheet names.",
    "No organization mapping or real-data import was approved or written into ERPNext.",
    "These are the user's historical source files, not verified Lotus production records.",
    "This workflow checks data readiness. Existing ERPNext integration tests use generated fixtures."])
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
lines=["# OneDrive data audit","",report["scope"],"","| Check | Rows/issues |","| --- | ---: |",
    f"| Labor source rows | {len(labor)} |",f"| Negative labor counts | {len(neg)} |",
    f"| Labor balance errors | {len(imbalance)} |",f"| Blank labor counts | {len(incomplete)} |",
    f"| Fractional plant counts | {len(fractional)} |",f"| Material rows | {len(material_detail)} |",
    f"| Cancellation total errors | {len(reason_bad)} |","",
    "**Readiness: FAIL.** See report.json for examples and limitations.",""]
lines.extend("- "+e for e in report["exclusions"])
summary="\n".join(lines)+"\n"
(OUT/"summary.md").write_text(summary)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(summary)
print(summary)
raise SystemExit(2 if issues else 0)

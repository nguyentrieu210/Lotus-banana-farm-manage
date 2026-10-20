"""Smoke-render both Excel-shaped proposal forms with synthetic records; no ERP data."""
from pathlib import Path
import subprocess
from jinja2 import Environment

HTML=Path("/tmp/newwww/lotus_material_proposal_print.html").read_text(encoding="utf-8")
e=Environment(autoescape=True)
template=e.from_string(HTML)

def make_row(i):
    return dict(item_name="Vật tư thử "+str(i),specification="Quy cách thử",item_code="TEST-"+str(i),
        uom="kg",stock=10.0,qty=float(i),norm=0.5,issued_qty=None,needed_date="22/10/2026",
        warehouse="KHO",area="Lô A",scale="1 ha",purpose="Chăm sóc vườn",notes="",
        supplier="",price=1500.0,amount=1500.0*i)

for buy,n in [(True,58),(False,14)]:
    args=dict(purchase=buy,title="PHIẾU ĐỀ XUẤT MUA VẬT TƯ" if buy else "PHIẾU ĐỀ XUẤT CẤP VẬT TƯ",
        farm_label="Vườn 222 Thuận Phú",document={"name":"DEMO-001"},
        state="Bản mẫu",created_by="Người đề xuất thử",created_at="19/10/2026",
        department="Chăm sóc",reason="Chăm sóc vườn",warehouse="KHO",
        logo_data="",pdf_url="#",rows=[make_row(i) for i in range(1,n+1)],
        all_priced=buy,total=1500*n*(n+1)/2,amount_words="Một trăm đồng",
        approval={"name":"","image":""},number=lambda v:format(float(v),",.2f"))
    html=template.render(**args)
    assert html.count("<tr>")>=n
    assert "PHIẾU ĐỀ XUẤT" in html
    proc=subprocess.run(["wkhtmltopdf","--quiet","--orientation","Landscape","--page-size","A4",
        "--disable-javascript","--margin-top","8mm","--margin-bottom","8mm","-","-"],
        input=html.encode("utf-8"),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if proc.returncode or not proc.stdout.startswith(b"%PDF-"):
        raise RuntimeError("PDF render failed: "+proc.stderr.decode("utf-8","ignore")[:300])
    assert len(proc.stdout)>7000
    print(("BUY" if buy else "ISSUE"),"PDF_RENDER_OK",len(proc.stdout),"bytes",n,"rows")

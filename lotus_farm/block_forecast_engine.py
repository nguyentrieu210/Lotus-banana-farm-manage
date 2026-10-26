"""Single Book2 forecast engine: Farm Block census + approved Plan Cohorts ONLY.

Never reads Lotus Cut Journal Entry, cut-mother dates or previous forecast.
Outputs non-authoritative, date-stamped estimates; no database writes.
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
from collections import defaultdict

WAVE_SHARES=(0.17,0.40,0.25,0.18)
WAVE_STEP_DAYS=30
SHOOT_REPRESENTATIVE_DAY=0
SHOOT_TO_INJECT_DAYS=5
INJECT_TO_CUT_BUD_DAYS=16
CUT_BUD_TO_HARVEST_DAYS=65
SURVIVAL_TO_CUT=0.90
SURVIVAL_TO_HARVEST=0.97
PACK_RATE=0.98
KG_BY_CYCLE={1:19,2:20}
SUCKER_TO_FLOWER_MONTHS=6


def date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def months_after(value, amount):
    base=date(value)
    offset=base.year*12+(base.month-1)+int(amount)
    year, month=divmod(offset,12)
    return dt.date(year,month+1,min(base.day,calendar.monthrange(year,month+1)[1]))


def round_excel(number):
    return int(float(number)+0.5)


def portions(count, shares=WAVE_SHARES):
    if int(count)!=count or count<=0 or len(shares)!=4 or abs(sum(shares)-1)>1e-8:
        raise ValueError("Số cây phải nguyên dương; bốn tỷ lệ trổ phải đủ 100%.")
    rest=int(count)
    result=[]
    for share in shares[:-1]:
        q=min(rest,round_excel(count*share))
        result.append(q); rest-=q
    result.append(rest)
    return result


def source_rows(blocks, cohorts):
    """Use latest approved cohort versions per (block,cohort code).

    If a block has ANY approved cohorts, do not also count its census as a
    second source. Unapproved cohorts never silently become a forecast.
    """
    approved={}
    for row in cohorts:
        if row.get("approval_state")!="Approved":
            continue
        key=(row.get("farm_block"),row.get("cohort_code"))
        old=approved.get(key)
        if not old or int(row.get("version") or 0)>int(old.get("version") or 0):
            approved[key]=row
    by_block=defaultdict(list)
    for c in approved.values():
        by_block[c.get("farm_block")].append(c)
    sources=[]; warnings=[]
    for b in blocks:
        block=b["name"]
        if not b.get("active",True):
            continue
        crows=by_block.get(block,[])
        if crows:
            for c in sorted(crows,key=lambda x:(str(x.get("crop_cycle") or ""),str(x.get("cohort_code")))):
                basis=c.get("quantity_basis")
                anchor=c.get("anchor")
                when=c.get("anchor_date")
                qty=float(c.get("planned_qty") or 0)
                if basis not in ("Bunches","Trees","Selected Suckers") or qty<=0 or not qty.is_integer():
                    warnings.append(f'{block}: Đợt {c.get("cohort_code")} thiếu số cây/buồng hợp lệ.')
                    continue
                if anchor=="Shooting" and when:
                    flowering=date(when)
                elif anchor=="Selection" and when:
                    flowering=months_after(when,SUCKER_TO_FLOWER_MONTHS)
                else:
                    warnings.append(f'{block}: Đợt {c.get("cohort_code")} cần mốc chọn chồi hoặc trổ; không suy từ chặt mẹ/trồng.')
                    continue
                sources.append(dict(farm_block=block,zone=b.get("farm_zone") or "",
                    crop_cycle=c.get("crop_cycle"),cohort=c.get("name") or c.get("cohort_code"),
                    basis=basis,trees=int(qty),flower_start=flowering,
                    cycle_no=int(c.get("cycle_no") or 2 if anchor=="Selection" else c.get("cycle_no") or 1),
                    origin="Plan Cohort đã duyệt",source_version=int(c.get("version") or 1)))
        else:
            raw=b.get("lotus_tree_count")
            when=b.get("lotus_estimated_flowering_date")
            if not raw or int(raw)<=0 or not when:
                warnings.append(f"{block}: Chưa có số cây kiểm kê và mốc trổ dự kiến; không tự ước lượng.")
                continue
            sources.append(dict(farm_block=block,zone=b.get("farm_zone") or "",
                crop_cycle=None,cohort=None,basis="Trees",trees=int(raw),
                flower_start=date(when),cycle_no=int(b.get("cycle_no") or 1),
                origin="Kiểm kê lô + trổ dự kiến",source_version=None))
    return sources,warnings


def forecast(blocks,cohorts,from_date=None,to_date=None,block=None):
    sources,warnings=source_rows(blocks,cohorts)
    first=date(from_date) if from_date else None
    last=date(to_date) if to_date else None
    if first and last and last<first:
        raise ValueError("Khoảng ngày dự thu không hợp lệ.")
    rows=[]
    for s in sources:
        if block and s["farm_block"]!=block:
            continue
        for wave,count in enumerate(portions(s["trees"]),1):
            if count==0: continue
            start=s["flower_start"]+dt.timedelta(days=(wave-1)*WAVE_STEP_DAYS)
            flowering=start+dt.timedelta(days=SHOOT_REPRESENTATIVE_DAY)
            injection=flowering+dt.timedelta(days=SHOOT_TO_INJECT_DAYS)
            cut=injection+dt.timedelta(days=INJECT_TO_CUT_BUD_DAYS)
            harvest=cut+dt.timedelta(days=CUT_BUD_TO_HARVEST_DAYS)
            if first and harvest<first or last and flowering>last:
                continue
            cut_qty=round_excel(count*SURVIVAL_TO_CUT)
            harvest_qty=round_excel(cut_qty*SURVIVAL_TO_HARVEST)
            pack_qty=round_excel(harvest_qty*PACK_RATE)
            weight=KG_BY_CYCLE.get(s["cycle_no"],19)
            ident="|".join(map(str,(s["farm_block"],s["crop_cycle"],s["cohort"],wave,
                                      s["source_version"],s["flower_start"])))
            rows.append(dict(key=hashlib.sha256(ident.encode()).hexdigest()[:32],
                farm_block=s["farm_block"],zone=s["zone"],crop_cycle=s["crop_cycle"],
                cohort=s["cohort"],wave=wave,source=s["origin"],cycle_no=s["cycle_no"],
                source_version=s["source_version"],qty_basis=s["basis"],
                flower_window_start=str(start),flower_date=str(flowering),
                inject_date=str(injection),cut_bud_date=str(cut),harvest_date=str(harvest),
                tree_qty=count,bunches_shoot=count,bunches_cut=cut_qty,
                bunches_harvest=harvest_qty,bunches_pack=pack_qty,
                kg_pack=pack_qty*weight,estimated=True))
    rows.sort(key=lambda r:(r["harvest_date"],r["farm_block"],r["wave"]))
    monthly=defaultdict(lambda:dict(bunches=0,packed_kg=0))
    for row in rows:
        slot=monthly[row["harvest_date"][:7]]
        slot["bunches"]+=row["bunches_harvest"]
        slot["packed_kg"]+=row["kg_pack"]
    return dict(rows=rows,monthly=[dict(month=k,**v) for k,v in sorted(monthly.items())],
                warnings=warnings,source_count=len(sources),unmapped_lots=len(warnings),
                rule="CHỈ DỰ PHÓNG – dữ liệu theo LÔ/VỤ/ĐỢT, không sử dụng nhật ký chặt cây mẹ.")

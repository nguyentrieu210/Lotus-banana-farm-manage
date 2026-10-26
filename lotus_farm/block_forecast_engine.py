"""Lotus crop forecast from Farm Block census / approved Plan Cohort only.

Output is a scenario until its source and parameter version are approved.
Daily events spread the four flowering windows without inflating totals.
Never reads or infers from a mother-tree cutting journal.
"""
from __future__ import annotations
import calendar
import datetime as dt
import hashlib
import math
from collections import defaultdict

from lotus_farm.forecast_parameters import DEFAULTS,approved_version,validate

def date(value):
    if isinstance(value,dt.datetime):return value.date()
    if isinstance(value,dt.date):return value
    return dt.date.fromisoformat(str(value)[:10])

def months_after(value,amount):
    d=date(value)
    index=d.year*12+d.month-1+int(amount)
    year,month=divmod(index,12)
    return dt.date(year,month+1,min(d.day,calendar.monthrange(year,month+1)[1]))

def round_excel(value):
    return int(float(value)+0.5)

def portions(total,weights):
    if not isinstance(total,int) or total<0 or len(weights)<1 or abs(sum(weights)-1)>1e-8:
        raise ValueError("Số cây/buồng cần nguyên không âm và tỷ lệ phân đợt phải cộng 100%.")
    remaining=total;parts=[]
    for rate in weights[:-1]:
        q=min(remaining,round_excel(total*rate))
        parts.append(q);remaining-=q
    return parts+[remaining]

def distribute_daily(value,days):
    """Integer-preserving distribution of a wave into all its days."""
    q,r=divmod(int(value),int(days))
    return [q+int(i<r) for i in range(days)]

def source_rows(blocks,cohorts):
    approved={}
    for row in cohorts:
        if row.get("approval_state")!="Approved":continue
        key=(row.get("farm_block"),row.get("crop_cycle"),row.get("cohort_code"))
        prior=approved.get(key)
        if not prior or int(row.get("version") or 0)>int(prior.get("version") or 0):
            approved[key]=row
    per_block=defaultdict(list)
    for row in approved.values():per_block[row.get("farm_block")].append(row)
    sources=[];warnings=[]
    for b in blocks:
        if not b.get("active",True):continue
        block=b["name"]
        batches=per_block.get(block,[])
        if batches:
            for c in sorted(batches,key=lambda x:(str(x.get("crop_cycle") or ""),str(x.get("cohort_code") or ""))):
                raw=c.get("planned_qty")
                try:quantity=int(raw)
                except (TypeError,ValueError):quantity=0
                if not quantity or float(raw)!=quantity or c.get("quantity_basis") not in ("Trees","Selected Suckers","Bunches"):
                    warnings.append(f'{block}: Đợt {c.get("cohort_code")} thiếu số lượng hợp lệ.')
                    continue
                anchor=c.get("anchor");when=c.get("anchor_date")
                if not when or anchor not in ("Shooting","Selection"):
                    warnings.append(f'{block}: Đợt {c.get("cohort_code")} thiếu ngày chọn chồi/trổ được xác nhận.')
                    continue
                if c.get("quantity_basis")=="Bunches" and anchor=="Selection":
                    warnings.append(f'{block}: Số BUỒNG không thể gắn vào mốc CHỌN CHỒI.')
                    continue
                # Selection -> bloom depends on the selected forecast profile; set
                # selection_date instead of projecting here.
                distribution=c.get("forecast_distribution_mode") or (
                    "Single Wave" if anchor=="Shooting" and c.get("quantity_basis")=="Bunches" else "Four Waves")
                cycle_no=c.get("cycle_no")
                count_status="Cohort Approved"
                if not cycle_no:
                    cycle_no=2 if anchor=="Selection" else 1
                    count_status="Cycle Unconfirmed"
                    warnings.append(f'{block}: Đợt {c.get("cohort_code")} chưa liên kết số vụ cây; trọng lượng kg/buồng chỉ là kịch bản.')
                sources.append(dict(farm_block=block,zone=b.get("farm_zone") or "",
                    crop_cycle=c.get("crop_cycle"),cohort=c.get("name") or c.get("cohort_code"),
                    basis=c["quantity_basis"],quantity=quantity,
                    anchor=anchor,anchor_date=date(when),distribution=distribution,
                    cycle_no=cycle_no,count_status=count_status,
                    origin="Plan Cohort",source_version=int(c.get("version") or 1),
                    source_modified=str(c.get("modified") or "")))
        else:
            raw=b.get("lotus_tree_count")
            when=b.get("lotus_estimated_flowering_date")
            try:quantity=int(raw)
            except (TypeError,ValueError):quantity=0
            if not when or quantity<=0 or float(raw)!=quantity:
                warnings.append(f"{block}: Thiếu số cây lô và mốc trổ; không suy từ diện tích.")
                continue
            sources.append(dict(farm_block=block,zone=b.get("farm_zone") or "",
                crop_cycle=None,cohort=None,basis="Trees",quantity=quantity,
                anchor="Shooting",anchor_date=date(when),distribution="Four Waves",
                cycle_no=1,count_status=b.get("forecast_count_source") or "Unverified",
                origin="Farm Block (số cây nguồn chưa phải kiểm kê)",
                source_version=None,source_modified=str(b.get("modified") or "")))
    return sources,warnings

def weight_kg(cycle,params):
    cycle=int(cycle or 1)
    return params["kg_cycle_1"] if cycle==1 else params["kg_cycle_2"] if cycle==2 else params["kg_cycle_3"]

def daily_for_wave(wave):
    days=wave["window_days"]
    trees=distribute_daily(wave["tree_qty"],days)
    shoots=distribute_daily(wave["bunches_shoot"],days)
    cuts=distribute_daily(wave["bunches_cut"],days)
    harvested=distribute_daily(wave["bunches_harvest"],days)
    packed=distribute_daily(wave["bunches_pack"],days)
    for i in range(days):
        when=date(wave["flower_window_start"])+dt.timedelta(days=i)
        offset=wave["timing"]
        yield dict(key=f'{wave["key"]}:{i}',wave_key=wave["key"],
                   farm_block=wave["farm_block"],zone=wave["zone"],
                   crop_cycle=wave["crop_cycle"],cohort=wave["cohort"],wave=wave["wave"],
                   profile=wave["profile"],source_version=wave["source_version"],
                   count_status=wave["count_status"],parameter_status=wave["parameter_status"],
                   flower_date=str(when),inject_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"])),
                   cut_bud_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"]+offset["inject_to_cut_days"])),
                   harvest_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"]+offset["inject_to_cut_days"]+offset["cut_to_harvest_days"])),
                   tree_qty=trees[i],bunches_shoot=shoots[i],bunches_cut=cuts[i],
                   bunches_harvest=harvested[i],bunches_pack=packed[i],
                   kg_pack=round(packed[i]*wave["weight_kg"],3),
                   qty_basis=wave["qty_basis"],estimated=True)

def forecast(blocks,cohorts,from_date=None,to_date=None,block=None,profiles=None,include_daily=False):
    sources,warnings=source_rows(blocks,cohorts)
    first=date(from_date) if from_date else None
    last=date(to_date) if to_date else None
    if first and last and last<first:raise ValueError("Khoảng ngày dự thu không hợp lệ.")
    waves=[];daily=[];monthly=defaultdict(lambda:dict(bunches=0,packed_kg=0))
    for s in sources:
        if block and s["farm_block"]!=block:continue
        estimated_bloom=(months_after(s["anchor_date"],DEFAULTS["sucker_to_flower_months"])
                         if s["anchor"]=="Selection" else s["anchor_date"])
        base=approved_version(profiles or [],s["farm_block"],estimated_bloom)
        config=validate(base) if base else validate(DEFAULTS)
        parameter_status="Approved" if base else "Unapproved Book2 scenario"
        if not base:
            warnings.append(f'{s["farm_block"]}: Chưa có bộ thông số dự thu đã duyệt có hiệu lực; chỉ được xem kịch bản.')
        bloom=months_after(s["anchor_date"],config["sucker_to_flower_months"]) if s["anchor"]=="Selection" else s["anchor_date"]
        full_weights=[config[f"wave_{i}_share"] for i in range(1,5)]
        weights=[1.0] if s["distribution"]=="Single Wave" else full_weights
        # Bunches at Shooting is an observed/planned bunch count, NOT a tree
        # count, so 90% per tree must not be applied a second time.
        raw_by_wave=portions(s["quantity"],weights)
        for i,initial in enumerate(raw_by_wave):
            if not initial:continue
            start=bloom+dt.timedelta(days=i*config["wave_step_days"])
            window=config["wave_window_days"] if len(weights)==4 else 1
            if s["basis"]=="Bunches":
                shoots=initial
                cut=round_excel(shoots*config["cut_rate_per_flowered_bunch"])
            else:
                shoots=round_excel(initial*config["flowering_rate"])
                cut=min(shoots,round_excel(initial*config["cut_rate_per_tree"]))
                if round_excel(initial*config["cut_rate_per_tree"])>shoots:
                    warnings.append(f'{s["farm_block"]}: tỷ lệ cắt bắp/cây cao hơn tỷ lệ trổ; đã giới hạn ở số buồng trổ.')
            harvest=round_excel(cut*config["harvest_rate"])
            packed=round_excel(harvest*config["pack_rate"])
            weight=weight_kg(s["cycle_no"],config)
            ident="|".join(map(str,(s["farm_block"],s["crop_cycle"],s["cohort"],i+1,
                               s["source_version"],s["anchor_date"],base.get("name") if base else "preview")))
            window_end=start+dt.timedelta(days=window-1)
            harvest_start=start+dt.timedelta(days=config["shoot_to_inject_days"]+
                    config["inject_to_cut_days"]+config["cut_to_harvest_days"])
            harvest_end=harvest_start+dt.timedelta(days=window-1)
            if first and harvest_end<first or last and start>last:
                continue
            wave=dict(key=hashlib.sha256(ident.encode()).hexdigest()[:32],
                 farm_block=s["farm_block"],zone=s["zone"],crop_cycle=s["crop_cycle"],
                 cohort=s["cohort"],wave=i+1,source=s["origin"],cycle_no=s["cycle_no"] or 1,
                 qty_basis=s["basis"],count_status=s["count_status"],
                 profile=base.get("name") if base else None,
                 parameter_status=parameter_status,source_version=s["source_version"],
                 source_modified=s["source_modified"],
                 flower_window_start=str(start),flower_window_end=str(window_end),
                 flower_date=str(start),inject_date=str(start+dt.timedelta(days=config["shoot_to_inject_days"])),
                 cut_bud_date=str(start+dt.timedelta(days=config["shoot_to_inject_days"]+config["inject_to_cut_days"])),
                 harvest_date=str(harvest_start),harvest_window_end=str(harvest_end),
                 tree_qty=initial,bunches_shoot=shoots,bunches_cut=cut,bunches_harvest=harvest,
                 bunches_pack=packed,kg_pack=round(packed*weight,3),weight_kg=weight,
                 window_days=window,timing=config,estimated=True)
            waves.append(wave)
            # Monthly yield from each DAILY harvest date, not a repeated
            # 17/40/25/18 harvest curve and not a 30-day single spike.
            for row in daily_for_wave(wave):
                slot=monthly[row["harvest_date"][:7]]
                slot["bunches"]+=row["bunches_harvest"]
                slot["packed_kg"]+=row["kg_pack"]
                if include_daily:daily.append(row)
    waves.sort(key=lambda r:(r["harvest_date"],r["farm_block"],r["wave"]))
    result=dict(rows=waves,monthly=[dict(month=k,**v) for k,v in sorted(monthly.items())],
                warnings=sorted(set(warnings)),source_count=len(sources),
                missing_sources_count=len(warnings),estimated=True,
                rule="Dự phóng theo lô/vụ/đợt. Không dùng nhật ký chặt cây mẹ.")
    if include_daily:result["daily_rows"]=daily
    return result

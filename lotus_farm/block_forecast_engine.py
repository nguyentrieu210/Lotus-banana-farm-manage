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
                if quantity<=0 or float(raw)!=quantity or c.get("quantity_basis") not in ("Trees","Selected Suckers","Bunches"):
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
            # The previously supplied per-lot tree count is the OFFICIAL
            # OPERATING BASELINE for forecast/planning, even on legacy records
            # with Unverified/Source File/Estimated status. This is a management
            # acceptance of the numbers, NOT proof of a physical field census.
            physical_count=b.get("forecast_count_source")=="Census Confirmed"
            sources.append(dict(farm_block=block,zone=b.get("farm_zone") or "",
                crop_cycle=None,cohort=None,basis="Trees",quantity=quantity,
                anchor="Shooting",anchor_date=date(when),distribution="Four Waves",
                cycle_no=1,count_status="Census Confirmed" if physical_count else "Planning Baseline",
                origin="Số cây gốc đợt trước đã chốt" if not physical_count else "Số cây ghi nhận ngoài vườn",
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
                   cycle_no=wave.get("cycle_no"),generation=wave.get("generation",0),
                   source_crop_cycle=wave.get("source_crop_cycle"),source_cohort=wave.get("source_cohort"),
                   selection_date=str(when),
                   flower_date=str(when),inject_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"])),
                   cut_bud_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"]+offset["inject_to_cut_days"])),
                   harvest_date=str(when+dt.timedelta(days=offset["shoot_to_inject_days"]+offset["inject_to_cut_days"]+offset["cut_to_harvest_days"])),
                   tree_qty=trees[i],bunches_shoot=shoots[i],bunches_cut=cuts[i],
                   bunches_harvest=harvested[i],bunches_pack=packed[i],
                   kg_pack=round(packed[i]*wave["weight_kg"],3),
                   qty_basis=wave["qty_basis"],estimated=True)

def projection_config(source, profiles):
    """Select a parameter version using its own selection-to-flowering offset."""
    applicable=[]
    for candidate in profiles or []:
        if candidate.get("approval_state")!="Approved" or not candidate.get("active",True):
            continue
        if candidate.get("farm_block") and candidate["farm_block"]!=source["farm_block"]:
            continue
        config=validate(candidate)
        bloom=(months_after(source["anchor_date"],config["sucker_to_flower_months"])
               if source["anchor"]=="Selection" else source["anchor_date"])
        if approved_version([candidate],source["farm_block"],bloom):
            applicable.append(candidate)
    applicable.sort(key=lambda p:(bool(p.get("farm_block")),int(p.get("version") or 0)),reverse=True)
    profile=applicable[0] if applicable else None
    config=validate(profile or DEFAULTS)
    bloom=(months_after(source["anchor_date"],config["sucker_to_flower_months"])
           if source["anchor"]=="Selection" else source["anchor_date"])
    return profile,config,bloom


def forecast(blocks,cohorts,from_date=None,to_date=None,block=None,profiles=None,
             include_daily=False,horizon_months=None):
    """One engine for the initial four waves and all succeeding sucker crops.

    A selection happens at flowering. Each wave's next flowering is shifted by
    calendar months from that wave, never multiplied into another four waves.
    horizon_months=None exposes one crop for rule reconciliation.
    """
    sources,warnings=source_rows(blocks,cohorts)
    if block:sources=[s for s in sources if s["farm_block"]==block]
    first=date(from_date) if from_date else None
    last=date(to_date) if to_date else None
    if horizon_months is not None:
        if int(horizon_months)!=horizon_months or not 1<=int(horizon_months)<=36:
            raise ValueError("Khoảng dự thu phải từ 1 đến 36 tháng.")
        anchors=[projection_config(s,profiles)[2] for s in sources]
        anchor=first or min(anchors,default=dt.date.today())
        first=anchor.replace(day=1)
        last=months_after(first,int(horizon_months))-dt.timedelta(days=1)
    if first and last and last<first:raise ValueError("Khoảng ngày dự thu không hợp lệ.")
    waves=[];daily=[];monthly=defaultdict(lambda:dict(bunches=0,packed_kg=0))
    if horizon_months:
        for i in range(int(horizon_months)):
            monthly[str(months_after(first,i))[:7]]
    for s in sources:
        profile,config,bloom=projection_config(s,profiles)
        generation=0
        previous_starts=None
        while True:
            cycle_no=int(s["cycle_no"])+generation
            if generation and any(other["farm_block"]==s["farm_block"] and
                    int(s["cycle_no"])<int(other["cycle_no"])<=cycle_no and
                    other["count_status"]!="Cycle Unconfirmed" for other in sources):
                break # An explicit successor cohort owns its own later crops.
            if not profile:
                warnings.append(f'{s["farm_block"]}: Chưa có bộ thông số dự thu đã duyệt có hiệu lực; chỉ được xem kịch bản.')
            status="Approved" if profile else "Unapproved Book2 scenario"
            weights=([1.0] if s["distribution"]=="Single Wave" else
                     [config[f"wave_{i}_share"] for i in range(1,5)])
            starts=([bloom+dt.timedelta(days=i*config["wave_step_days"]) for i in range(len(weights))]
                    if previous_starts is None else
                    [months_after(d,config["sucker_to_flower_months"]) for d in previous_starts])
            if last and min(starts)>last:break
            # The next crop's configuration is scoped to its projected bloom.
            next_source={**s,"anchor":"Selection","anchor_date":starts[0]}
            next_profile,next_config,next_bloom=projection_config(next_source,profiles)
            for i,initial in enumerate(portions(s["quantity"],weights)):
                if not initial:continue
                start=starts[i]
                window=config["wave_window_days"] if len(weights)==4 else 1
                if s["basis"]=="Bunches":
                    shoots=initial;cut=round_excel(shoots*config["cut_rate_per_flowered_bunch"])
                else:
                    shoots=round_excel(initial*config["flowering_rate"])
                    cut=min(shoots,round_excel(initial*config["cut_rate_per_tree"]))
                    if round_excel(initial*config["cut_rate_per_tree"])>shoots:
                        warnings.append(f'{s["farm_block"]}: tỷ lệ cắt bắp/cây cao hơn tỷ lệ trổ; đã giới hạn ở số buồng trổ.')
                harvest=round_excel(cut*config["harvest_rate"])
                packed=round_excel(harvest*config["pack_rate"])
                weight=weight_kg(cycle_no,config)
                ident="|".join(map(str,(s["farm_block"],s["crop_cycle"],s["cohort"],i+1,
                    s["source_version"],s["anchor_date"],profile.get("name") if profile else "preview",generation)))
                window_end=start+dt.timedelta(days=window-1)
                offset=config["shoot_to_inject_days"]+config["inject_to_cut_days"]+config["cut_to_harvest_days"]
                harvest_start=start+dt.timedelta(days=offset)
                harvest_end=harvest_start+dt.timedelta(days=window-1)
                if first and harvest_end<first or last and start>last:continue
                wave=dict(key=hashlib.sha256(ident.encode()).hexdigest()[:32],
                    farm_block=s["farm_block"],zone=s["zone"],
                    crop_cycle=s["crop_cycle"] if not generation else None,
                    cohort=s["cohort"] if not generation else None,
                    source_crop_cycle=s["crop_cycle"],source_cohort=s["cohort"],
                    wave=i+1,cycle_no=cycle_no,generation=generation,
                    source=s["origin"] if not generation else "Chồi kế tiếp từ trổ",
                    qty_basis=s["basis"],count_status=s["count_status"] if not generation else "Planning Baseline",
                    profile=profile.get("name") if profile else None,parameter_status=status,
                    source_version=s["source_version"],source_modified=s["source_modified"],
                    flower_window_start=str(start),flower_window_end=str(window_end),flower_date=str(start),
                    selection_date=str(start),selection_window_end=str(window_end),
                    next_flower_date=str(months_after(start,next_config["sucker_to_flower_months"])),
                    next_flower_window_end=str(months_after(start,next_config["sucker_to_flower_months"])+dt.timedelta(days=(next_config["wave_window_days"] if len(weights)==4 else 1)-1)),
                    inject_date=str(start+dt.timedelta(days=config["shoot_to_inject_days"])),
                    cut_bud_date=str(start+dt.timedelta(days=config["shoot_to_inject_days"]+config["inject_to_cut_days"])),
                    harvest_date=str(harvest_start),harvest_window_end=str(harvest_end),
                    tree_qty=initial,bunches_shoot=shoots,bunches_cut=cut,bunches_harvest=harvest,
                    bunches_pack=packed,kg_pack=round(packed*weight,3),weight_kg=weight,
                    window_days=window,timing=config,estimated=True)
                crop_daily=list(daily_for_wave(wave))
                visible=[r for r in crop_daily if (not first or date(r["harvest_date"])>=first)
                         and (not last or date(r["harvest_date"])<=last)]
                if include_daily:daily.extend(crop_daily)
                for row in visible:
                    slot=monthly[row["harvest_date"][:7]]
                    slot["bunches"]+=row["bunches_harvest"];slot["packed_kg"]+=row["kg_pack"]
                if not visible:continue
                if horizon_months:
                    wave.update(bunches_harvest=sum(r["bunches_harvest"] for r in visible),
                                bunches_pack=sum(r["bunches_pack"] for r in visible),
                                kg_pack=round(sum(r["kg_pack"] for r in visible),3),
                                harvest_date=visible[0]["harvest_date"],harvest_window_end=visible[-1]["harvest_date"])
                wave["carton_equivalent"]=round(wave["kg_pack"]/config["kg_per_carton"],3)
                wave["container_equivalent"]=round(wave["kg_pack"]/(config["kg_per_carton"]*config["cartons_per_container"]),5)
                waves.append(wave)
            if not horizon_months:break
            if s["basis"]=="Bunches":
                warnings.append(f'{s["farm_block"]}: Nguồn buồng đã trổ chỉ tính vụ đó; cần số cây/chồi để lặp vụ.')
                break
            previous_starts=starts
            profile,config,bloom=next_profile,next_config,next_bloom
            generation+=1
            if generation>120:raise ValueError("Mốc cây quá xa khoảng dự thu; cần cập nhật đợt cây.")
    waves.sort(key=lambda r:(r["harvest_date"],r["farm_block"],r["cycle_no"],r["wave"]))
    result=dict(rows=waves,monthly=[dict(month=k,**v) for k,v in sorted(monthly.items())],
        warnings=sorted(set(warnings)),source_count=len(sources),estimated=True,
        missing_sources_count=len(warnings),horizon_months=horizon_months,
        window_start=str(first) if first else None,window_end=str(last) if last else None,
        rule="Chọn chồi cùng lúc trổ; trổ vụ kế sau số tháng lịch của bộ thông số.")
    if include_daily:result["daily_rows"]=daily
    return result

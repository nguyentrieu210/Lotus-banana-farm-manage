"""Validated, versionable Book2 forecast assumptions.

Shares and biological rates are *scenario assumptions* until approved by a farm
manager. Stage-specific conversion is explicit; a counted bunch is not a tree.
"""
from __future__ import annotations
from math import isfinite

DEFAULTS = {
    "wave_1_share": .17, "wave_2_share": .40, "wave_3_share": .25, "wave_4_share": .18,
    "wave_window_days": 30, "wave_step_days": 30,
    "sucker_to_flower_months": 6, "shoot_to_inject_days": 5,
    "inject_to_cut_days": 16, "cut_to_harvest_days": 65,
    "flowering_rate": 1.0, "cut_rate_per_tree": .90,
    "cut_rate_per_flowered_bunch": 1.0,
    "harvest_rate": .97, "pack_rate": .98,
    "kg_cycle_1":19, "kg_cycle_2":20, "kg_cycle_3":19,
    "kg_per_carton":13, "cartons_per_container":1320,
    "census_sucker_yield": .97,
    "apply_sucker_yield_to_counted_trees":0,
}
RATES=("wave_1_share","wave_2_share","wave_3_share","wave_4_share",
       "flowering_rate","cut_rate_per_tree","cut_rate_per_flowered_bunch",
       "harvest_rate","pack_rate","census_sucker_yield")
POSITIVE_INTS=("wave_window_days","wave_step_days","sucker_to_flower_months",
               "inject_to_cut_days","cut_to_harvest_days","cartons_per_container")
NONNEGATIVE_INTS=("shoot_to_inject_days",)
POSITIVE_FLOATS=("kg_cycle_1","kg_cycle_2","kg_cycle_3","kg_per_carton")


def validate(values):
    """Return a clean snapshot; never mutate a saved approved document."""
    clean={}
    values=values or {}
    for name,base in DEFAULTS.items():
        candidate=values.get(name)
        candidate=base if candidate is None or candidate=="" else candidate
        try:
            val=float(candidate)
        except (TypeError,ValueError):
            raise ValueError(f"Thông số {name} phải là số.") from None
        if not isfinite(val):
            raise ValueError(f"Thông số {name} phải hữu hạn.")
        if name in POSITIVE_INTS+NONNEGATIVE_INTS+("apply_sucker_yield_to_counted_trees",):
            if not val.is_integer() or val<0 or name in POSITIVE_INTS and val==0:
                raise ValueError(f"Thông số {name} phải là số nguyên hợp lệ.")
            val=int(val)
        if name in RATES and (val<0 or val>1):
            raise ValueError(f"Thông số {name} phải nằm từ 0 tới 1.")
        if name in POSITIVE_FLOATS and val<=0:
            raise ValueError(f"Thông số {name} phải lớn hơn 0.")
        clean[name]=val
    if abs(sum(clean[f"wave_{i}_share"] for i in range(1,5))-1)>1e-8:
        raise ValueError("Bốn tỷ lệ trổ phải cộng đúng 100%.")
    if clean["apply_sucker_yield_to_counted_trees"] != 0:
        raise ValueError("Không nhân 97% chồi vào số cây/chồi đã kiểm kê hoặc chọn thực tế.")
    if clean["wave_step_days"]<clean["wave_window_days"]:
        raise ValueError("Bốn cửa sổ trổ đang chồng lấn. Kiểm tra bước và độ dài cửa sổ.")
    return clean


def approved_version(profiles,block,when):
    """Use only approved effective profile, specific block first, then newest."""
    valid=[]
    for profile in profiles:
        if profile.get("approval_state")!="Approved" or not profile.get("active",True):
            continue
        if profile.get("farm_block") and profile["farm_block"]!=block:
            continue
        if profile.get("valid_from") and str(profile["valid_from"])>str(when):
            continue
        if profile.get("valid_to") and str(profile["valid_to"])<str(when):
            continue
        valid.append(profile)
    valid.sort(key=lambda p:(bool(p.get("farm_block")),int(p.get("version") or 0)),reverse=True)
    return valid[0] if valid else None


def snapshot(profile=None):
    return validate(profile)

"""Ca đóng gói theo nguồn buồng (spec 002, US6). Pure: no Frappe, no database.

A shift takes bunches from lô and ribbon colours (its sources). What it packs, finished kg, secondary kg and cartons, is
split over the sources by the kg each brought in, so every lô and colour gets its kg per bunch, cartons per bunch and
pack-out rate. The value of the stock receipt comes from each lô's work in progress the same way: kg brought in × the
lô's cost per kg, spread over its finished and secondary kg.
"""
TOLERANCE_KG = 0.0005


def _f(value):
    return float(value or 0)


def _key(source):
    return (source["farm_block"], source["bunch_tag"])


def check_sources(sources, input_kg=None):
    """Errors of the sources as typed, in Vietnamese: whole bunches, kg above zero, one row per lô and colour, and the kg
    of the sources adding up to the kg the shift took in (when that is given separately)."""
    errors, seen = [], set()
    for index, s in enumerate(sources, 1):
        bunches = s.get("bunches")
        if not isinstance(bunches, int) and not (isinstance(bunches, float) and bunches.is_integer()) or int(bunches or 0) < 1:
            errors.append(f"Dòng {index}: số buồng phải là số nguyên lớn hơn 0.")
        if _f(s.get("kg")) <= 0:
            errors.append(f"Dòng {index}: kg nhận phải lớn hơn 0.")
        key = _key(s)
        if key in seen:
            errors.append(f"Dòng {index}: lô và đợt màu này đã có ở dòng trên; gộp vào một dòng.")
        seen.add(key)
    total = sum(_f(s.get("kg")) for s in sources)
    if input_kg is not None and abs(total - _f(input_kg)) > TOLERANCE_KG:
        errors.append(f"Tổng kg các nguồn ({round(total, 3)}) phải bằng kg đưa vào ca ({round(_f(input_kg), 3)}).")
    return errors


def over_received(sources, harvested, received_elsewhere):
    """Lô and colours where the shift takes more bunches than were harvested and not yet taken by another shift.
    harvested, received_elsewhere: {(lô, màu): bunches}."""
    wanted = {}
    for s in sources:
        wanted[_key(s)] = wanted.get(_key(s), 0) + int(s.get("bunches") or 0)
    out = []
    for key, bunches in wanted.items():
        left = int(harvested.get(key, 0)) - int(received_elsewhere.get(key, 0))
        if bunches > left:
            out.append({"farm_block": key[0], "bunch_tag": key[1], "bunches": bunches, "left": max(left, 0)})
    return out


def outputs(input_kg, finished_kg, secondary_kg):
    """Loss and pack-out rate of the shift; an error when it packs more than it took in."""
    taken, finished, secondary = _f(input_kg), _f(finished_kg), _f(secondary_kg)
    if finished < 0 or secondary < 0:
        return {"error": "Kg thành phẩm và phụ phẩm không được âm."}
    if finished + secondary > taken + TOLERANCE_KG:
        return {"error": f"Thành phẩm và phụ phẩm ({round(finished + secondary, 3)} kg) nhiều hơn kg đưa vào ca ({round(taken, 3)} kg)."}
    return {"loss_kg": round(max(taken - finished - secondary, 0), 3), "packout_percent": round(finished / taken * 100, 2) if taken else None}


def _whole_split(total, shares):
    """`total` whole units over shares, largest remainder first, so the parts add up to the total."""
    raw = [total * s for s in shares]
    parts = [int(r) for r in raw]
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - parts[i]), i))
    for i in order[: total - sum(parts)]:
        parts[i] += 1
    return parts


def split(sources, finished_kg, secondary_kg, cartons):
    """Per source, by kg brought in: finished and secondary kg, cartons, kg per bunch, cartons per bunch, pack-out rate."""
    total = sum(_f(s.get("kg")) for s in sources)
    if not total:
        return []
    shares = [_f(s.get("kg")) / total for s in sources]
    boxes = _whole_split(int(cartons or 0), shares)
    rows = []
    for s, share, box in zip(sources, shares, boxes):
        kg, bunches = _f(s.get("kg")), int(s.get("bunches") or 0)
        finished = _f(finished_kg) * share
        rows.append(dict(s, share=round(share, 6), finished_kg=round(finished, 3), secondary_kg=round(_f(secondary_kg) * share, 3), cartons=box,
                         kg_per_bunch=round(kg / bunches, 3) if bunches else None,
                         cartons_per_bunch=round(box / bunches, 3) if bunches else None,
                         packout_percent=round(finished / kg * 100, 2) if kg else None))
    return rows


def receipt_rows(split_rows, rates):
    """Stock receipt lines of a shift: per source, its finished and secondary kg, carrying the value taken off the lô's
    work in progress (kg brought in × the lô's cost per kg), shared between the two by kg. rates: {lô: đ per kg}.
    Returns (rows, lô without a rate)."""
    rows, missing = [], []
    for s in split_rows:
        rate = rates.get(s["farm_block"])
        if not rate:
            missing.append(s["farm_block"])
            continue
        value = _f(s["kg"]) * _f(rate)
        packed = s["finished_kg"] + s["secondary_kg"]
        for kind, qty in (("finished", s["finished_kg"]), ("secondary", s["secondary_kg"])):
            if qty > 0:
                part = value * qty / packed
                rows.append({"kind": kind, "farm_block": s["farm_block"], "bunch_tag": s["bunch_tag"], "qty": qty,
                             "rate": round(part / qty, 4), "value": round(part, 2)})
    return rows, sorted(set(missing))

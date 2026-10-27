"""Pure daily work allocation from versioned forecast waves."""
import hashlib
from datetime import timedelta
from lotus_farm.block_forecast_engine import date

# work code / offset after injection / basis / readable note
INJECTION_WORK=(
    ("CV020",0,"bunches_shoot","Chích bắp: cần kiểm tra trổ ngoài vườn"),
    ("CV021",5,"bunches_shoot","Chống đổ: phải khảo sát cây cần chống thực tế"),
    ("CV022",7,"bunches_shoot","Vén lá, tỉa"),
    ("CV023",7,"bunches_shoot","Lặt hoa 1"),
    ("CV024",7,"bunches_shoot","Phun buồng 1"),
    ("CV025",10,"bunches_shoot","Lặt hoa 2"),
    ("CV026",10,"bunches_shoot","Phun buồng 2"),
    ("CV027",13,"bunches_shoot","Lặt hoa 3"),
    ("CV028",13,"bunches_shoot","Phun buồng 3"),
    ("CV029",16,"bunches_cut","Cắt bắp"),
    ("CV030",16,"bunches_cut","Cột dây màu"),
    ("CV031",16,"bunches_cut","Phun buồng 4"),
    ("CV032",16,"bunches_cut","Lót, chèn xốp"),
    ("CV033",16,"bunches_cut","Bao buồng"),
)
HARVEST_WORK=(
    ("CV034",-10,"bunches_harvest","Đo trái: cửa sổ thu -10 đến -7 ngày"),
    ("CV035",0,"bunches_harvest","Cắt/vác buồng: theo đo trái thực tế"),
    ("CV036",0,"bunches_harvest","Vận chuyển buồng"),
)

def work_events(daily_rows,start,end):
    grouped={}
    for wave in daily_rows:
        for code,off,basis,note,anchor in (
            [(a,b,c,d,"inject") for a,b,c,d in INJECTION_WORK]+
            [(a,b,c,d,"harvest") for a,b,c,d in HARVEST_WORK]):
            current=date(wave["inject_date"] if anchor=="inject" else wave["harvest_date"])+timedelta(days=off)
            if current<start or current>end:
                continue
            qty=int(wave[basis])
            if qty<1:continue
            key=(str(current),wave["farm_block"],code)
            if key not in grouped:
                grouped[key]=dict(date=str(current),farm_block=wave["farm_block"],
                    work_code=code,planned_qty=0,uom="Cây" if code=="CV021" else "Buồng",
                    note=note,sources=[],crop_cycle=wave.get("crop_cycle"),cohort=wave.get("cohort"),
                    parameter_status=wave.get("parameter_status"),count_status=wave.get("count_status"),
                    profile=wave.get("profile"),source_details=[])
                grouped[key]['farm_block_label']=wave.get('farm_block_label') or wave['farm_block']
            event=grouped[key]
            event["planned_qty"]+=qty
            event["sources"].append(wave["key"])
            event["source_details"].append(dict(key=wave["key"],quantity=qty,
                crop_cycle=wave.get("crop_cycle"),cohort=wave.get("cohort"),
                profile=wave.get("profile"),source_version=wave.get("source_version"),
                projected_cycle_no=wave.get('cycle_no'),generation=wave.get('generation',0),
                source_crop_cycle=wave.get('source_crop_cycle'),source_cohort=wave.get('source_cohort')))
            if event["parameter_status"]!=wave.get("parameter_status"):event["parameter_status"]="Mixed"
            if event["count_status"]!=wave.get("count_status"):event["count_status"]="Mixed"
            if event["profile"]!=wave.get("profile"):event["profile"]=None
            if event["crop_cycle"]!=wave.get("crop_cycle"):event["crop_cycle"]=None
            if event["cohort"]!=wave.get("cohort"):event["cohort"]=None
    events=[]
    for (day,block,code),row in sorted(grouped.items()):
        row["sources"]=sorted(set(row["sources"]))
        row["schedule_key"]="BOOK2-"+hashlib.sha256("|".join([day,block,code]+row["sources"]).encode()).hexdigest()[:34]
        events.append(row)
    return events

"""One presence per morning and afternoon; each session earns half a workday."""
from datetime import datetime, time


def presence_status(day, checkins):
    moments=sorted({datetime.fromisoformat(str(c['time']).replace(' ','T')[:19]) for c in checkins})
    moments=[m for m in moments if m.date()==day]
    morning=next((m for m in moments if m.time()<time(12)),None)
    afternoon=next((m for m in moments if m.time()>=time(12)),None)
    count=int(bool(morning))+int(bool(afternoon))
    return dict(status=('Absent','Half Day','Present')[count],working_hours=count*4,workdays=count/2,
        morning_present=int(bool(morning)),afternoon_present=int(bool(afternoon)),
        morning_time=str(morning) if morning else None,afternoon_time=str(afternoon) if afternoon else None,
        checkins=len(moments),needs_review=0,reason='',suggested_overtime=0,shift=None,
        in_time=None,out_time=None,late_entry=0,early_exit=0,overtime_hours=0)

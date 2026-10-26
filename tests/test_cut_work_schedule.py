import datetime as dt
import unittest

from lotus_farm import cut_forecast_rules as cut
from lotus_farm.cut_work_schedule import work_calendar, INJECTION_STEPS, HARVEST_STEPS

D = dt.date


def entry(*, block="LO-01", qty=100, source="log-1"):
    return dict(name=source, zone="A", farm_block=block, crop_cycle="CYCLE-A",
                plan_cohort="PLAN-A", source_ref=source, cut_date=D(2026, 1, 1), tree_qty=qty)


PROFILE = {**cut.DEFAULTS, "inject_to_budcut_days":16}


class Book2CareCalendarTests(unittest.TestCase):
    def test_unmapped_entry_is_never_allocated_to_any_block(self):
        rows, warnings, unmapped = work_calendar([entry(block=None)], PROFILE)
        self.assertEqual(rows, [])
        self.assertEqual(unmapped, 1)
        self.assertTrue(any("chưa được gắn lô" in w for w in warnings))

    def test_wrong_approved_timing_blocks_work_schedule(self):
        rows, warnings, _ = work_calendar([entry()], cut.DEFAULTS)
        self.assertEqual(rows, [])
        self.assertTrue(any("+16" in w for w in warnings))

    def test_four_waves_schedule_care_and_packaging_with_no_repeated_dates(self):
        rows, warnings, unmapped = work_calendar([entry()], PROFILE)
        self.assertEqual(unmapped, 0)
        self.assertEqual(len(rows), 4 * (len(INJECTION_STEPS) + len(HARVEST_STEPS)))
        self.assertEqual(len({r["schedule_key"] for r in rows}), len(rows))
        waves = cut.expand([entry()], PROFILE)
        first = waves[0]
        def day(code, date):
            return next(r for r in rows if r["work_code"] == code and r["date"] == str(date))
        self.assertEqual(day("CV020", first["inject_date"])["planned_qty"], first["shoot_qty"])
        for code, offset in (("CV023",7),("CV025",10),("CV027",13),
                             ("CV024",7),("CV026",10),("CV028",13),("CV031",16),
                             ("CV029",16),("CV033",16)):
            self.assertEqual(day(code, first["inject_date"]+dt.timedelta(days=offset))["farm_block"], "LO-01")
        harvest_window = day("CV034", first["harvest_date"]-dt.timedelta(days=10))
        self.assertEqual(harvest_window["window_end"], str(first["harvest_date"]-dt.timedelta(days=7)))
        self.assertEqual(day("CV035", first["harvest_date"])["planned_qty"], first["harvest_qty"])
        self.assertTrue(all(r["forecast_only"] for r in rows))
        self.assertTrue(any("DỰ KIẾN" in w for w in warnings))

    def test_two_cut_logs_same_block_day_are_aggregated_into_one_work_line(self):
        rows, warnings, _ = work_calendar(
            [entry(qty=100, source="s1"), entry(qty=200, source="s2")],
            PROFILE)
        self.assertEqual(len(rows), 4 * (len(INJECTION_STEPS)+len(HARVEST_STEPS)))
        a=cut.expand([entry(qty=100)],PROFILE)[0]
        b=cut.expand([entry(qty=200)],PROFILE)[0]
        first=next(r for r in rows if r["work_code"]=="CV020"
                   and r["date"]==str(a["inject_date"]))
        self.assertEqual(first["planned_qty"],a["shoot_qty"]+b["shoot_qty"])
        self.assertEqual(len(first["sources"]),2)

    def test_date_window_filters_without_changing_source(self):
        a=entry()
        first=cut.expand([a],PROFILE)[0]
        on=str(first["inject_date"])
        rows, _, _=work_calendar([a], PROFILE,from_date=on,to_date=on,farm_block="LO-01")
        self.assertTrue(rows)
        self.assertTrue(all(r["date"]==on for r in rows))
        self.assertEqual(len(work_calendar([a],PROFILE,farm_block="OTHER")[0]),0)
        with self.assertRaises(ValueError):
            work_calendar([a], PROFILE, from_date="2026-08-01", to_date="2026-07-31")


if __name__ == "__main__":
    unittest.main()

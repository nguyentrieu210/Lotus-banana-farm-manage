"""Explicit concurrency gate for disposable CI sites only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import frappe

from lotus_farm.api.v1.allocations import reserve
from lotus_farm.supply import reservation_total
from lotus_farm.tests.test_integration import LotusIntegrationTest


def run():
    site = frappe.local.site
    sites_path = frappe.local.sites_path
    if "test" not in site or not frappe.conf.get("allow_tests"):
        frappe.throw("Concurrency fixtures may run only on a disposable test site.")
    fixture = LotusIntegrationTest("test_allocation_capacity_and_release")
    fixture.setUp()
    second_order = frappe.copy_doc(fixture.so)
    second_order.insert()
    second_order.submit()
    requests = [
        (fixture.forecast.name, fixture.so.name, fixture.so.items[0].name),
        (fixture.forecast.name, second_order.name, second_order.items[0].name),
    ]
    frappe.db.commit()  # Required for independent connections to see the disposable fixtures.
    barrier = Barrier(2)

    def worker(args):
        frappe.init(site=site, sites_path=sites_path)
        frappe.connect()
        frappe.set_user("Administrator")
        try:
            barrier.wait(timeout=30)
            reserve(*args, 8000, uuid4().hex)
            frappe.db.commit()
            return "reserved"
        except frappe.ValidationError:
            frappe.db.rollback()
            return "rejected"
        finally:
            frappe.destroy()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, requests))
    assert sorted(results) == ["rejected", "reserved"], results
    assert reservation_total(forecast=fixture.forecast.name) == 8000
    return {"results": results, "reserved_kg": 8000, "safe_supply_kg": 10000}

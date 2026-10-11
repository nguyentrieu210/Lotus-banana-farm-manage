"""Validate the 222 ha Lotus Map -> ERP review bundle without needing Frappe."""
from collections import Counter
import json
import math

FORMAT = "lotus-erp-map-draft-v1"
MANUAL = {"A35", "C17", "C24", "E6", "E7"}


class MapBundleError(ValueError):
    pass


def _polygon(value, code):
    if not isinstance(value, dict) or value.get("type") != "Polygon":
        raise MapBundleError(code + ": only a WGS84 Polygon is accepted")
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 1:
        raise MapBundleError(code + ": expected one outer boundary")
    ring = coordinates[0]
    if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
        raise MapBundleError(code + ": ring must be closed")
    for point in ring:
        if (not isinstance(point, list) or len(point) != 2
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in point)
                or not 106.7 < point[0] < 106.9 or not 11.4 < point[1] < 11.8):
            raise MapBundleError(code + ": coordinates must be lon/lat in the farm vicinity")
    return value


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get("format") != FORMAT:
        raise MapBundleError("Unknown map bundle format")
    if (bundle.get("approved") is not False or bundle.get("requires_field_validation") is not True
            or bundle.get("verification") != "UNVERIFIED_PDF_ALIGNMENT"):
        raise MapBundleError("This importer accepts ONLY explicitly unverified PDF drafts")
    blocks = bundle.get("care_blocks")
    plots = bundle.get("irrigation_plots")
    if not isinstance(blocks, list) or not isinstance(plots, list) or len(blocks) != 64 or len(plots) != 205:
        raise MapBundleError("Expected 64 care blocks and 205 irrigation plot records")
    codes = set()
    owner_map = {}
    link_count = 0
    for b in blocks:
        code = b.get("code")
        if not isinstance(code, str) or not code or code in codes:
            raise MapBundleError("Missing or duplicated care block code")
        codes.add(code)
        if not (isinstance(b.get("area_ha_pdf"), (int, float)) and b["area_ha_pdf"] > 0):
            raise MapBundleError(code + ": missing source area")
        _polygon(b.get("geometry"), code)
        links = b.get("irrigation_codes")
        if not isinstance(links, list) or not links:
            raise MapBundleError(code + ": missing irrigation codes")
        for plot in links:
            owner_map.setdefault(plot, []).append(code)
            link_count += 1
    if abs(sum(b["area_ha_pdf"] for b in blocks) - 215.16) > .001 or link_count != 209:
        raise MapBundleError("PDF area total or 209 ownership references changed")
    counts = Counter()
    manual = set()
    for p in plots:
        code = p.get("code")
        if not isinstance(code, str) or not code or counts[code]:
            raise MapBundleError("Duplicated/missing irrigation plot code")
        counts[code] += 1
        _polygon(p.get("geometry"), code)
        expected = owner_map.get(code)
        if not expected or expected != p.get("candidate_blocks", []) and code != "E6":
            raise MapBundleError(code + ": owners disagree with PDF table")
        if code == "E6" and (expected != ["E4"] or p.get("candidate_blocks") != ["E4", "E5"]):
            raise MapBundleError("E6 note conflict must remain explicit")
        if code in MANUAL:
            manual.add(code)
            if p.get("parent_block") is not None or p.get("needs_manual_review") is not True:
                raise MapBundleError(code + ": shared/contradictory ownership must remain unassigned")
        else:
            if expected != [p.get("parent_block")] or p["parent_block"] not in codes:
                raise MapBundleError(code + ": parent is not a single source-listed care block")
    if set(counts) != set(owner_map) or manual != MANUAL:
        raise MapBundleError("PDF codes or manual-review exceptions changed")
    if not isinstance(bundle.get("manual_review"), list) or {x.get("code") for x in bundle["manual_review"]} != MANUAL:
        raise MapBundleError("Required conflict report is missing")
    return dict(care_blocks=64, irrigation_plots=205, ownership_links=209,
                direct_parent_plots=200, unresolved_codes=sorted(MANUAL),
                unverified=True)


def load_bundle(raw):
    if isinstance(raw, bytes):
        if len(raw) > 10 * 1024 * 1024:
            raise MapBundleError("Map bundle exceeds 10 MB")
        raw = raw.decode("utf-8")
    value = json.loads(raw) if isinstance(raw, str) else raw
    validate_bundle(value)
    return value

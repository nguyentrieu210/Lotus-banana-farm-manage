# Vườn 180 Thuận Phú: original HTT 170ha KML

The user confirmed that the existing ERP farm `LOTUS-180` / Vườn 180 Thuận Phú corresponds to `HTT_170ha_Model.kml`. The registered farm area remains 180 ha.

Original KML SHA256: `842d41bad538cadd933f002bad2fc2b13cde6bdbccabc51d7195098d34e995dc`. Source repository `lotus-map`, commit `404f43a`, retains the approved drawing coordinates in its original care layer. Lot codes, source label positions and source areas come from `labels.json` / `htt170`.

There are 82 unique ERP care-block codes across zones A–F, with source areas totalling 162.38 ha. Each code is matched to the smallest existing closed source ring containing its original label point. 81 uniquely identified lot rings are closed. C-13 has no suitable closed lot ring: its label falls inside a much larger enclosing outline (over 40 times its stated area), which is deliberately rejected. C-13 retains its original label point and the source drawing linework, without a fabricated polygon. Every selected closed coordinate sequence was checked verbatim against the original KML; no flycam interpretation, inferred division, coordinate transform, or area-fitting is used.

`data/farm180-care-boundaries.geojson` contains 81 original closed rings and the C-13 original label point. `data/farm180-perimeter.geojson` contains 413 original care drawing line strings, each also checked against the original KML. No as-built boundary file is used. Source area, registered farm area, and measured geometry area remain separate values.

`tools/import_farm180_map.py` previews by default. `--commit --backup <new path>` creates missing ERP blocks and draft geometry versions. `--replace-rejected-source` removes only the exact 81 Draft geometry records from the explicitly rejected flycam source hash, after saving a snapshot. It also removes the explicitly identified incorrect C-13 enclosing polygon from the original-source trial. Approved or unrelated versions are retained. Database geometry remains Draft pending the application's normal approval workflow, even though the coordinate source is the original KML.

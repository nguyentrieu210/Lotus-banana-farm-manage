# Vườn 180 Thuận Phú: confirmed HTT 170ha source

On 2026-10-20 the user explicitly confirmed that their “180 ha” request refers to `HTT_170ha_Model.kml` in Lotus Map. The existing business farm remains `LOTUS-180` / Vườn 180 Thuận Phú; its registered 180 ha area is unchanged.

Source repository commit: `404f43a`. Import uses the latest `v2/data/farms/farm170/as-built/lots.geojson` and the locked `as-built/original-perimeter.geojson`. Coordinates are preserved; no map registration is applied to vectors. The common flycam raster uses its existing display alignment.

- 82 care-block identifiers in six zones A–F; source areas total 162.38 ha.
- 81 closed Polygon/MultiPolygon shapes, inserted as Draft Farm Block Geometry.
- C-13 has open source linework. It remains a master care block with its stated 0.82 ha source area and dashed map linework, without an invented closed polygon or geometry area.
- The six-part outer perimeter remains exactly as in the pinned source. The extension-selection reference is excluded.

Source areas, the registered farm area, and measured geometry areas express different inputs. None is modified to force agreement.

`tools/import_farm180_map.py` previews by default. `--commit --backup <new path>` adds missing blocks and new draft geometry versions, with a JSON snapshot first. It never deletes existing geometry or approves draft interpretations. Reruns compare exact shape content and preserve business block identifiers.

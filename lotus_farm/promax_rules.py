"""Map geometry of a lô: the checks on a GeoJSON polygon (map imports, Farm Block Geometry) and on GPS coordinates."""
import json
import math
from lotus_farm.rules import RuleError


def geometry(value):
    value = json.loads(value) if isinstance(value, str) else value
    if value.get('type') == 'Feature':
        value = value.get('geometry') or {}
    if value.get('type') not in ('Polygon', 'MultiPolygon'):
        raise RuleError('Hình học thửa phải là Polygon hoặc MultiPolygon theo WGS84.')
    polygons = [value['coordinates']] if value['type'] == 'Polygon' else value['coordinates']
    if not polygons:
        raise RuleError('Hình học cần ít nhất một đa giác.')
    for polygon in polygons:
        if not polygon:
            raise RuleError('Đa giác phải có đường bao ngoài.')
        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise RuleError('Đường bao đa giác phải khép kín và có ít nhất bốn điểm.')
            for point in ring:
                if len(point) != 2:
                    raise RuleError('Tọa độ phải là cặp kinh độ, vĩ độ.')
                coordinates(*reversed(point))
            area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))
            if abs(area) < 1e-12:
                raise RuleError('Đường bao đa giác có diện tích bằng 0.')
            # Reject crossing edges; touch at neighboring endpoints is allowed.
            def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            edges=list(zip(ring,ring[1:]))
            for i,(a,b) in enumerate(edges):
                for j,(c,d) in enumerate(edges):
                    if j<=i+1 or (i==0 and j==len(edges)-1):continue
                    if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:
                        raise RuleError('Đường bao đa giác tự cắt nhau.')
    return value


def coordinates(latitude, longitude):
    try: latitude,longitude=float(latitude),float(longitude)
    except (TypeError,ValueError):raise RuleError('GPS cần vĩ độ và kinh độ dạng số.') from None
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90<=latitude<=90 or not -180<=longitude<=180:
        raise RuleError('Tọa độ GPS nằm ngoài phạm vi WGS84.')
    return latitude,longitude

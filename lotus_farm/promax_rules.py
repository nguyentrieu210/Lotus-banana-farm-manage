"""Contracts shared by reporting, field capture and controlled extraction."""
import json
import math
from datetime import date, timedelta
from lotus_farm.rules import RuleError, quantity


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


def point_in_geometry(latitude, longitude, value):
    latitude,longitude=coordinates(latitude,longitude)
    value=geometry(value)
    def inside(ring):
        result=False
        for a,b in zip(ring,ring[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            if abs(dx*(latitude-a[1])-dy*(longitude-a[0]))<1e-10 and min(a[0],b[0])<=longitude<=max(a[0],b[0]) and min(a[1],b[1])<=latitude<=max(a[1],b[1]):return True
            if (a[1]>latitude)!=(b[1]>latitude) and longitude<(b[0]-a[0])*(latitude-a[1])/(b[1]-a[1])+a[0]:result=not result
        return result
    polygons=[value['coordinates']] if value['type']=='Polygon' else value['coordinates']
    return any(inside(p[0]) and not any(inside(h) for h in p[1:]) for p in polygons)


def work_completion(tasks):
    """Each task is equally weighted; different units are never summed."""
    values=[min(float(quantity(t['completed_qty']))/float(quantity(t['planned_qty'],positive=True)),1) for t in tasks]
    return sum(values)/len(values)*100 if values else None


def vintage_choice(snapshots, period_start, horizon_weeks):
    start=date.fromisoformat(str(period_start)[:10]);cutoff=start-timedelta(weeks=horizon_weeks)
    candidates=[s for s in snapshots if str(s['released_at'])[:10]<=cutoff.isoformat()]
    return max(candidates,key=lambda s:(str(s['released_at']),int(s.get('revision_no') or 1),s['name'])) if candidates else None


def split_amount(reserved, available, requested):
    reserved=quantity(reserved,positive=True);requested=quantity(requested,positive=True);available=quantity(available)
    if requested>reserved or requested>available:
        raise RuleError('Số chuyển sang hàng thực vượt phân bổ tương lai còn lại hoặc số giữ hàng thực tế.')
    return float(requested),float(reserved-requested)


def weighted_packout(samples, minimum):
    if len(samples)<minimum or minimum<1:raise RuleError('Chưa đủ mẫu đóng gói đã đối chiếu đầy đủ.')
    raw=sum(quantity(s['input_kg'],positive=True) for s in samples)
    finished=sum(quantity(s['finished_kg']) for s in samples)
    if finished>raw:raise RuleError('Khối lượng thành phẩm vượt nguyên liệu đầu vào đã đối chiếu.')
    return dict(sample_count=len(samples),input_kg=float(raw),finished_kg=float(finished),packout_rate_percent=float(finished/raw*100))


def kml_geometries(data):
    """Preview placemarks; names never become automatic Farm/Plot mappings."""
    from xml.etree import ElementTree
    if len(data)>10*1024*1024 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise RuleError('Tệp KML quá lớn hoặc có khai báo thực thể không được hỗ trợ.')
    try:root=ElementTree.fromstring(data)
    except ElementTree.ParseError:raise RuleError('Không đọc được tệp KML.') from None
    result=[]
    for placemark in root.findall('.//{*}Placemark'):
        polygons=[]
        for polygon in placemark.findall('.//{*}Polygon'):
            rings=[]
            for boundary in ['outerBoundaryIs','innerBoundaryIs']:
                for element in polygon.findall('{*}'+boundary+'/{*}LinearRing/{*}coordinates'):
                    rings.append([[float(v) for v in point.split(',')[:2]] for point in (element.text or '').split()])
            if rings:polygons.append(rings)
        if polygons:
            value=dict(type='Polygon',coordinates=polygons[0]) if len(polygons)==1 else dict(type='MultiPolygon',coordinates=polygons)
            name=placemark.find('{*}name')
            result.append(dict(name=name.text if name is not None else None,geometry=geometry(value)))
    if not result:raise RuleError('Tệp KML không có vùng đa giác nào được hỗ trợ.')
    return result

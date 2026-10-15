"""Independent, opt-in route records. Coordinates are approximate city positions."""
import json
import math
import database
import map_data


def validate_points(points):
    if not 2 <= len(points) <= 40:
        raise ValueError('请填写起点和终点，最多支持 40 个地点')
    result = []
    for point in points:
        name = str(point['name']).strip()
        try:
            lon, lat = float(point['lon']), float(point['lat'])
        except (ValueError, TypeError):
            raise ValueError('经纬度请填写数字') from None
        if not name or not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -85 <= lat <= 85:
            raise ValueError('地点名称不能为空；经度须在 -180～180，纬度须在 -85～85')
        result.append(dict(name=name, lon=lon, lat=lat))
    if all((p['lon'], p['lat']) == (result[0]['lon'], result[0]['lat']) for p in result):
        raise ValueError('起点与终点不能全部相同')
    return result


def parse_line(text):
    """Exact local names only: never silently substitute an airport with its city."""
    parts = text.strip().replace('，', ',').split('|')
    if len(parts) == 2:
        coords = parts[1].split(',')
        if len(coords) != 2:
            raise ValueError('坐标格式：地点名称 | 经度, 纬度')
        try:
            return dict(name=parts[0].strip(), lon=float(coords[0]), lat=float(coords[1]))
        except ValueError:
            raise ValueError('经纬度请填写数字') from None
    name = text.strip()
    found = map_data.places().get(name) or map_data.places().get(name.removesuffix('市'))
    if found:
        return dict(name=name, lon=found[0], lat=found[1])
    raise ValueError(f'未找到「{name}」，请从候选选择，或填写：名称 | 经度, 纬度')


def init_db():
    with database.get_conn() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS travel_routes (id INTEGER PRIMARY KEY, mode TEXT NOT NULL, title TEXT NOT NULL, points TEXT NOT NULL)')


def list_routes(mode):
    init_db()
    with database.get_conn() as conn:
        rows = conn.execute('SELECT * FROM travel_routes WHERE mode=? ORDER BY id DESC', (mode,)).fetchall()
    return [dict(row) | {'points': json.loads(row['points'])} for row in rows]


def save_route(mode, title, points, route_id=None):
    if mode not in ('air', 'rail'):
        raise ValueError('未知交通方式')
    points = validate_points(points)
    title = title.strip() or f"{points[0]['name']} → {points[-1]['name']}"
    init_db()
    with database.get_conn() as conn:
        values = (title, json.dumps(points, ensure_ascii=False))
        if route_id is None:
            return conn.execute('INSERT INTO travel_routes(title,points,mode) VALUES(?,?,?)', (*values, mode)).lastrowid
        if conn.execute('UPDATE travel_routes SET title=?,points=? WHERE id=? AND mode=?', (*values, route_id, mode)).rowcount != 1:
            raise ValueError('这条线路已不存在，请新建线路')
    return route_id


def delete_route(mode, route_id):
    with database.get_conn() as conn:
        conn.execute('DELETE FROM travel_routes WHERE id=? AND mode=?', (route_id, mode))

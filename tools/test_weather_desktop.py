import os
import sys
import types

root = r"D:\Waylore"
sys.path.insert(0, root)

ft = types.ModuleType("flet")
class Icons:
    pass
for name in ["WB_SUNNY", "WB_CLOUDY", "CLOUD", "FOGGY", "GRAIN",
             "WATER_DROP", "SNOWING", "CLOUDY_SNOWING", "THUNDERSTORM"]:
    setattr(Icons, name, name)
ft.Icons = Icons
sys.modules["flet"] = ft

db = types.ModuleType("database")
db.DB_PATH = os.path.join(root, "data", "test.db")
sys.modules["database"] = db

nt = types.ModuleType("network_tls")
nt.https_context = lambda: None
sys.modules["network_tls"] = nt

import weather

print("cities:", len(weather._load_cities()))
for q in ["枣庄", "义乌", "安溪", "石狮", "昆山"]:
    print("search", q, "->", [c["name"] for c in weather.search_city(q)][:3])

loc = weather.locate_ip()
print("locate_ip ->", loc)
if loc:
    data = weather.fetch(loc["lat"], loc["lon"])
    print("fetch ->", None if not data else {k: data[k] for k in ("temp", "text", "humidity", "wind")})

print("nearest Jinan ->", weather._nearest_city(36.65, 117.12))

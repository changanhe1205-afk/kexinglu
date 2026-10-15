# 第三方资源与数据来源 / Third-party notices

本项目包含第三方依赖与地理数据，它们保留各自的许可和使用条件。这里记录来源，不把未确认许可的数据宣称为公共领域，也不表示本项目获得航空公司或铁路机构的官方背书。

| 资源 / Resource | 来源 / Source |
| --- | --- |
| Flet 桌面框架 | https://github.com/flet-dev/flet |
| Pillow 图像处理 | https://python-pillow.github.io/ |
| certifi 根证书 | https://github.com/certifi/python-certifi |
| pypinyin 拼音转换 | https://github.com/mozillazg/python-pinyin |
| PyInstaller 打包工具 | https://pyinstaller.org/ |
| Natural Earth 世界陆地轮廓（公共领域） | https://www.naturalearthdata.com/about/terms-of-use/ |
| OurAirports 机场坐标（公共领域） | https://ourairports.com/data/ |
| Wikidata 车站坐标（CC0 结构化数据） | https://www.wikidata.org/wiki/Wikidata:Licensing |
| 中国行政区划简化数据 | 原项目内置快照，来源标注为阿里云 DataV；参见 `map_data.py`。 |
| 铁路站名 | 12306 station_name.js 快照，参见 `stations_data.py`。 |

更详细的抓取时间、筛选条件与链接位于 `assets/map/*-source.txt` 和 `assets/airline-sources.txt`。车站坐标不用于导航测量。航空公司名称、代码及相关标识属于相应主体；票面为应用内纪念设计，不可作为乘车或登机凭证。

在线功能还使用高德地图瓦片、IP-API 与 Open-Meteo，以及用户自行配置的 AI 服务。可用性与使用条件由对应服务商决定。

Third-party dependencies, datasets, and names retain their respective rights and terms. Public-domain and CC0 statements apply only to the identified datasets, not automatically to the entire repository. Airline and railway references do not imply endorsement. Tickets generated here are keepsakes, not valid boarding or travel documents.

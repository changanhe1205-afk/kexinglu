"""客行录 · 旅程票根模块（界面部分）

机票、火车票也是值得收藏的"影笺"：每一次出发都有一段故事。
    · 手动填写出发地 / 目的地等信息，生成一张登机牌风格的纪念票根
    · 把 12306 / 航旅纵横 / 航司截图交给 AI 识别，自动填好表单
    · 支持任何 OpenAI 兼容的视觉模型接口（默认智谱 glm-4v-flash，免费）

布局：
    ┌─ 白色顶栏：标题 / 识别导入 / 保存 ────────────────────────────────┐
    │ 左栏 300        │ 中间：登机牌风格大票根（按交通工具配色）      │ 右栏 340       │
    │ 行程统计         │  打孔线 / 航线虚线 / 票号座位                │ 填写票根信息    │
    │ 票根列表         │  空状态引导                                 │ AI 识别 + 设置  │
    └───────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import uuid
import time
from collection_motion import motion_enabled
from datetime import datetime

import flet as ft
from date_utils import calendar_date, open_calendar
import flet.canvas as cv

import ai_ocr
import ticket_db as tdb
import ticket_design
from ticket_money import amount_text
import theme
from stations_data import STATIONS_12306
from theme import badge, card_shadow, empty_state, glass_surface, icon_badge

# ---------------- 仿真票根：航司品牌 / 机场三字码 / 条码 ----------------
AIRLINES = {
    "MU": ("中国东方航空", "#1A3C8C"), "CA": ("中国国际航空", "#C8102E"),
    "CZ": ("中国南方航空", "#0078BE"), "HU": ("海南航空", "#B01E23"),
    "MF": ("厦门航空", "#0069AA"), "3U": ("四川航空", "#D7000F"),
    "ZH": ("深圳航空", "#C4002F"), "FM": ("上海航空", "#00388F"),
    "9C": ("春秋航空", "#3F9C35"), "HO": ("吉祥航空", "#E60012"),
    "GJ": ("浙江长龙航空", "#C7A100"), "KN": ("中国联合航空", "#C7000B"),
    "GS": ("天津航空", "#C7000B"), "SC": ("山东航空", "#1C64A8"),
    "TV": ("西藏航空", "#B9503C"), "PN": ("西部航空", "#5B2C83"),
    "G5": ("华夏航空", "#176EAD"), "EU": ("成都航空", "#C03A35"),
    "JD": ("北京首都航空", "#B83236"), "8L": ("云南祥鹏航空", "#B84032"),
    "NS": ("河北航空", "#33729A"), "KY": ("昆明航空", "#A33239"),
    "QW": ("青岛航空", "#397695"), "DR": ("苏南瑞丽航空", "#94723E"),
    "DZ": ("东海航空", "#32748A"), "OQ": ("重庆航空", "#3474A7"),
    "RY": ("江西航空", "#5C7F9D"), "GY": ("多彩贵州航空", "#916095"),
    "AQ": ("九元航空", "#C47832"), "BK": ("奥凯航空", "#AF4935"),
    "GX": ("北部湾航空", "#38798D"), "FU": ("福州航空", "#B03D38"),
    "UQ": ("乌鲁木齐航空", "#B58532"), "9H": ("长安航空", "#A73A3D"),
    "GT": ("桂林航空", "#A64055"), "A6": ("湖南航空", "#B13C35"),
    "CN": ("大新华航空", "#A83639"), "Y8": ("金鹏航空", "#A77938"),
    "JR": ("幸福航空", "#4B8C77"),
    "9D": ("天骄航空", "#4D8090"), "LT": ("龙江航空", "#466D9D"),
}
AIRLINE_FALLBACK = ("中国民航", "#3A5A8C")

# 航司品牌宣传语（竖排短句, 主宣传语, 联盟/卖点小标）——用于票根背面广告位
AIRLINE_ADS = {
    "MU": ("东方万里", "东方万里行 · 精彩每一程", "天合联盟成员"),
    "CA": ("凤凰知音", "凤凰知音 · 伴您翱翔五洲", "星空联盟成员"),
    "CZ": ("南航明珠", "明珠相伴 · 连通世界", "南航明珠会员"),
    "MF": ("白鹭相伴", "白鹭相伴 · 精彩永随", "天合联盟成员"),
    "HU": ("海航之约", "不期而遇 · 相伴相惜", "五星航空"),
    "3U": ("美丽川航", "美丽川航 · 至真至诚", "熊猫之路航线"),
    "ZH": ("深航领先", "深圳航空 · 领先一步", "星空联盟成员"),
    "FM": ("满意到家", "上海航空 · 满意到家", "天合联盟成员"),
    "9C": ("想飞就飞", "春秋航空 · 想飞就飞", "高性价比之选"),
    "HO": ("吉祥如意", "吉祥航空 · 如意到家", "星空联盟优连伙伴"),
    "GJ": ("长龙相伴", "长龙航空 · 一路相伴", "亚运合作伙伴"),
    "KN": ("实惠联航", "中国联航 · 实惠出行", "经济出行之选"),
    "GS": ("快乐起航", "天津航空 · 快乐起航", "环渤海航线网络"),
    "SC": ("厚道山航", "厚道山航 · 品质飞翔", "山东人的航空"),
    "TV": ("雪域之翼", "西藏航空 · 雪域之翼", "高原航线专家"),
    "PN": ("年轻个性", "西部航空 · 年轻个性", "低成本航空"),
}
AIRLINE_AD_FALLBACK = ("云端之约", "中国民航 · 云端之约", "安全准点出行")

# 全球机场选择库（三字码, 机场名）——出发地/目的地下拉用
AIRPORTS_GLOBAL = [
    ("PEK", "北京首都国际机场"), ("PKX", "北京大兴国际机场"),
    ("PVG", "上海浦东国际机场"), ("SHA", "上海虹桥国际机场"),
    ("CAN", "广州白云国际机场"), ("SZX", "深圳宝安国际机场"),
    ("CTU", "成都双流国际机场"), ("TFU", "成都天府国际机场"),
    ("KMG", "昆明长水国际机场"), ("XIY", "西安咸阳国际机场"),
    ("CKG", "重庆江北国际机场"), ("HGH", "杭州萧山国际机场"),
    ("NKG", "南京禄口国际机场"), ("WUH", "武汉天河国际机场"),
    ("XUZ", "徐州观音国际机场"),
    ("CSX", "长沙黄花国际机场"), ("XMN", "厦门高崎国际机场"),
    ("TAO", "青岛胶东国际机场"), ("DLC", "大连周水子国际机场"),
    ("SYX", "三亚凤凰国际机场"), ("HAK", "海口美兰国际机场"),
    ("TSN", "天津滨海国际机场"), ("CGO", "郑州新郑国际机场"),
    ("FOC", "福州长乐国际机场"), ("SHE", "沈阳桃仙国际机场"),
    ("HRB", "哈尔滨太平国际机场"), ("URC", "乌鲁木齐地窝堡国际机场"),
    ("KWE", "贵阳龙洞堡国际机场"), ("LHW", "兰州中川国际机场"),
    ("NNG", "南宁吴圩国际机场"), ("KWL", "桂林两江国际机场"),
    ("WNZ", "温州龙湾国际机场"), ("NGB", "宁波栎社国际机场"),
    ("TNA", "济南遥墙国际机场"), ("HFE", "合肥新桥国际机场"),
    ("KHN", "南昌昌北国际机场"), ("TYN", "太原武宿国际机场"),
    ("SJW", "石家庄正定国际机场"), ("CGQ", "长春龙嘉国际机场"),
    ("HET", "呼和浩特白塔国际机场"), ("INC", "银川河东国际机场"),
    ("XNN", "西宁曹家堡国际机场"), ("LXA", "拉萨贡嘎机场"),
    ("WUX", "无锡硕放机场"), ("JJN", "泉州晋江国际机场"),
    ("ZUH", "珠海金湾机场"), ("SWA", "揭阳潮汕国际机场"),
    ("HKG", "香港国际机场"), ("MFM", "澳门国际机场"),
    ("TPE", "台湾桃园国际机场"), ("TSA", "台北松山机场"), ("KHH", "高雄国际机场"),
    ("HND", "东京羽田国际机场"), ("NRT", "东京成田国际机场"),
    ("KIX", "大阪关西国际机场"), ("NGO", "名古屋中部国际机场"),
    ("FUK", "福冈机场"), ("CTS", "札幌新千岁机场"), ("OKA", "那霸机场"),
    ("ICN", "首尔仁川国际机场"), ("PUS", "釜山金海国际机场"), ("CJU", "济州国际机场"),
    ("SIN", "新加坡樟宜国际机场"),
    ("BKK", "曼谷素万那普国际机场"), ("DMK", "曼谷廊曼国际机场"),
    ("HKT", "普吉国际机场"), ("CNX", "清迈国际机场"),
    ("KUL", "吉隆坡国际机场"), ("CGK", "雅加达苏加诺哈达国际机场"),
    ("DPS", "巴厘岛伍拉赖国际机场"), ("MNL", "马尼拉尼诺阿基诺国际机场"),
    ("HAN", "河内内排国际机场"), ("SGN", "胡志明市新山一国际机场"),
    ("DAD", "岘港国际机场"), ("PNH", "金边国际机场"),
    ("KTM", "加德满都特里布万国际机场"), ("DEL", "德里英迪拉甘地国际机场"),
    ("BOM", "孟买贾特拉帕蒂国际机场"), ("CMB", "科伦坡班达拉奈克国际机场"),
    ("MLE", "马累维拉纳国际机场"), ("DXB", "迪拜国际机场"),
    ("AUH", "阿布扎比国际机场"), ("DOH", "多哈哈马德国际机场"),
    ("IST", "伊斯坦布尔国际机场"), ("SVO", "莫斯科谢列梅捷沃国际机场"),
    ("LHR", "伦敦希思罗机场"), ("LGW", "伦敦盖特威克机场"),
    ("CDG", "巴黎戴高乐机场"), ("FRA", "法兰克福机场"),
    ("MUC", "慕尼黑机场"), ("BER", "柏林勃兰登堡机场"),
    ("AMS", "阿姆斯特丹史基浦机场"), ("ZRH", "苏黎世机场"),
    ("GVA", "日内瓦国际机场"), ("FCO", "罗马菲乌米奇诺机场"),
    ("MXP", "米兰马尔彭萨机场"), ("MAD", "马德里巴拉哈斯机场"),
    ("BCN", "巴塞罗那埃尔普拉特机场"), ("VIE", "维也纳国际机场"),
    ("PRG", "布拉格瓦茨拉夫哈维尔机场"), ("ATH", "雅典国际机场"),
    ("LIS", "里斯本温贝托德尔加多机场"), ("CPH", "哥本哈根凯斯楚普机场"),
    ("ARN", "斯德哥尔摩阿兰达机场"), ("OSL", "奥斯陆加勒穆恩机场"),
    ("HEL", "赫尔辛基万塔机场"), ("WAW", "华沙肖邦机场"),
    ("JFK", "纽约肯尼迪国际机场"), ("EWR", "纽瓦克自由国际机场"),
    ("LAX", "洛杉矶国际机场"), ("SFO", "旧金山国际机场"),
    ("ORD", "芝加哥奥黑尔国际机场"), ("DFW", "达拉斯沃斯堡国际机场"),
    ("ATL", "亚特兰大哈茨菲尔德国际机场"), ("SEA", "西雅图塔科马国际机场"),
    ("BOS", "波士顿洛根国际机场"), ("IAD", "华盛顿杜勒斯国际机场"),
    ("MIA", "迈阿密国际机场"), ("MCO", "奥兰多国际机场"),
    ("HNL", "檀香山国际机场"), ("YYZ", "多伦多皮尔逊国际机场"),
    ("YVR", "温哥华国际机场"), ("YUL", "蒙特利尔特鲁多国际机场"),
    ("MEX", "墨西哥城贝尼托胡亚雷斯国际机场"), ("GRU", "圣保罗瓜鲁柳斯国际机场"),
    ("EZE", "布宜诺斯艾利斯埃塞萨国际机场"), ("SCL", "圣地亚哥阿图罗梅里诺机场"),
    ("LIM", "利马豪尔赫查韦斯国际机场"), ("BOG", "波哥大埃尔多拉多国际机场"),
    ("CAI", "开罗国际机场"), ("JNB", "约翰内斯堡坦博国际机场"),
    ("NBO", "内罗毕乔莫肯雅塔国际机场"), ("ADD", "亚的斯亚贝巴博莱国际机场"),
    ("CMN", "卡萨布兰卡穆罕默德五世机场"),
    ("SYD", "悉尼金斯福德史密斯机场"), ("MEL", "墨尔本机场"),
    ("BNE", "布里斯班机场"), ("PER", "珀斯机场"),
    ("AKL", "奥克兰国际机场"), ("CHC", "基督城国际机场"),
]
_AIRPORT_NAMES = {name for _, name in AIRPORTS_GLOBAL}

# 火车站选择库（高铁/火车用）——覆盖全国主要客运站
STATIONS_GLOBAL = [
    "北京南", "北京西", "北京丰台", "北京朝阳", "上海虹桥", "上海", "上海南",
    "广州南", "广州白云", "深圳北", "福田", "香港西九龙",
    "成都东", "成都西", "重庆北", "重庆西", "杭州东", "杭州西",
    "南京南", "武汉", "汉口", "武昌", "长沙南", "西安北",
    "郑州东", "天津南", "天津西", "济南西", "济南东", "青岛北",
    "厦门北", "厦门", "福州南", "福州", "合肥南", "南昌西",
    "贵阳北", "贵阳东", "昆明南", "南宁东", "桂林北",
    "太原南", "石家庄", "沈阳北", "沈阳", "长春西", "哈尔滨西", "大连北",
    "兰州西", "乌鲁木齐", "西宁", "银川", "呼和浩特东",
    "海口东", "三亚", "苏州", "无锡东", "宁波", "温州南", "金华",
    "徐州东", "洛阳龙门", "宜昌东", "襄阳东", "怀化南", "衡阳东", "柳州",
    "遵义", "都匀东", "独山东", "凯里南", "安顺西", "六盘水", "毕节",
    "铜仁", "宜宾西", "绵阳", "德阳", "南充北", "达州",
    "惠州北", "珠海", "佛山西", "东莞南", "潮汕", "揭阳",
    "泉州", "莆田", "漳州", "龙岩", "三明北",
    "黄山北", "九华山", "庐山", "上饶", "鹰潭北",
    "宝鸡南", "延安", "大同南", "运城北", "临汾西",
    "宜昌北", "恩施", "张家界西", "凤凰古城", "韶山南",
]

# 搜索索引：(站名, 简拼, 全拼, 拼在一起的检索串)。建一次，后面反复用。
STATION_INDEX = [
    (name, abbr, full, (name + abbr + full).lower())
    for name, abbr, full in STATIONS_12306
]
_BIG_STATIONS = set(STATIONS_GLOBAL)

# 机场真实运营方（票头用，按三字码查）——不虚构集团名
AIRPORT_GROUPS = {
    "PEK": ("首都机场集团有限公司", "CAPITAL AIRPORTS GROUP"),
    "PKX": ("首都机场集团有限公司", "CAPITAL AIRPORTS GROUP"),
    "PVG": ("上海机场（集团）有限公司", "SHANGHAI AIRPORT GROUP"),
    "SHA": ("上海机场（集团）有限公司", "SHANGHAI AIRPORT GROUP"),
    "CAN": ("广东省机场管理集团有限公司", "GUANGDONG AIRPORT GROUP"),
    "SZX": ("深圳市机场（集团）有限公司", "SHENZHEN AIRPORT GROUP"),
    "XMN": ("元翔（厦门）国际航空港", "XIAMEN IPORT GROUP"),
    "KMG": ("云南机场集团有限责任公司", "YUNNAN AIRPORT GROUP"),
    "CTU": ("四川省机场集团有限公司", "SICHUAN AIRPORT GROUP"),
    "TFU": ("四川省机场集团有限公司", "SICHUAN AIRPORT GROUP"),
    "XIY": ("西部机场集团有限公司", "WESTERN AIRPORT GROUP"),
    "CKG": ("重庆机场集团有限公司", "CHONGQING AIRPORT GROUP"),
    "HGH": ("杭州萧山国际机场有限公司", "HANGZHOU INTL AIRPORT"),
    "NKG": ("东部机场集团有限公司", "EASTERN AIRPORT GROUP"),
    "WUH": ("湖北省机场集团有限公司", "HUBEI AIRPORT GROUP"),
    "CSX": ("湖南省机场管理集团有限公司", "HUNAN AIRPORT GROUP"),
    "TAO": ("青岛国际机场集团有限公司", "QINGDAO INTL AIRPORT GROUP"),
    "HKG": ("香港机场管理局", "AIRPORT AUTHORITY HONG KONG"),
    "MFM": ("澳门国际机场专营股份", "MACAU INTL AIRPORT"),
    "TPE": ("桃园国际机场公司", "TAOYUAN INTL AIRPORT"),
}

# 各航司示例航班号（选中航司后推荐，仍可直接手输）
AIRLINE_FLIGHTS = {
    "MU": ["MU5101", "MU5646", "MU583", "MU2117", "MU5409"],
    "CA": ["CA1501", "CA1835", "CA910", "CA1121", "CA401"],
    "CZ": ["CZ3101", "CZ3901", "CZ6223", "CZ350", "CZ1835"],
    "MF": ["MF8101", "MF8167", "MF8501", "MF8103", "MF8527"],
    "HU": ["HU7101", "HU7705", "HU7301", "HU7289"],
    "3U": ["3U8611", "3U8901", "3U8633", "3U8885"],
    "ZH": ["ZH9101", "ZH9501", "ZH9703", "ZH9845"],
    "FM": ["FM9101", "FM9301", "FM9203", "FM9421"],
    "9C": ["9C8811", "9C8901", "9C8601", "9C8735"],
    "HO": ["HO1111", "HO1281", "HO1071", "HO1195"],
    "GJ": ["GJ8001", "GJ8101", "GJ8887"],
    "KN": ["KN2901", "KN5901", "KN5905"],
    "GS": ["GS6601", "GS7801", "GS7855"],
    "SC": ["SC4601", "SC4801", "SC4901", "SC4951"],
    "TV": ["TV9801", "TV9901", "TV6011"],
    "PN": ["PN6201", "PN6301", "PN6427"],
}

# 火车/高铁示例车次（选火车类交通工具时推荐）
TRAIN_SAMPLES = ["G1", "G102", "G834", "G2963", "D2811", "D1794",
                 "K112", "Z150", "C6012", "T8"]


def _pinyin_name(name: str) -> str:
    """中文姓名转大写拼音（王运美 → WANGYUNMEI）；已是英文则原样大写。"""
    s = (name or "").strip()
    if not s:
        return ""
    if any("一" <= ch <= "鿿" for ch in s):
        try:
            from pypinyin import lazy_pinyin
            return "".join(lazy_pinyin(s)).upper()
        except Exception:
            return s
    return s.upper()

AIRPORT_CODES = [
    ("浦东", "PVG"), ("虹桥", "SHA"), ("大兴", "PKX"), ("首都", "PEK"),
    ("高崎", "XMN"), ("白云", "CAN"), ("宝安", "SZX"), ("双流", "CTU"),
    ("天府", "TFU"), ("咸阳", "XIY"), ("江北", "CKG"), ("萧山", "HGH"),
    ("禄口", "NKG"), ("天河", "WUH"), ("黄花", "CSX"), ("胶东", "TAO"),
    ("流亭", "TAO"), ("周水子", "DLC"), ("凤凰", "SYX"), ("美兰", "HAK"),
    ("滨海", "TSN"), ("新郑", "CGO"), ("长乐", "FOC"), ("桃仙", "SHE"),
    ("太平", "HRB"), ("地窝堡", "URC"), ("龙洞堡", "KWE"), ("中川", "LHW"),
    ("吴圩", "NNG"), ("两江", "KWL"), ("龙湾", "WNZ"), ("栎社", "NGB"),
    ("遥墙", "TNA"), ("长水", "KMG"), ("北京", "PEK"), ("上海", "SHA"),
    ("厦门", "XMN"), ("广州", "CAN"), ("深圳", "SZX"), ("成都", "CTU"),
    ("西安", "XIY"), ("重庆", "CKG"), ("杭州", "HGH"), ("南京", "NKG"),
    ("武汉", "WUH"), ("长沙", "CSX"), ("青岛", "TAO"), ("大连", "DLC"),
    ("三亚", "SYX"), ("海口", "HAK"), ("天津", "TSN"), ("郑州", "CGO"),
    ("福州", "FOC"), ("沈阳", "SHE"), ("哈尔滨", "HRB"), ("昆明", "KMG"),
    ("乌鲁木齐", "URC"), ("贵阳", "KWE"), ("兰州", "LHW"), ("南宁", "NNG"),
    ("桂林", "KWL"), ("温州", "WNZ"), ("宁波", "NGB"), ("济南", "TNA"),
]


def airline_of(code_text: str) -> tuple[str, str, str]:
    """从航班号前缀推断航司，返回 (二字代码, 航司名, 品牌色)。"""
    prefix = (code_text or "").strip().upper()[:2]
    if prefix in AIRLINES:
        name, color = AIRLINES[prefix]
        return prefix, name, color
    name, color = AIRLINE_FALLBACK
    return "", name, color


def airport_info(city: str) -> tuple[str, str]:
    """按地名匹配机场，返回 (地名关键字, 三字码)：先查常用表，再查全球机场库。"""
    s = (city or "").strip()
    # Full names and explicit IATA codes take priority over city aliases.
    for code, name in AIRPORTS_GLOBAL:
        if s == name or re.search(r'(?<![A-Z])'+code+r'(?![A-Z])', s.upper()):
            return name.removesuffix('国际机场').removesuffix('机场'), code
    if any(key in s for key in ('徐州', '观音')):
        return '徐州观音', 'XUZ'
    for key, code in AIRPORT_CODES:
        if key in s:
            return key, code
    for code, name in AIRPORTS_GLOBAL:
        if name in s or (len(s) >= 3 and s in name):
            short = name
            for suf in ("国际机场", "机场"):
                if short.endswith(suf):
                    short = short[: -len(suf)]
                    break
            return short, code
    return "", ""


def airport_matches(query: str, limit=8):
    """One search index for inline suggestions and the full airport picker."""
    from pypinyin import lazy_pinyin
    q=re.sub(r'[\s·]+', '', query or '').lower()
    if not hasattr(airport_matches, '_index'):
        airport_matches._index=[(code,name,(code+' '+name+' '+''.join(lazy_pinyin(name))+' '+
            ''.join(word[0] for word in lazy_pinyin(name))).lower()) for code,name in AIRPORTS_GLOBAL]
    return [(code,name) for code,name,search in airport_matches._index if not q or q in search.replace(' ','')][:limit]


def airport_code(city: str) -> str:
    """按地名子串匹配机场三字码，匹配不到返回空串。"""
    return airport_info(city)[1]


MONTHS_EN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
             "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _en_date(date_str: str) -> str:
    """登机牌日期格式：08JUL。"""
    raw = (date_str or "").strip()
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
        return f"{d.day:02d}{MONTHS_EN[d.month - 1]}"
    except ValueError:
        return raw


def _barcode(seed: str, height: float = 24, n: int = 40) -> ft.Row:
    """由票号生成的伪随机条形码（纯视觉）。"""
    total = (sum(ord(c) for c in (seed or "XY")) * 7) % 9973 + 17
    return ft.Row(spacing=1.6, controls=[
        ft.Container(width=1.0 + (total * (i + 3)) % 5 % 3 * 1.2,
                     height=height, bgcolor="#17233A")
        for i in range(n)
    ])


def _qr(seed: str, cell: float = 4.2, n: int = 11) -> ft.Container:
    """由票号生成的伪二维码（三个定位角 + 随机点阵）。"""
    total = (sum(ord(c) for c in (seed or "TL")) * 13) % 9973 + 31

    def cell_on(r: int, c: int) -> bool:
        corner = ((r < 3 and c < 3) or (r < 3 and c >= n - 3)
                  or (r >= n - 3 and c < 3))
        if corner:
            rr = r if r < 3 else r - n + 3
            cc = c if c < 3 else c - n + 3
            return rr in (0, 2) or cc in (0, 2)
        return (total * (r * n + c + 5)) % 7 in (0, 1, 3, 5)

    return ft.Container(
        padding=5, border_radius=6, bgcolor="#FFFFFF",
        border=ft.Border.all(1, "#17233A"),
        content=ft.Column(spacing=0, controls=[
            ft.Row(spacing=0, controls=[
                ft.Container(width=cell, height=cell,
                             bgcolor="#17233A" if cell_on(r, c) else None)
                for c in range(n)])
            for r in range(n)]))


VEHICLES = ["飞机", "高铁", "火车"]
VEHICLE_ICONS = {"飞机": ft.Icons.FLIGHT_TAKEOFF, "高铁": ft.Icons.TRAIN,
                 "火车": ft.Icons.TRAIN_OUTLINED}

# ---------------- 铁路电子客票报销凭证 ----------------
# 国铁现行版式：动车组（G / D / C 字头）走蓝票，普速列车走红票。
# 蓝票是满版青色、底部压一条深色带；红票是白纸上套一块粉色印区（带白边）。
# 下面所有色值都是从真实票面截图里取出来的。
RAIL_SKINS = {
    "高铁": {                                   # 蓝票
        "paper": "#96CBCF",                     # 满版底色
        "body": "#9CCED2",                      # 印区渐变起点
        "body2": "#ACD6DA",                     # 印区渐变终点
        "band": "#52AFB8",                      # 底部深色带
        "head": "#FFFFFF",                      # 背面顶部白条
        "wm": "#24FFFFFF",                      # 底纹（列车剪影，很淡）
        "wm2": "#1FFFFFFF",                     # 底纹（浅色块）
        "no": "#E03A2F",                        # 票号红
        "ink": "#12171A",                       # 票面文字
        "line": "#79BCC3",
        "inset": 0,                             # 无白边
        "radius": 14,
        "inner_radius": 0,
    },
    "火车": {                                   # 红票
        "paper": "#FFFFFF",                     # 白纸
        "body": "#F7C9C4",                      # 印区渐变起点
        "body2": "#F2BEB8",
        "band": "#FCE7E3",                      # 底部浅色带
        "head": "",                             # 背面没有顶部白条
        "wm": "#3DFFFFFF",
        "wm2": "#2EFFFFFF",
        "no": "#D8362B",
        "ink": "#12171A",
        "line": "#E9D6D3",
        "inset": 21,                            # 一圈白边
        "radius": 14,
        "inner_radius": 6,
    },
}
RAIL_INK = "#1F2229"                            # 票面文字：近黑
RAIL_SUB = "#3B3F47"
RAIL_CLASSES = ["商务座", "特等座", "优选一等座", "一等座", "二等座",
                "新空调软卧", "新空调硬卧", "软卧", "硬卧", "软座", "硬座",
                "无座", "二等包座"]
RAIL_DEFAULT_CLASS = {"高铁": "二等座", "火车": "硬座"}

# 背面：整版《报销凭证使用须知》，文字照国铁票面原文。
RAIL_BACK_TITLE = "报销凭证使用须知"
RAIL_BACK_RULES = [
    "购票后如需报销凭证的，应在开车前或乘车日期之日起180日以内(含当日),"
    "持购票时所使用的有效身份证件原件到车站售票窗口、自动售票机领取。",
    "退票后如需退票费报销凭证，应在办理之日起180天以内(含当日),"
    "持购票时所使用的有效身份证件原件到车站退票窗口领取。",
    "报销凭证开具后请妥善保管，丢失后将无法办理补办申领手续。",
    "已领取报销凭证的车票办理改签、退票或退款手续时，须回交报销凭证方可办理。",
    "报销凭证不能作为乘车凭证使用。",
    "未尽事宜见《国铁集团铁路旅客运输规程》等有关规定和车站公告，"
    "跨境旅客事宜见铁路跨境旅客相关运输组织规则和车站公告。",
]


def _cn_date(date_str: str) -> str:
    """2026-09-13 → 2026年09月13日；认不出来就原样返回。"""
    s = (date_str or "").strip()
    match = re.match(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", s)
    if not match:
        return s
    return (f"{match.group(1)}年{int(match.group(2)):02d}月"
            f"{int(match.group(3)):02d}日")


def _cn_time(time_str: str) -> str:
    """11:44 → 11:44；空的话返回空串。"""
    return (time_str or "").strip()[:5]


def _station_pinyin(name: str) -> str:
    """站名拼音：昆明 → Kunming、重庆北 → Chongqingbei。"""
    py = _pinyin_name(name)
    return py.capitalize() if py else ""


def _split_seat(seat: str, vehicle: str) -> tuple[str, str]:
    """拆「座位 / 舱位」为（车厢座位号, 席别）。

    例：二等座 02车08F号 → ("02车08F号", "二等座")；12车05号 → ("12车05号", 默认席别)
    """
    text = (seat or "").strip()
    cls = ""
    for name in RAIL_CLASSES:
        if name in text:
            cls = name
            text = text.replace(name, " ").strip(" 　/·、,")
            break
    if not text:
        return "", cls or RAIL_DEFAULT_CLASS.get(vehicle, "")
    if "车" not in text and not text.endswith("号") and len(text) <= 6:
        text += "号"
    return text, cls or RAIL_DEFAULT_CLASS.get(vehicle, "")


def _price_text(raw: str) -> str:
    """票价统一成票面上的 ￥145.0元 写法。"""
    s = (raw or "").strip().replace("￥", "").replace("¥", "").replace("元", "")
    s = s.strip()
    if not s:
        return ""
    try:
        return f"￥{float(s):.1f}元"
    except ValueError:
        return f"￥{s}元"


def _dash_row(width: float, color: str, dash: float = 4.5,
              gap: float = 3.5, height: float = 1.4) -> ft.Row:
    """一条虚线（用小方块拼）。"""
    n = max(1, int(width // (dash + gap)))
    return ft.Row(spacing=gap, tight=True, controls=[
        ft.Container(width=dash, height=height, bgcolor=color) for _ in range(n)])


def _dashed_box(content: ft.Control, width: float, height: float,
                color: str, radius: float = 3) -> ft.Stack:
    """虚线框：真实票面的「报销凭证 遗失不补」就是虚线边框。"""
    dash, gap, th = 4.5, 3.5, 1.3
    n_h = max(1, int(width // (dash + gap)))
    n_v = max(1, int(height // (dash + gap)))
    edges: list[ft.Control] = []
    for i in range(n_h):
        x = i * (dash + gap)
        edges.append(ft.Container(left=x, top=0, width=dash, height=th,
                                  bgcolor=color))
        edges.append(ft.Container(left=x, bottom=0, width=dash, height=th,
                                  bgcolor=color))
    for i in range(n_v):
        y = i * (dash + gap)
        edges.append(ft.Container(left=0, top=y, width=th, height=dash,
                                  bgcolor=color))
        edges.append(ft.Container(right=0, top=y, width=th, height=dash,
                                  bgcolor=color))
    return ft.Stack(width=width, height=height, controls=[
        *edges,
        ft.Container(left=0, right=0, top=0, bottom=0, alignment=ft.Alignment.CENTER,
                     content=content),
    ])



def _pretty_date(date_str: str) -> str:
    """2026-05-01 → 2026年5月1日 周五。"""
    raw = (date_str or "").strip()
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return raw
    week = "一二三四五六日"[d.weekday()]
    return f"{d.year}年{d.month}月{d.day}日 周{week}"


def _refresh_theme_values() -> None:
    """每次建页重新生成样式，避免模块级字段缓存旧主题。"""
    global FORM_FIELD, VEHICLE_COLORS, VEHICLE_SOFTS, RECORD_FIELD
    FORM_FIELD = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE)),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1.4, color=theme.MIST_BLUE)),
        },
        text_style=ft.TextStyle(size=13, color=theme.TEXT_MAIN),
        label_style=ft.TextStyle(size=11.5, color=theme.TEXT_SUB),
        hint_style=ft.TextStyle(size=12, color=theme.TEXT_FAINT),
        filled=True, fill_color=theme.CARD_BG,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=9),
    )
    VEHICLE_COLORS = {"飞机": theme.SKY_CYAN, "高铁": theme.MINT_GREEN, "火车": theme.MIST_BLUE}
    VEHICLE_SOFTS = {"飞机": theme.SKY_CYAN_SOFT, "高铁": theme.MINT_GREEN_SOFT, "火车": theme.MIST_BLUE_SOFT}
    RECORD_FIELD = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=9, side=ft.BorderSide(width=1, color=theme.LINE)),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=9, side=ft.BorderSide(width=1.3, color=theme.MIST_BLUE)),
        },
        text_style=ft.TextStyle(size=12, color=theme.TEXT_MAIN),
        label_style=ft.TextStyle(size=10.5, color=theme.TEXT_SUB),
        filled=True, fill_color=theme.CARD_BG,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=7),
    )


_refresh_theme_values()


def build(page: ft.Page) -> ft.Control:
    _refresh_theme_values()
    current: dict = {"id": None}          # 当前选中的票根
    form_image: dict = {"path": ""}       # 表单关联的截图（AI 识别或手选）
    picked_vehicle: dict = {"v": "飞机"}
    preview_state = {"draft": False, "width": 0, "height": 0}
    preview_caption = ft.Text("票面预览", size=11, color=theme.TEXT_SUB)
    rolling={'active':False,'task':None,'deadline':0,'hover':False,'form_hover':False,'focus':None,'items':[],'revision':0,'busy':False}
    floating = {'open':False, 'scroll':0, 'extent':0, 'direction':1}
    from route_atlas import RouteAtlas
    atlas = RouteAtlas(page, automatic=True, embedded=True)
    def postpone():rolling['deadline']=time.monotonic()+6
    def hover_display(e):rolling['hover']=str(e.data).lower()=='true';postpone()
    def hover_form(e):rolling['form_hover']=str(e.data).lower()=='true';postpone()
    roll_caption=ft.Text('',size=11,color=theme.TEXT_SUB)
    roll_marks=ft.Row(spacing=5,alignment=ft.MainAxisAlignment.CENTER)
    pass_hint=ft.Text('',size=10.5,color=theme.TEXT_SUB,text_align=ft.TextAlign.CENTER)

    def show_tip(msg: str) -> None:
        page.show_dialog(theme.toast(ft.Text(msg, size=12.5, color="#FFFFFF"),
                                     bgcolor=theme.MIST_BLUE_DEEP))

    # ---------------- 图片工具 ----------------
    def _save_image(src: str) -> str:
        if not src or not os.path.exists(src):
            return ""
        ext = os.path.splitext(src)[1].lower() or ".png"
        dest = os.path.join(tdb.TICKET_DIR, f"{uuid.uuid4().hex}{ext}")
        shutil.copyfile(src, dest)
        return dest

    def _remove_image(path: str) -> None:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # ---------------- 左栏：统计 + 票根列表 ----------------
    # （顶栏已去掉：底部导航会告诉你现在在哪，保存按钮在右侧「填写票根」卡片里）
    stats_text = ft.Text("", size=11, color=theme.TEXT_SUB, expand=True, max_lines=2)
    ticket_list = ft.ListView(spacing=9, expand=True, padding=ft.Padding.only(right=3))
    def list_scrolled(e):
        ft.context.disable_auto_update()
        floating['scroll']=e.pixels
        floating['extent']=e.max_scroll_extent
    ticket_list.on_scroll=list_scrolled
    category = {"value": "all"}
    category_bar = ft.Row(spacing=4)
    card_cache = {}

    def pick_category(key):
        rolling['revision']+=1;postpone()
        category["value"] = key
        refresh_tickets()

    def build_trip_card(t: dict) -> ft.Control:
        active = t["id"] == current["id"]
        main_c = VEHICLE_COLORS.get(t.get("vehicle"), theme.SKY_CYAN)
        soft_c = VEHICLE_SOFTS.get(t.get("vehicle"), theme.SKY_CYAN_SOFT)
        route = f"{t.get('from_city') or '—'} → {t.get('to_city') or '—'}"
        sub_parts = [t.get("depart_date") or "日期待补"]
        if t.get("code"):
            sub_parts.append(t["code"])
        cached=card_cache.get(t['id'])
        if cached and cached[0]==t:
            card=cached[1]
            card.bgcolor=soft_c if active else theme.CARD_BG
            card.border=ft.Border.all(1.4,main_c if active else theme.LINE)
            card.shadow=card_shadow() if active else None
            return card
        card=ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=15,
            bgcolor=soft_c if active else theme.CARD_BG,
            border=ft.Border.all(1.4, main_c if active else theme.LINE),
            shadow=card_shadow() if active else None,
            on_click=lambda e, tid=t["id"]: select_ticket(tid),
            tooltip=route,
            content=ft.Column(spacing=7, controls=[
                ft.Row(spacing=6, controls=[
                    ft.Icon(VEHICLE_ICONS.get(t.get("vehicle"), ft.Icons.FLIGHT_TAKEOFF),
                            size=15, color=main_c),
                    ft.Text(t.get("vehicle") or "飞机", size=10.5, color=main_c),
                    ft.Container(expand=True),
                    ft.Text(t.get("depart_date") or "待定", size=10, color=theme.TEXT_SUB),
                ]),
                ft.Text(route, size=12.5, weight=ft.FontWeight.W_600,
                        color=theme.TEXT_MAIN, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(t.get("code") or "未填写班次", size=10.5, color=theme.TEXT_SUB),
                make_pass(t, available_width=242),
            ]),
        )
        card_cache[t['id']]=(dict(t),card)
        return card

    route_preview=ft.Container(border_radius=12,clip_behavior=ft.ClipBehavior.HARD_EDGE)
    route_summary=ft.Text(size=10.5,color=theme.TEXT_SUB)
    route_style_box=ft.Container()

    def change_map_style(key):
        import route_style
        route_style.set_style(key)
        atlas.change_style(key)
        refresh_tickets()

    def open_routes(mode):
        import route_atlas
        postpone()
        atlas.switch(mode)
        refresh_tickets()

    def refresh_tickets(focus_saved=False) -> None:
        tickets = tdb.list_tickets()
        valid_ids={t['id'] for t in tickets}
        for key in list(card_cache):
            if key not in valid_ids:del card_cache[key]
        import ticket_routes,route_style
        route_style_box.content=route_style.selector(change_map_style,compact=True)
        route_signature=(atlas.mode,route_style.current(),tuple((t['id'],t.get('vehicle'),t.get('from_city'),t.get('to_city'),t.get('code'),t.get('depart_date')) for t in tickets))
        if route_preview.data!=route_signature or focus_saved:
            route_preview.data=route_signature
            atlas.reload(tickets)
            if focus_saved:
                route=next((r for r in atlas.routes if r['id']==current['id']),None)
                if route:atlas.fit(route['points'],update=False)
            atlas.draw()
        air,air_missing=ticket_routes.from_tickets(tickets,'air')
        rail,rail_missing=ticket_routes.from_tickets(tickets,'rail')
        route_summary.value=f'已自动生成 · 飞机 {len(air)} / 铁路 {len(rail)}'
        if air_missing or rail_missing:
            route_summary.value+=f' · {len(air_missing)+len(rail_missing)} 张待定位'
            route_summary.value+='\n未识别：'+'；'.join(f"{t.get('from_city','')} → {t.get('to_city','')}" for t in (air_missing+rail_missing)[:2])
        route_summary.tooltip='\n'.join(f"{t.get('from_city','')} → {t.get('to_city','')}：请核对机场全称/三字码或车站名称" for t in air_missing+rail_missing) or None
        rolling['items']=[t for t in tickets if t.get('vehicle')=='飞机']
        category_bar.controls = [ft.Container(
            expand=True, height=31, border_radius=9, alignment=ft.Alignment.CENTER,
            bgcolor=theme.MIST_BLUE_SOFT if category["value"] == key else theme.CARD_BG,
            border=ft.Border.all(1, theme.ACCENT if category["value"] == key else theme.LINE),
            tooltip="票根分类：" + label, on_click=lambda e, k=key: pick_category(k),
            content=ft.Text(label, size=11, color=theme.ACCENT if category["value"] == key else theme.TEXT_SUB),
        ) for key, label in (("all", "全部"), ("air", "飞机"), ("rail", "铁路"))]
        st = tdb.stats()
        stats_text.value = (f"{st['trips']} 次旅程 · {st['cities']} 座城市"
                            + (f" · 今年 {st['this_year']} 次" if st["this_year"] else ""))
        if tickets:
            ticket_list.controls = []
            for label, icon, items in (
                ("飞机", ft.Icons.FLIGHT, [t for t in tickets if t.get("vehicle") == "飞机"]),
                ("铁路 · 高铁 / 火车", ft.Icons.TRAIN, [t for t in tickets if t.get("vehicle") != "飞机"]),
            ):
                if category["value"] != "all" and (label == "飞机") != (category["value"] == "air"):
                    continue
                ticket_list.controls.append(ft.Container(
                    padding=ft.Padding.only(left=4, top=10, bottom=4),
                    content=ft.Row(spacing=6, controls=[
                        ft.Icon(icon, size=15, color=theme.TEXT_SUB),
                        ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=theme.TEXT_SUB, expand=True),
                        theme.count_pill(len(items)),
                    ])))
                ticket_list.controls.extend(build_trip_card(t) for t in items)
                if not items:
                    ticket_list.controls.append(ft.Text("暂无票根", size=11, color=theme.TEXT_FAINT))
        else:
            # 中间那张大卡已经把空状态说清楚了，左栏只留一句提示，不重复铺图标
            ticket_list.controls = [ft.Container(
                padding=ft.Padding.only(top=12, left=4),
                content=ft.Text("还没有票根，右侧填一条试试", size=11,
                                color=theme.TEXT_FAINT))]
        paint_pass()
        page.update()

    def select_ticket(ticket_id: int | None) -> None:
        if preview_state['draft'] and ticket_id != current['id']:
            from notebook_navigation import after_dialog_closed
            page.show_dialog(ft.AlertDialog(modal=True,title=ft.Text('当前票根尚未保存'),
                content=ft.Text('继续编辑，或放弃修改后查看另一张票根。'),actions=[
                    ft.TextButton('继续编辑',on_click=lambda e:page.pop_dialog()),
                    ft.TextButton('放弃修改并查看',on_click=lambda e:after_dialog_closed(page,lambda:open_ticket(ticket_id)))]))
            return
        if ticket_id == current['id'] and preview_state['draft']:
            show_ticket();return
        open_ticket(ticket_id)

    def open_ticket(ticket_id):
        rolling['revision']+=1;postpone()
        current["id"] = ticket_id
        t = tdb.get_ticket(ticket_id) if ticket_id else None
        flip_state["back"] = False
        fill_form(t)
        if t:
            atlas.switch('air' if t.get('vehicle')=='飞机' else 'rail')
            atlas.selected=ticket_id
            atlas.draw()
        show_ticket()
        refresh_tickets()

    # ---------------- 中间：仿真票根（翻转看背面广告） ----------------
    pass_area = ft.Container(
        expand=True, alignment=ft.Alignment.CENTER,
        opacity=1,offset=ft.Offset(0,0),
        animate_opacity=ft.Animation(180,ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(260,ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_scale=ft.Animation(170, ft.AnimationCurve.EASE_IN_OUT),
    )

    def make_pass(t: dict, back=False, large=False, available_width=None) -> ft.Control:
        item = dict(t)
        style = ticket_design.normalize_style(item.get("style"))
        vehicle = item.get("vehicle") or "飞机"
        natural_w, natural_h = ticket_design.dimensions(vehicle, style)
        available_w = preview_state["width"] or max(260, (page.width or 1320) - 44 - 240 - 320 - 40)
        available_h = preview_state["height"] or max(280, (page.height or 900) - 350)
        if large:
            available_w = min(1000, (page.width or 1320)-160)
            available_h = max(300, (page.height or 900)-180)
        if available_width is not None:
            available_w, available_h = available_width, 400
        scale = min(1.35 if large else 1, available_w/natural_w, available_h/natural_h)
        width = natural_w * scale
        if vehicle != "飞机":
            return ticket_design.rail_ticket(item, width, back)
        item["_from_code"] = airport_code(item.get("from_city") or "")
        item["_to_code"] = airport_code(item.get("to_city") or "")
        item["_airline"] = airline_of(item.get("code") or "")[1]
        item["_airline_color"] = airline_of(item.get("code") or "")[2]
        return ticket_design.boarding_pass(item, style, width, back)

    def make_pass_back(t: dict) -> ft.Control:
        return make_pass(t, back=True)

    def _open_image(path: str) -> None:
        try:
            os.startfile(path)   # type: ignore[attr-defined]
        except OSError:
            show_tip("图片在：" + path)

    flip_state = {"busy": False, "back": False}

    async def flip_pass(e=None) -> None:
        """翻转票根：横向压扁 → 换面 → 展开，模拟 3D 翻面。"""
        if flip_state["busy"] or not isinstance(pass_area.content, ft.GestureDetector):
            return
        flip_state["busy"] = True
        rolling['revision']+=1;postpone()
        pass_area.scale = ft.Scale(scale_x=0.03, scale_y=1.0)
        page.update()
        await asyncio.sleep(0.2)
        flip_state["back"] = not flip_state["back"]
        paint_pass()
        pass_area.scale = ft.Scale(scale_x=1.0, scale_y=1.0)
        page.update()
        await asyncio.sleep(0.2)
        flip_state["busy"] = False

    def preview_ticket() -> dict | None:
        if preview_state["draft"]:
            return dict(id=current["id"] or 0, vehicle=picked_vehicle["v"],
                from_city=from_input.value, to_city=to_input.value,
                depart_date=date_input.value, depart_time=depart_time_input.value,
                arrive_time=arrive_time_input.value, code=_dd_get(flight_dd),
                seat=seat_input.value, gate=gate_input.value, price=price_input.value,
                passenger=passenger_input.value, passenger_id=pid_input.value,
                note=note_input.value, image=form_image["path"], style=style_picker.value)
        if current["id"]:
            return tdb.get_ticket(current["id"])
        return None

    def paint_pass() -> None:
        t = preview_ticket()
        preview_caption.value = "编辑预览 · 保存后生效" if preview_state["draft"] else "票面预览"
        if t:
            pass_area.content = ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.CLICK, on_tap=flip_pass,
                content=make_pass(t, back=flip_state["back"]))
        else:
            pass_area.content = empty_state(ft.Icons.CONFIRMATION_NUMBER_OUTLINED,
                "还没有旅程票根", "在右侧填写行程，即可预览票面", theme.ACCENT)
        items=rolling['items'];index=next((i for i,v in enumerate(items) if v['id']==current['id']),-1)
        roll_bar.visible=bool(index>=0 and category['value']!='rail' and not preview_state['draft'])
        roll_caption.value=f'航程回放   {index+1:02d} / {len(items):02d}' if index>=0 else ''
        previous_roll.disabled=next_roll.disabled=len(items)<2
        pass_hint.value='轻点票面翻转正反面 · 收起后保留编辑内容'
        start=max(0,min(index-3,len(items)-7))
        roll_marks.controls=[ft.Container(width=22 if i==index else 5,height=5,border_radius=4,
            bgcolor=theme.ACCENT if i==index else theme.LINE) for i in range(start,min(len(items),start+7))]

    def draft_changed(e=None) -> None:
        rolling['revision']+=1;postpone()
        preview_state["draft"] = True
        flip_state["back"] = False
        paint_pass()
        page.update()

    def resize_preview(e) -> None:
        if abs(preview_state["width"] - e.width) < 1 and abs(preview_state["height"] - e.height) < 1:
            return
        preview_state.update(width=e.width, height=e.height)
        paint_pass()
        page.update()

    pass_area.on_size_change = resize_preview

    def enlarge(e=None) -> None:
        t = preview_ticket()
        if not t:
            return
        page.show_dialog(ft.AlertDialog(
            bgcolor=theme.CARD_BG, title=ft.Text("票面预览", color=theme.TEXT_MAIN),
            content=make_pass(t, back=flip_state["back"], large=True),
            actions=[ft.TextButton("关闭", on_click=lambda e: page.pop_dialog())]))

    def show_source(e=None) -> None:
        t = preview_ticket() or {}
        image = t.get("image")
        if image and os.path.isfile(image):
            _open_image(image)
        else:
            show_tip("这张票根尚未附上原图")

    # ---------------- 右栏：填写表单 ----------------
    def vehicle_button(name: str) -> ft.FilledButton:
        return ft.FilledButton(
            content=name, data=name, height=32, elevation=0,
            on_click=lambda e: (picked_vehicle.update({"v": e.control.data}),
                                paint_vehicle(), draft_changed()),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=9),
                                 padding=ft.Padding.symmetric(horizontal=13)),
        )

    vehicle_buttons = {name: vehicle_button(name) for name in VEHICLES}
    vehicle_row = ft.Row(spacing=7, controls=list(vehicle_buttons.values()))

    def paint_vehicle() -> None:
        for name, btn in vehicle_buttons.items():
            active = name == picked_vehicle["v"]
            main_c = VEHICLE_COLORS[name]
            btn.bgcolor = main_c if active else theme.CARD_BG
            btn.color = theme.ON_ACCENT if active else theme.TEXT_SUB
        _reload_places()
        style_picker.visible = picked_vehicle["v"] == "飞机"

    # ---------------- 出发地 / 目的地：可随便打字 + 全国车站选择器 ----------------
    # 之前用的是 editable Dropdown：字打不进去（每敲一下选项被重设），
    # 而且默认只列 80 个站、还得先拼对简拼才搜得到。现在改成
    # 普通输入框（想打什么打什么）+ 一个能搜全量 3404 个站的选择器。
    def _station_matches(query: str, limit: int = 400):
        """按站名 / 简拼 / 全拼筛选，返回 (显示名, 右侧拼音提示, 数据)。"""
        q = (query or "").strip().lower().replace(" ", "")
        pool = STATION_INDEX
        if not q:
            # 没输入时：常用大站排前面，后面接全量
            head = [r for r in pool if r[0] in _BIG_STATIONS]
            rest = [r for r in pool if r[0] not in _BIG_STATIONS]
            pool = head + rest
            hits = pool
        else:
            hits = [r for r in pool if q in r[3]]
        return hits[:limit], len(hits)

    def _open_place_picker(target: ft.TextField) -> None:
        train = picked_vehicle["v"] != "飞机"
        kind = "车站" if train else "机场"

        search = ft.TextField(
            hint_text=(f"输入{kind}名 / 拼音 / 简拼，如 杭州西 · hangzhouxi · hzx"
                       if train else "输入机场名或三字码，如 杭州萧山 · HGH"),
            text_size=13, height=44, autofocus=True,
            prefix_icon=ft.Icons.SEARCH,
            border_radius=11, filled=True, bgcolor=theme.CARD_BG,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border=ft.InputBorder.OUTLINE,
            border_color=theme.LINE,
            focused_border_color=theme.MIST_BLUE,
            on_change=lambda e: refresh(e.control.value),
            on_submit=lambda e: pick(search.value.strip()),
        )
        count_text = ft.Text("", size=11, color=theme.TEXT_FAINT)
        results = ft.ListView(spacing=3, height=372, padding=ft.Padding.only(right=4))

        def row_for(data) -> ft.Control:
            name, hint, icon = data
            return ft.Container(
                padding=ft.Padding.symmetric(horizontal=11, vertical=9),
                border_radius=10, ink=True,
                on_click=lambda e, n=name: pick(n),
                on_hover=lambda e: setattr(
                    e.control, "bgcolor",
                    theme.with_alpha(theme.ACCENT, 0.10)
                    if e.data == "true" else None) or e.control.update(),
                content=ft.Row(spacing=10, controls=[
                    ft.Icon(icon, size=15, color=theme.MIST_BLUE),
                    ft.Text(name, size=13, color=theme.TEXT_MAIN, expand=True,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(hint, size=10, color=theme.TEXT_FAINT, max_lines=1),
                ]))

        def refresh(q: str = "") -> None:
            if train:
                hits, total = _station_matches(q)
                data = [(n, py, ft.Icons.TRAIN) for n, py, _full, _k in hits]
            else:
                hit = airport_matches(q, len(AIRPORTS_GLOBAL))
                total = len(hit)
                data = [(f"{c} · {n}", c, ft.Icons.FLIGHT)
                        for c, n in hit[:400]]
            results.controls = [row_for(d) for d in data] or [
                ft.Container(
                    padding=ft.Padding.only(top=24),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(f"没找到，换个词试试；"
                                    f"也可以直接点下面的「就用我输入的」",
                                    size=12, color=theme.TEXT_FAINT))]
            count_text.value = (f"共 {total} 个{kind}" if not q else
                                f"匹配 {total} 个 · 最多列 400 个")
            page.update()

        def pick(name: str) -> None:
            if not name:
                return
            target.value = name
            place_candidates.visible=False
            page.pop_dialog()
            draft_changed()

        def use_typed(e=None) -> None:
            pick(search.value.strip())

        search.value=target.value or ''
        refresh(search.value)
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.TRAIN if train else ft.Icons.FLIGHT,
                        size=18, color=theme.ACCENT),
                ft.Text(f"选一个{kind}", size=16,
                        weight=ft.FontWeight.W_700),
            ]),
            content=ft.Column(spacing=10, tight=True, width=520, controls=[
                search, count_text, results,
            ]),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("就用我输入的", icon=ft.Icons.KEYBOARD,
                              on_click=use_typed),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

    def _make_place_field(label: str):
        """普通输入框（想打什么打什么）+ 右侧浮一个"从全国车站里选"的按钮。

        按钮没有用 TextField 的 suffix —— 那个在 Flet 1.x 里不渲染，
        改成用 Stack 把按钮叠在输入框右侧，稳定可靠。
        """
        tf = ft.TextField(
            label=label, hint_text="可直接输入",
            text_size=12.5, height=52,
            content_padding=ft.Padding.only(left=12, right=44, top=10, bottom=10),
            label_style=ft.TextStyle(size=11.5, color=theme.TEXT_SUB),
            hint_style=ft.TextStyle(size=11.5, color=theme.TEXT_FAINT),
            text_style=ft.TextStyle(size=12.5, color=theme.TEXT_MAIN),
            border={
                ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                    border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE)),
                ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                    border_radius=10, side=ft.BorderSide(width=1.4, color=theme.MIST_BLUE)),
            },
        )
        btn = ft.IconButton(
            ft.Icons.MANAGE_SEARCH, icon_size=18, icon_color=theme.MIST_BLUE,
            tooltip="从全国 3400 多个车站 / 机场里挑",
            width=34, height=34, padding=0,
            on_click=lambda e: _open_place_picker(tf))
        box = ft.Stack(height=52, controls=[
            tf,
            ft.Container(right=4, top=9, content=btn),
        ])
        return box, tf

    from_box, from_input = _make_place_field("出发地")
    to_box, to_input = _make_place_field("目的地")
    place_candidates=ft.Container(visible=False,padding=8,border_radius=10,
        bgcolor=theme.CARD_BG_SOFT,border=ft.Border.all(1,theme.LINE))

    def suggest_places(target):
        query=target.value or ''
        train=picked_vehicle['v']!='飞机'
        if train:
            rows=[(name,py,name) for name,py,_full,_keys in _station_matches(query,6)[0]]
        else:
            rows=[(name,code,f'{code} · {name}') for code,name in airport_matches(query,6)]
        def choose(value):
            target.value=value
            place_candidates.visible=False
            draft_changed()
        suggestions=[ft.Container(padding=ft.Padding.symmetric(horizontal=6,vertical=7),
            border_radius=6,ink=True,tooltip='选用：'+value,
            on_click=lambda e,v=value:choose(v),
            content=ft.Row(controls=[ft.Text(name,size=11,color=theme.TEXT_MAIN,expand=True,max_lines=2),
                ft.Text(hint,size=11,color=theme.ACCENT)])) for name,hint,value in rows]
        place_candidates.content=ft.Column(spacing=3,controls=[
            ft.Row(controls=[ft.Text(target.label+'候选',size=10,color=theme.TEXT_SUB,expand=True),
                ft.IconButton(ft.Icons.CLOSE,icon_size=13,width=22,height=22,padding=0,
                    tooltip='收起地点候选',on_click=lambda e:(setattr(place_candidates,'visible',False),page.update()))]),
            ft.ListView(controls=suggestions,height=min(180,max(45,len(rows)*42)),spacing=2) if rows else
            ft.Text('暂无匹配，可继续填写自定义地点。',size=11,color=theme.TEXT_SUB)])
        place_candidates.visible=True

    def place_typed(e):
        suggest_places(e.control)
        draft_changed()

    def place_focused(e):
        suggest_places(e.control);page.update()

    from_input.on_change=to_input.on_change=place_typed
    from_input.on_focus=to_input.on_focus=place_focused

    def _reload_places() -> None:
        """交通工具切换：提示语换一下就行，选择器打开时会自己判断。"""
        train = picked_vehicle["v"] != "飞机"
        hint = "搜索火车站，或直接输入" if train else "搜索全球机场，或直接输入"
        from_input.hint_text = hint
        to_input.hint_text = hint
        place_candidates.visible=False
        airline_dd.visible = not train
        flight_dd.label = "车次" if train else "航班"
        flight_dd.hint_text = "如 G834 / K112" if train else "如 MU5812，可自由删改"
    date_input = ft.TextField(**FORM_FIELD, label="出发日期", hint_text="点击右侧日历选择",
                              read_only=True)
    depart_time_input = ft.TextField(**FORM_FIELD, label="出发时间", hint_text="如 08:00")
    arrive_time_input = ft.TextField(**FORM_FIELD, label="到达时间", hint_text="如 10:21")

    _DD_BORDER = {
        ft.ControlState.DEFAULT: ft.OutlineInputBorder(
            border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE)),
        ft.ControlState.FOCUSED: ft.OutlineInputBorder(
            border_radius=10, side=ft.BorderSide(width=1.4, color=theme.MIST_BLUE)),
    }
    _DD_STYLE = dict(text_size=12.5,
                     label_style=ft.TextStyle(size=11.5, color=theme.TEXT_SUB),
                     hint_style=ft.TextStyle(size=11.5, color=theme.TEXT_FAINT),
                     text_style=ft.TextStyle(size=12.5, color=theme.TEXT_MAIN),
                     border=_DD_BORDER)

    flight_dd = ft.TextField(label="航班 / 车次",hint_text="如 MU5812",**FORM_FIELD)

    def _airline_selected(e) -> None:
        """Offer only the prefix in an empty field; never replace a typed flight."""
        prefix = e.control.value or ""
        if not (flight_dd.value or '').strip():
            flight_dd.value=prefix
        page.update()

    airline_dd = ft.Dropdown(
        label="航空公司", hint_text="可选；航班号可以独立填写",
        editable=True, enable_filter=True, menu_height=260,
        options=[ft.DropdownOption(key=p, text=f"{p} · {n}", leading_icon=ft.Icons.FLIGHT)
                 for p, (n, _c) in AIRLINES.items()],
        on_select=_airline_selected,
        **_DD_STYLE)

    def _set_code(code: str) -> None:
        """回填航班号：识别出航司则选中并带出推荐列表。"""
        code = (code or "").strip()
        prefix, _, _ = airline_of(code)
        if prefix:
            airline_dd.value, airline_dd.text = prefix, ""
        else:
            airline_dd.value, airline_dd.text = None, ""
        flight_dd.value = code

    seat_input = ft.TextField(**FORM_FIELD, label="座位 / 舱位",
                              hint_text="如 12A / 二等座 02车08F号")
    gate_input = ft.TextField(**FORM_FIELD, label="登机口 / 检票口", hint_text="如 45 / A12")
    price_input = ft.TextField(**FORM_FIELD, label="票价（CNY）", hint_text="如 680.00")
    passenger_input = ft.TextField(**FORM_FIELD, label="乘客", hint_text="谁出发")
    pid_input = ft.TextField(**FORM_FIELD, label="证件号",
                             hint_text="票面上只显示 5003****337 这种打码形式")
    note_input = ft.TextField(**FORM_FIELD, label="备注", hint_text="和谁同行、为了什么出发…")

    date_picker = ft.DatePicker(on_change=lambda e: (
        setattr(date_input, "value",
                calendar_date(e.control.value)),
        draft_changed()))
    image_pick = ft.FilePicker()
    shot_pick = ft.FilePicker()
    page.services.append(image_pick)
    page.services.append(shot_pick)

    image_status = ft.Text("", size=10.5, color=theme.TEXT_FAINT, expand=True)

    async def choose_image(e=None) -> None:
        files = await image_pick.pick_files(
            dialog_title="选择票面截图", file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
            allow_multiple=False)
        if not files:
            return
        form_image["path"] = _save_image(files[0].path)
        image_status.value = "已附上截图"
        draft_changed()

    def _dd_set(dd, name: str) -> None:
        """回填出发地 / 目的地。"""
        dd.value = (name or "").strip()

    def _dd_get(dd) -> str:
        """Read text inputs, retaining compatibility with optional dropdown fields."""
        v = (getattr(dd, "value", None) or "").strip()
        return v or (getattr(dd, "text", None) or "").strip()

    def fill_form(t: dict | None) -> None:
        preview_state["draft"] = False
        form_title.value='编辑当前票根' if t else '新增票根'
        save_action.content='更新当前票根' if t else '保存新票根'
        save_copy.visible=bool(t)
        style_picker.value = ticket_design.normalize_style((t or {}).get("style"))
        picked_vehicle["v"] = (t or {}).get("vehicle") or "飞机"
        paint_vehicle()
        _dd_set(from_input, (t or {}).get("from_city") or "")
        _dd_set(to_input, (t or {}).get("to_city") or "")
        date_input.value = (t or {}).get("depart_date") or ""
        depart_time_input.value = (t or {}).get("depart_time") or ""
        arrive_time_input.value = (t or {}).get("arrive_time") or ""
        _set_code((t or {}).get("code") or "")
        seat_input.value = (t or {}).get("seat") or ""
        gate_input.value = (t or {}).get("gate") or ""
        price_input.value = (t or {}).get("price") or ""
        passenger_input.value = (t or {}).get("passenger") or ""
        pid_input.value = (t or {}).get("passenger_id") or ""
        note_input.value = (t or {}).get("note") or ""
        place_candidates.visible=False
        form_image["path"] = (t or {}).get("image") or ""
        image_status.value = "已附上截图" if form_image["path"] else ""
        page.update()

    def clear_form() -> None:
        current["id"] = None
        form_image["path"] = ""
        flip_state["back"] = False
        fill_form(None)
        draft_changed()

    def new_ticket(vehicle='飞机'):
        def begin(e=None):
            clear_form()
            picked_vehicle['v']=vehicle
            paint_vehicle()
            category['value']='air' if vehicle=='飞机' else 'rail'
            show_ticket(edit=True)
            refresh_tickets()
        has_content=any((field.value or '').strip() for field in
                (from_input,to_input,flight_dd,price_input,passenger_input,note_input,date_input,
                 depart_time_input,arrive_time_input,seat_input,gate_input,pid_input))
        if preview_state['draft'] and (has_content or form_image['path'] or style_picker.value!='classic'):
            page.show_dialog(ft.AlertDialog(modal=True,bgcolor=theme.CARD_BG,
                title=ft.Text('当前内容尚未保存',color=theme.TEXT_MAIN),
                content=ft.Text('新建会清空当前表单。已保存的票根不会被覆盖。',color=theme.TEXT_SUB),
                actions=[ft.TextButton('继续填写',on_click=lambda e:page.pop_dialog()),
                    ft.TextButton('放弃修改并新建',on_click=lambda e:(page.pop_dialog(),begin()))]))
        else:begin()

    def save_ticket(e=None, as_new=False) -> None:
        from_city = _dd_get(from_input)
        to_city = _dd_get(to_input)
        if not from_city or not to_city:
            show_tip("出发地和目的地都要填哦")
            return
        try:
            price=amount_text(price_input.value)
        except ValueError as error:
            show_tip(str(error));return
        fields = dict(
            vehicle=picked_vehicle["v"], from_city=from_city, to_city=to_city,
            depart_date=(date_input.value or "").strip(),
            depart_time=(depart_time_input.value or "").strip(),
            arrive_time=(arrive_time_input.value or "").strip(),
            code=_dd_get(flight_dd).upper(),
            seat=(seat_input.value or "").strip(),
            gate=(gate_input.value or "").strip(),
            price=price,
            passenger=(passenger_input.value or "").strip(),
            passenger_id=(pid_input.value or "").strip(),
            note=(note_input.value or "").strip(),
            image=form_image["path"], style=style_picker.value,
        )
        if current["id"] and not as_new:
            old = tdb.get_ticket(current["id"]) or {}
            if old.get("image") and old["image"] != fields["image"]:
                _remove_image(old["image"])
            tdb.update_ticket(current["id"], **fields)
            show_tip("票根已更新")
        else:
            if as_new and fields['image']:
                fields['image']=_save_image(fields['image'])
            current["id"] = tdb.add_ticket(**fields)
            show_tip("已收藏一张票根")
        fill_form(tdb.get_ticket(current["id"]))
        atlas.mode='air' if picked_vehicle['v']=='飞机' else 'rail'
        atlas.selected=current['id']
        refresh_tickets(focus_saved=True)
        saved_route=next((r for r in atlas.routes if r['id']==current['id']),None)
        if not saved_route:
            show_tip('票根已保存，但地点尚未识别。请使用机场完整名称/三字码，或准确车站名称。')

    def remove_ticket(e=None) -> None:
        if not current["id"]:
            show_tip("先在左侧选中一张要删除的票根")
            return
        row = tdb.delete_ticket(current["id"])
        if row:
            _remove_image(row.get("image") or "")
        show_tip("票根已删除")
        clear_form()
        preview_state['draft']=False
        close_ticket()
        refresh_tickets()

    # ---------------- 右栏：AI 识别 ----------------
    ai_status = ft.Text("", size=11, color=theme.MIST_BLUE_DEEP, expand=True)

    async def recognize_shot(e=None) -> None:
        cfg = ai_ocr.load_config()
        if not cfg.get("api_key"):
            ai_status.value = "还没有配置 AI，先在下方「AI 识别设置」填写密钥"
            ai_status.color = theme.DANGER
            page.update()
            return
        files = await shot_pick.pick_files(
            dialog_title="选择机票 / 火车票截图",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
            allow_multiple=False)
        if not files:
            return
        path = files[0].path
        ai_status.value = "AI 识别中，请稍候…"
        ai_status.color = theme.MIST_BLUE_DEEP
        page.update()
        try:
            info = await asyncio.to_thread(ai_ocr.recognize_ticket, path, cfg)
        except Exception as exc:
            ai_status.value = f"识别失败：{exc}"
            ai_status.color = theme.DANGER
            page.update()
            return
        clear_form()
        picked_vehicle["v"] = info.get("vehicle") or "飞机"
        paint_vehicle()
        _dd_set(from_input, info.get("from_city") or "")
        _dd_set(to_input, info.get("to_city") or "")
        date_input.value = info.get("depart_date") or ""
        depart_time_input.value = info.get("depart_time") or ""
        arrive_time_input.value = info.get("arrive_time") or ""
        _set_code(info.get("code") or "")
        seat_input.value = info.get("seat") or ""
        gate_input.value = info.get("gate") or ""
        price_input.value = info.get("price") or ""
        passenger_input.value = info.get("passenger") or ""
        pid_input.value = info.get("passenger_id") or ""
        note_input.value = info.get("note") or ""
        form_image["path"] = _save_image(path)
        image_status.value = "已附上识别的截图"
        ai_status.value = "识别完成！核对无误后点「保存新票根」"
        ai_status.color = theme.MINT_GREEN
        draft_changed()

    # AI 配置
    cfg = ai_ocr.load_config()
    base_url_input = ft.TextField(**RECORD_FIELD, label="接口地址 Base URL",
                                  value=cfg["base_url"], height=40)
    key_input = ft.TextField(**RECORD_FIELD, label="API Key", value=cfg["api_key"],
                             password=True, can_reveal_password=True, height=40)
    model_input = ft.TextField(**RECORD_FIELD, label="模型名", value=cfg["model"], height=40)

    def save_ai_config(e=None) -> None:
        ai_ocr.save_config({
            "base_url": base_url_input.value or "",
            "api_key": key_input.value or "",
            "model": model_input.value or "",
        })
        show_tip("AI 配置已保存（保存在本机 data 目录）")

    style_picker = ft.Dropdown(
        label="飞机票面样式", value="classic", text_size=12, width=260,
        options=[ft.DropdownOption(key=k, text=v) for k, v in ticket_design.AIR_STYLES.items()],
        on_select=draft_changed, fill_color=theme.CARD_BG, filled=True,
        border_color=theme.LINE, color=theme.TEXT_MAIN,
        label_style=ft.TextStyle(color=theme.TEXT_SUB, size=11),
    )
    for field in (date_input, depart_time_input, arrive_time_input,
                  seat_input, gate_input, price_input, passenger_input, pid_input, note_input):
        field.on_change = draft_changed
    # 保留原航司推荐逻辑，同时让票面跟随选中项更新。
    old_airline_select = airline_dd.on_select
    def airline_changed(e):
        if old_airline_select:
            old_airline_select(e)
        draft_changed()
    airline_dd.on_select = airline_changed
    def code_typed(e):
        # The TextField owns its value and cursor. Do not rewrite either on keystrokes.
        prefix,_,_=airline_of(e.control.value)
        airline_dd.value=prefix or None
        airline_dd.text=''
        draft_changed()
    flight_dd.on_change = code_typed

    form_title=ft.Text('新增票根',size=14,weight=ft.FontWeight.W_700,color=theme.TEXT_MAIN,expand=True)
    save_action=ft.FilledButton('保存新票根',icon=ft.Icons.SAVE_OUTLINED,expand=True,
        bgcolor=theme.ACCENT,color=theme.ON_ACCENT,height=38,elevation=0,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),on_click=save_ticket)
    save_copy=ft.TextButton('另存为新票根',icon=ft.Icons.ADD,visible=False,
        on_click=lambda e:save_ticket(as_new=True))

    form_card = ft.Container(
        padding=16, border_radius=18, bgcolor=theme.CARD_BG,
        border=ft.Border.all(1, theme.LINE), shadow=card_shadow(),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                icon_badge(ft.Icons.EDIT_OUTLINED, 30, theme.MIST_BLUE_SOFT, theme.MIST_BLUE_DEEP, 16),
                form_title,
                ft.TextButton("新增", icon=ft.Icons.ADD, height=30,
                              on_click=lambda e:new_ticket(picked_vehicle['v'])),
            ]),
            vehicle_row,
            style_picker,
            ft.Row(spacing=8, controls=[ft.Container(expand=True, content=from_box),
                                        ft.Icon(ft.Icons.ARROW_FORWARD, size=15, color=theme.TEXT_FAINT),
                                        ft.Container(expand=True, content=to_box)]),
            place_candidates,
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=date_input),
                ft.IconButton(ft.Icons.EVENT, icon_size=17, icon_color=theme.MIST_BLUE_DEEP,
                              tooltip="选择日期", width=34, height=34, padding=0,
                              on_click=lambda e: open_calendar(page, date_picker, date_input.value)),
            ]),
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=depart_time_input),
                ft.Container(expand=True, content=arrive_time_input),
            ]),
            airline_dd,
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=flight_dd),
                ft.Container(expand=True, content=seat_input),
            ]),
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=gate_input),
                ft.Container(expand=True, content=price_input),
            ]),
            passenger_input,
            pid_input,
            note_input,
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.TextButton("附一张截图", icon=ft.Icons.IMAGE_OUTLINED, height=32,
                              on_click=choose_image),
                image_status,
            ]),
            ft.Row(spacing=8, controls=[
                save_action,
                ft.TextButton("删除", icon=ft.Icons.DELETE_OUTLINE, height=38,
                              style=ft.ButtonStyle(color=theme.DANGER),
                              on_click=remove_ticket),
            ]),
            save_copy,
        ]),
    )

    ai_card = ft.Container(
        padding=16, border_radius=18, bgcolor=theme.CARD_BG,
        border=ft.Border.all(1, theme.LINE), shadow=card_shadow(),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                icon_badge(ft.Icons.AUTO_AWESOME, 30, theme.SKY_CYAN_SOFT, theme.MIST_BLUE_DEEP, 16),
                ft.Column(spacing=1, expand=True, controls=[
                    ft.Text("截图 AI 识别", size=14, weight=ft.FontWeight.W_700,
                            color=theme.TEXT_MAIN),
                    ft.Text("12306 / 航旅纵横 / 航司截图都能认", size=10.5,
                            color=theme.TEXT_SUB),
                ]),
            ]),
            ft.Container(
                padding=11, border_radius=11, bgcolor=theme.SKY_CYAN_SOFT,
                content=ft.Text("选一张票面截图，AI 自动读出出发地、目的地、日期、车次 / 航班号、座位，填好后核对保存即可。",
                                size=10.5, color=theme.TEXT_MAIN),
            ),
            ft.FilledButton(
                "选择截图并识别", icon=ft.Icons.QR_CODE_SCANNER, expand=True,
                bgcolor=theme.SKY_CYAN, color="#FFFFFF", height=38, elevation=0,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),
                on_click=recognize_shot,
            ),
            ai_status,
        ]),
    )

    ai_config_card = ft.Container(
        padding=16, border_radius=18, bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.all(1, theme.LINE_SOFT),
        content=ft.Column(spacing=9, controls=[
            ft.Row(spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=15, color=theme.TEXT_SUB),
                ft.Text("AI 识别设置", size=12.5, weight=ft.FontWeight.W_700,
                        color=theme.TEXT_SUB, expand=True),
            ]),
            base_url_input,
            key_input,
            model_input,
            ft.FilledButton(
                "保存配置", icon=ft.Icons.KEY_OUTLINED, height=34, elevation=0,
                bgcolor=theme.MIST_BLUE_DEEP, color="#FFFFFF",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=save_ai_config),
            ft.Text("默认智谱 glm-4v-flash（免费）；任何 OpenAI 兼容视觉接口均可，改地址和模型名即可。密钥只保存在本机。",
                    size=9.5, color=theme.TEXT_FAINT),
        ]),
    )

    left_panel = ft.Container(
        width=286,
        on_hover=hover_display,
        padding=ft.Padding.symmetric(horizontal=14, vertical=16),
        content=ft.Column(spacing=11, controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=13, vertical=11),
                border_radius=14, gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[theme.MIST_BLUE_SOFT, theme.SKY_CYAN_SOFT]),
                content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.Icons.TRAVEL_EXPLORE, size=18, color=theme.MIST_BLUE_DEEP),
                    stats_text,
                ]),
            ),
            category_bar,
            ft.Row(spacing=8,controls=[
                ft.FilledButton('新增机票',icon=ft.Icons.FLIGHT_TAKEOFF,expand=True,height=44,
                    on_click=lambda e:new_ticket('飞机'),bgcolor=theme.ACCENT,color=theme.ON_ACCENT,
                    style=ft.ButtonStyle(padding=8,text_style=ft.TextStyle(size=11.5),shape=ft.RoundedRectangleBorder(radius=12))),
                ft.FilledButton('新增铁路票根',icon=ft.Icons.TRAIN,expand=True,height=44,
                    on_click=lambda e:new_ticket('高铁'),bgcolor=theme.ACCENT,color=theme.ON_ACCENT,
                    style=ft.ButtonStyle(padding=8,text_style=ft.TextStyle(size=11.5),shape=ft.RoundedRectangleBorder(radius=12)))]),
            ticket_list,
        ]),
    )

    async def roll_ticket(delta=1,automatic=False):
        items=rolling['items']
        if len(items)<2 or rolling['busy'] or preview_state['draft'] or flip_state['busy']:return
        rolling['busy']=True;rolling['revision']+=1;revision=rolling['revision']
        index=next((i for i,t in enumerate(items) if t['id']==current['id']),0)
        target=items[(index+delta)%len(items)]['id']
        animate=motion_enabled()
        try:
            if animate:
                pass_area.opacity=0;pass_area.offset=ft.Offset(-.10*delta,0);pass_area.update()
                await asyncio.sleep(.19)
            if revision!=rolling['revision'] or preview_state['draft']:return
            if automatic and (not rolling['active'] or rolling['hover'] or rolling['form_hover']
                or rolling['focus'] is not None or any(isinstance(d,ft.AlertDialog) and d.open for d in page._dialogs.controls)):return
            select_ticket(target)
            if animate:
                pass_area.offset=ft.Offset(.10*delta,0);pass_area.update();await asyncio.sleep(.025)
        finally:
            pass_area.opacity=1;pass_area.offset=ft.Offset(0,0)
            if rolling['active']:pass_area.update()
            rolling['busy']=False;postpone()

    async def previous_pass(e):await roll_ticket(-1)
    async def next_pass(e):await roll_ticket(1)
    async def auto_roll():
        while rolling['active']:
            await asyncio.sleep(.2)
            blocked=(floating['open'] or len(ticket_list.controls)<3
                or preview_state['draft'] or rolling['hover'] or rolling['form_hover'] or rolling['focus'] is not None
                or len(page.views)>1 or flip_state['busy'] or rolling['busy'] or page.window.minimized or page.window.focused is False
                or not motion_enabled() or any(isinstance(d,ft.AlertDialog) and d.open for d in page._dialogs.controls))
            if blocked:postpone();continue
            if time.monotonic()>=rolling['deadline']:
                extent=floating['extent']
                target=floating['scroll']+180*floating['direction']
                if extent>0:
                    if target>=extent:target=extent;floating['direction']=-1
                    elif target<=0:target=0;floating['direction']=1
                    await ticket_list.scroll_to(offset=target,duration=1400)
                else:
                    await ticket_list.scroll_to(delta=140,duration=1400)
                postpone()
    def show_page():
        atlas.alive=True
        if rolling['active']:return
        rolling['active']=True;postpone();rolling['task']=page.run_task(auto_roll)
    def leave_page():
        atlas.alive=False
        rolling['active']=False;rolling['revision']+=1
        if rolling['task']:rolling['task'].cancel();rolling['task']=None

    previous_roll=ft.IconButton(ft.Icons.CHEVRON_LEFT,tooltip='上一张机票',icon_color=theme.TEXT_SUB,on_click=previous_pass)
    next_roll=ft.IconButton(ft.Icons.CHEVRON_RIGHT,tooltip='下一张机票',icon_color=theme.TEXT_SUB,on_click=next_pass)
    roll_bar=ft.Column(spacing=9,horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[
        ft.Row(alignment=ft.MainAxisAlignment.CENTER,spacing=12,controls=[
            previous_roll,roll_caption,next_roll]),roll_marks])

    center_area = ft.Container(
        expand=True, padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        on_hover=hover_display,clip_behavior=ft.ClipBehavior.HARD_EDGE,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,end=ft.Alignment.BOTTOM_CENTER,
            colors=[theme.CARD_BG,theme.SKY_CYAN_SOFT]),
        content=ft.Column(spacing=10, expand=True, controls=[
            ft.Row(controls=[preview_caption, ft.Container(expand=True),
                ft.IconButton(ft.Icons.OPEN_IN_FULL, tooltip="放大票面", icon_size=18,
                              icon_color=theme.TEXT_SUB, on_click=enlarge),
                ft.IconButton(ft.Icons.IMAGE_OUTLINED, tooltip="查看原图", icon_size=18,
                              icon_color=theme.TEXT_SUB, on_click=show_source),
            ]),
            pass_area,
            roll_bar,
            pass_hint,
        ]))

    right_panel = ft.Container(
        width=320, visible=False,
        on_hover=hover_form,
        bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.only(left=ft.BorderSide(1, theme.LINE)),
        content=ft.ListView(spacing=12, padding=ft.Padding.all(14),
                            controls=[form_card, ai_card, ai_config_card]),
    )

    def close_ticket(e=None):
        floating['open']=False
        ticket_overlay.visible=False
        rolling['focus']=None
        rolling['hover']=rolling['form_hover']=False
        postpone()
        page.update()

    def show_ticket(edit=False):
        floating['open']=True
        ticket_overlay.visible=True
        right_panel.visible=edit or preview_state['draft']
        pass_hint.value='轻点票面翻转正反面 · 收起后保留编辑内容'
        postpone()

    def edit_ticket(e=None):
        right_panel.visible=not right_panel.visible
        page.update()

    center_area.border_radius=18
    center_area.border=ft.Border.all(1,theme.LINE)
    center_area.shadow=card_shadow()
    center_area.content.controls[0].controls.extend([
        ft.IconButton(ft.Icons.EDIT_OUTLINED,tooltip='编辑这张票根',on_click=edit_ticket),
        ft.IconButton(ft.Icons.CLOSE,tooltip='收起票根',on_click=close_ticket)])
    # The map stays mounted behind the ticket; closing preserves its viewport.
    ticket_overlay=ft.Container(left=26,right=26,top=62,bottom=28,visible=False,
        content=ft.Row(spacing=12,controls=[center_area,right_panel]))
    def resize_map(e):
        size=(max(260,int(e.width)),max(220,int(e.height)))
        if atlas.embedded_size==size:return
        atlas.embedded_size=size
        atlas.resize()
    atlas.map_frame.on_size_change=resize_map
    map_area=ft.Container(expand=True,padding=ft.Padding.only(top=14,right=14,bottom=14),
        content=ft.Column(spacing=8,controls=[
            ft.Row(controls=[ft.Text('票根里的足迹',size=17,weight=ft.FontWeight.W_600,color=theme.TEXT_MAIN),
                ft.Container(expand=True),
                ft.TextButton('飞机地图',icon=ft.Icons.FLIGHT,on_click=lambda e:open_routes('air')),
                ft.TextButton('高铁地图',icon=ft.Icons.TRAIN,on_click=lambda e:open_routes('rail'))]),
            ft.Row(controls=[route_style_box,ft.Container(expand=True),
                ft.TextButton('中国',on_click=lambda e:atlas.home()),
                ft.TextButton('世界',on_click=lambda e:atlas.world()),
                ft.IconButton(ft.Icons.REMOVE,tooltip='缩小轨迹地图',on_click=lambda e:atlas.zoom(-1)),
                ft.IconButton(ft.Icons.ADD,tooltip='放大轨迹地图',on_click=lambda e:atlas.zoom(1))]),
            ft.Stack(expand=True,controls=[
                ft.Container(left=0,right=0,top=0,bottom=0,content=atlas.map_frame),ticket_overlay]),
            route_summary,
            ft.Text('轨迹自动来自票根 · 双指移动 / 捏合缩放 · 示意连线，非实际航路或铁路线',size=10,color=theme.TEXT_SUB)]))

    # Keep keyboard-focused forms stationary, including before the first edit.
    for field in (from_input,to_input,date_input,depart_time_input,arrive_time_input,flight_dd,
                  seat_input,gate_input,price_input,passenger_input,pid_input,note_input,style_picker,airline_dd):
        if not hasattr(field,'on_focus'):continue
        old_focus=field.on_focus;old_blur=field.on_blur
        def focused(e,control=field,previous=old_focus):
            rolling['focus']=id(control);rolling['revision']+=1;postpone()
            if previous:previous(e)
        def blurred(e,control=field,previous=old_blur):
            if rolling['focus']==id(control):rolling['focus']=None
            postpone()
            if previous:previous(e)
        field.on_focus=focused;field.on_blur=blurred

    # 初始化
    paint_vehicle()
    initial=next((t for t in tdb.list_tickets() if t.get('vehicle')=='飞机'),None)
    current['id']=initial['id'] if initial else None
    fill_form(initial)
    refresh_tickets()

    return ft.Row(spacing=0, expand=True,
                  data={'on_show':show_page,'on_hide':leave_page,'ticket_rolling':rolling,
                        'ticket_current':current,'ticket_preview':preview_state,'ticket_flip':flip_state,
                        'ticket_atlas':atlas,'ticket_floating':floating},
                  controls=[left_panel, map_area])

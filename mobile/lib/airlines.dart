/// 国内主要航空公司的宣传语。
///
/// 用户在票根里填写「航空公司」后，背面会自动换成对应航司的标语；
/// 没填或认不出来时，保留原来的通用句子。
const airlineSlogans = <String, String>{
  // 三大航 + 主要航司（官方/公开宣传语）
  '中国国际航空': '宾四海，礼天下',
  '中国东方航空': '世界品味，东方魅力',
  '中国南方航空': '安全第一，顾客至上',
  '海南航空': '相伴相惜，梦享飞行',
  '四川航空': '美丽川航，卓越时尚',
  '厦门航空': '人生路漫漫，白鹭常相伴',
  '深圳航空': '任何时候，自然体贴',
  '山东航空': '厚道山航，品质飞翔',
  '吉祥航空': '吉祥航空，如意到家',
  '春秋航空': '想飞就飞',
  '中国联合航空': '在云端、蕴天涯、享此时',
  '上海航空': '乘上航，到家了',
  // 其他地方航司（常用宣传语）
  '天津航空': '从心出发，天航相伴',
  '首都航空': '京彩相伴，首都航空',
  '祥鹏航空': '祥鹏航空，精彩随行',
  '西部航空': '西部航空，梦想起航',
  '成都航空': '成都航空，成人之美',
  '重庆航空': '重庆航空，山水相伴',
  '河北航空': '河北航空，飞向美好',
  '西藏航空': '西藏航空，雪域天路',
  '乌鲁木齐航空': '乌鲁木齐航空，丝路相伴',
  '福州航空': '福州航空，有福相伴',
  '北部湾航空': '北部湾航空，海丝相伴',
  '九元航空': '九元航空，让飞行更简单',
  '奥凯航空': '奥凯航空，奥妙之旅',
  '东海航空': '东海航空，东海相伴',
  '长龙航空': '长龙航空，龙行天下',
  '青岛航空': '青岛航空，青航相伴',
  '多彩贵州航空': '多彩贵州，多彩飞翔',
  '江西航空': '江西航空，赣鄱相伴',
  '桂林航空': '桂林航空，山水桂林',
  '金鹏航空': '金鹏航空，鹏程万里',
  '湖南航空': '湖南航空，湘伴而行',
  '华夏航空': '华夏航空，通程华夏',
  '幸福航空': '幸福航空，幸福旅程',
  '瑞丽航空': '瑞丽航空，瑞意相伴',
  '龙江航空': '龙江航空，龙行天下',
  '天骄航空': '天骄航空，草原天骄',
  '昆明航空': '昆明航空，春城相伴',
  '大连航空': '大连航空，浪漫同行',
};

/// 简称 / 两字码 → 全称，方便用户直接输「厦航」「MF」也能认出来。
const airlineAliases = <String, String>{
  '国航': '中国国际航空', 'CA': '中国国际航空',
  '东航': '中国东方航空', 'MU': '中国东方航空',
  '南航': '中国南方航空', 'CZ': '中国南方航空',
  '海航': '海南航空', 'HU': '海南航空',
  '川航': '四川航空', '3U': '四川航空',
  '厦航': '厦门航空', 'MF': '厦门航空',
  '深航': '深圳航空', 'ZH': '深圳航空',
  '山航': '山东航空', 'SC': '山东航空',
  '吉祥': '吉祥航空', 'HO': '吉祥航空',
  '春秋': '春秋航空', '9C': '春秋航空',
  '联航': '中国联合航空', 'KN': '中国联合航空',
  '上航': '上海航空', 'FM': '上海航空',
  '天航': '天津航空', 'GS': '天津航空',
  '首航': '首都航空', 'JD': '首都航空',
  '祥鹏': '祥鹏航空', '8L': '祥鹏航空',
  '西部': '西部航空', 'PN': '西部航空',
  '成都航': '成都航空', 'EU': '成都航空',
  '重庆航': '重庆航空', 'OQ': '重庆航空',
  '河北航': '河北航空', 'NS': '河北航空',
  '西藏航': '西藏航空', 'TV': '西藏航空',
  '乌鲁木齐': '乌鲁木齐航空', 'UQ': '乌鲁木齐航空',
  '福州航': '福州航空', 'FU': '福州航空',
  '北部湾': '北部湾航空', 'GX': '北部湾航空',
  '九元': '九元航空', 'AQ': '九元航空',
  '奥凯': '奥凯航空', 'BK': '奥凯航空',
  '东海': '东海航空', 'DZ': '东海航空',
  '长龙': '长龙航空', 'GJ': '长龙航空',
  '青岛航': '青岛航空', 'QW': '青岛航空',
  '多彩贵州': '多彩贵州航空', 'GY': '多彩贵州航空',
  '江西航': '江西航空', 'RY': '江西航空',
  '桂林航': '桂林航空', 'GT': '桂林航空',
  '金鹏': '金鹏航空', 'Y8': '金鹏航空',
  '湖南航': '湖南航空', 'A6': '湖南航空',
  '华夏': '华夏航空', 'G5': '华夏航空',
  '幸福': '幸福航空', 'JR': '幸福航空',
  '瑞丽': '瑞丽航空', 'DR': '瑞丽航空',
  '龙江': '龙江航空', 'LT': '龙江航空',
  '天骄': '天骄航空', '9D': '天骄航空',
  '昆明航': '昆明航空', 'KY': '昆明航空',
  '大连航': '大连航空',
};

/// 根据用户输入返回宣传语；认不出来返回 null。
String? airlineSlogan(String input) {
  final q = input.trim();
  if (q.isEmpty) return null;
  final direct = airlineSlogans[q];
  if (direct != null) return direct;
  final alias = airlineAliases[q] ?? airlineAliases[q.toUpperCase()];
  if (alias != null) return airlineSlogans[alias];
  for (final entry in airlineSlogans.entries) {
    if (q.contains(entry.key) || entry.key.contains(q)) return entry.value;
  }
  for (final entry in airlineAliases.entries) {
    if (q.contains(entry.key)) {
      final value = airlineSlogans[entry.value];
      if (value != null) return value;
    }
  }
  return null;
}

/// 输入联想：按全称、简称、两字码匹配。
List<String> airlineCandidates(String query, {int limit = 8}) {
  final q = query.trim().toLowerCase();
  if (q.isEmpty) return airlineSlogans.keys.take(limit).toList();
  final out = <String>[];
  for (final name in airlineSlogans.keys) {
    if (out.length >= limit) break;
    if (name.toLowerCase().contains(q)) out.add(name);
  }
  if (out.length < limit) {
    for (final entry in airlineAliases.entries) {
      if (out.length >= limit) break;
      if (entry.key.toLowerCase().contains(q) && !out.contains(entry.value)) {
        out.add(entry.value);
      }
    }
  }
  return out;
}

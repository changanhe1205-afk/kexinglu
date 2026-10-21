import 'i18n.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';
import 'look.dart';
import 'store.dart';

class WeatherPlace {
  final double lat, lon;
  final String name;
  const WeatherPlace(this.lat, this.lon, this.name);
}

class _LocalPlace {
  final String name;
  final double lon, lat;
  const _LocalPlace(this.name, this.lon, this.lat);
}

/// Weather uses public forecasts, with offline city lookup preserved.
/// 城市定位/搜索用随包内置的全国地名库 `assets/map/places.json`（离线、即时、
/// 国内地点优先离线检索，国外城市回退在线地理编码。
class WeatherService {
  Map<String, List<double>> _places = {};
  List<_LocalPlace> _reversePlaces = [];
  Future<void>? _loading;

  static const _suffixes = [
    '特别行政区', '维吾尔自治区', '壮族自治区', '回族自治区', '自治区',
    '自治州', '地区', '林区', '矿区', '特区', '县', '市', '区', '旗', '盟', '省',
  ];

  Future<void> _ensureLoaded() {
    return _loading ??= _load();
  }

  Future<void> _load() async {
    try {
      final raw = await rootBundle.loadString('assets/map/places.json');
      final map = Map<String, dynamic>.from(jsonDecode(raw));
      final places = <String, List<double>>{};
      for (final e in map.entries) {
        final v = e.value;
        if (v is! List || v.length < 2 || v[0] is! num || v[1] is! num) continue;
        places[e.key] = [(v[0] as num).toDouble(), (v[1] as num).toDouble()];
      }
      _places = places;
      final cityLike = RegExp(r'(市|地区|自治州|盟|旗|区|县|林区|矿区|特区)$');
      _reversePlaces = [
        for (final e in places.entries)
          if (cityLike.hasMatch(e.key))
            _LocalPlace(e.key, e.value[0], e.value[1]),
      ];
      // 全国区县地名（坐标沿用所属地级市），补全省/市/区县三级搜索。
      try {
        final extraRaw = await rootBundle.loadString('assets/map/cities_cn.json');
        final extra = Map<String, dynamic>.from(jsonDecode(extraRaw));
        for (final e in extra.entries) {
          if (_places.containsKey(e.key)) continue;
          final v = e.value;
          if (v is! List || v.length < 2 || v[0] is! num || v[1] is! num) continue;
          _places[e.key] = [(v[0] as num).toDouble(), (v[1] as num).toDouble()];
        }
      } catch (_) {}
    } catch (_) {
      _places = {};
      _reversePlaces = [];
    }
  }

  static String _strip(String s) {
    var r = s;
    var changed = true;
    while (changed) {
      changed = false;
      for (final suffix in _suffixes) {
        if (r.length > suffix.length && r.endsWith(suffix)) {
          r = r.substring(0, r.length - suffix.length);
          changed = true;
          break;
        }
      }
    }
    return r;
  }

  Future<Map<String, dynamic>> get(Uri url, {Map<String, String>? headers}) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 10);
    try {
      final req = await client.getUrl(url).timeout(const Duration(seconds: 10));
      headers?.forEach((k, v) => req.headers.set(k, v));
      final response = await req.close().timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) throw const FormatException('天气服务暂时不可用');
      return Map<String, dynamic>.from(jsonDecode(await response.transform(utf8.decoder).join().timeout(const Duration(seconds: 10))));
    } finally { client.close(force: true); }
  }

  /// Public weather API: no signing secrets in distributed clients.
  Future<Map<String, dynamic>> current(WeatherPlace place) async {
    final result = await get(Uri.https('api.open-meteo.com', '/v1/forecast', {
      'latitude': place.lat.toStringAsFixed(3), 'longitude': place.lon.toStringAsFixed(3),
      'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m',
      'wind_speed_unit': 'ms', 'timezone': 'auto',
    }));
    final value = result['current'];
    if (value is! Map || value['temperature_2m'] is! num) throw const FormatException('天气数据暂不可用');
    final code = value['weather_code'] as num? ?? -1;
    final (icon, label) = switch (code.toInt()) {
      0 => ('100', '晴'), 1 || 2 => ('101', '多云'), 3 => ('104', '阴'),
      45 || 48 => ('501', '雾'), 51 || 53 || 55 || 56 || 57 => ('300', '毛毛雨'),
      61 || 63 || 65 || 66 || 67 || 80 || 81 || 82 => ('305', '雨'),
      71 || 73 || 75 || 77 || 85 || 86 => ('400', '雪'),
      95 || 96 || 99 => ('302', '雷雨'), _ => ('999', '天气更新中'),
    };
    return {'temperature': {'value': value['temperature_2m']},
      'feelsLike': {'value': value['apparent_temperature']}, 'humidity': value['relative_humidity_2m'],
      'wind': {'speed': {'value': value['wind_speed_10m']}},
      'condition': {'code': icon, 'text': tr(label)}, 'source': 'Open-Meteo'};
  }

  List<WeatherPlace> _localSearch(String query) {
    final q = query.trim();
    if (q.isEmpty) return [];
    final ql = q.toLowerCase();
    final qs = _strip(ql);
    final scored = <(String, int)>[];
    for (final name in _places.keys) {
      final nl = name.toLowerCase();
      final ns = _strip(nl);
      int rank;
      if (nl == ql) {
        rank = 0;
      } else if (ns == qs) {
        rank = 1;
      } else if (nl.startsWith(ql)) {
        rank = 2;
      } else if (nl.contains(ql)) {
        rank = 3;
      } else {
        continue;
      }
      scored.add((name, rank));
    }
    scored.sort((a, b) {
      final c = a.$2.compareTo(b.$2);
      if (c != 0) return c;
      return a.$1.length.compareTo(b.$1.length);
    });
    return [
      for (final s in scored.take(10))
        WeatherPlace(_places[s.$1]![1], _places[s.$1]![0], s.$1),
    ];
  }

  Future<List<WeatherPlace>> search(String name) async {
    if (name.trim().isEmpty) return [];
    await _ensureLoaded();
    final local = _localSearch(name);
    if (local.isNotEmpty) return local;
    // 国内地名库没有命中的（如县级市、国外城市）再回退在线地理编码。
    final data = await get(Uri.https('geocoding-api.open-meteo.com', '/v1/search', {
      'name': name.trim(), 'count': '12', 'language': 'zh', 'format': 'json'}));
    return [for (final r in data['results'] ?? []) WeatherPlace(
      (r['latitude'] as num).toDouble(), (r['longitude'] as num).toDouble(),
      [r['name'], r['admin1'], r['country']].where((v) => v != null && '$v'.isNotEmpty).toSet().join(' · '))];
  }

  Future<String> reverseName(double lat, double lon) async {
    await _ensureLoaded();
    if (lon >= 72 && lon <= 136 && lat >= 15 && lat <= 55) {
      _LocalPlace? best;
      var bestDist = double.infinity;
      final cosLat = math.cos(lat * math.pi / 180);
      for (final p in _reversePlaces) {
        final dx = (p.lon - lon) * cosLat;
        final dy = p.lat - lat;
        final d = dx * dx + dy * dy;
        if (d < bestDist) { bestDist = d; best = p; }
      }
      if (best != null) return best.name;
    }
    try {
      final names = await placemarkFromCoordinates(lat, lon).timeout(const Duration(seconds: 4));
      if (names.isNotEmpty) {
        final a = names.first;
        final parts = [a.locality ?? a.subAdministrativeArea, a.administrativeArea, a.country]
            .whereType<String>().where((s) => s.isNotEmpty).toSet();
        if (parts.isNotEmpty) return parts.join(' · ');
      }
    } catch (_) {}
    return '${lat.toStringAsFixed(2)}, ${lon.toStringAsFixed(2)}';
  }

  static const _compassZh = {
    'n': '北', 'nne': '北东北', 'ne': '东北', 'ene': '东东北', 'e': '东',
    'ese': '东东南', 'se': '东南', 'sse': '南东南', 's': '南', 'ssw': '南西南',
    'sw': '西南', 'wsw': '西西南', 'w': '西', 'wnw': '西西北', 'nw': '西北', 'nnw': '北西北',
  };

  static String windDirection(String? compass) =>
      compass == null || compass == 'none' || compass == 'vrb'
          ? '' : (_compassZh[compass] ?? compass);

  static IconData icon(String code) => switch (code) {
    '100' => Icons.wb_sunny_outlined,
    '150' => Icons.nights_stay_outlined,
    '101' || '151' || '102' || '152' || '103' || '153' => Icons.wb_cloudy_outlined,
    '104' || '154' => Icons.cloud_outlined,
    '313' => Icons.ac_unit,
    '900' => Icons.thermostat,
    '901' => Icons.ac_unit,
    _ when code.startsWith('30') => Icons.thunderstorm,
    _ when code.startsWith('3') => Icons.umbrella,
    _ when code.startsWith('4') => Icons.ac_unit,
    _ when code == '503' || code == '504' || code == '507' || code == '508' => Icons.air,
    _ when code.startsWith('5') => Icons.foggy,
    _ => Icons.cloud_outlined,
  };
}

class WeatherPanel extends StatefulWidget {
  final JournalStore store;
  final AppPalette palette;
  const WeatherPanel({super.key, required this.store, required this.palette});
  @override State<WeatherPanel> createState() => _WeatherPanelState();
}

class _WeatherPanelState extends State<WeatherPanel> with WidgetsBindingObserver {
  final service = WeatherService();
  WeatherPlace? place;
  Map<String, dynamic>? data;
  bool busy = false, located = false, resolving = false, stale = false;
  String? error;
  String stamp = '';
  int generation = 0;
  DateTime? lastFetch;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final cache = widget.store.settings['weather_public_cache'];
    if (cache is Map && cache['lat'] is num && cache['lon'] is num && cache['data'] is Map) {
      data = Map<String, dynamic>.from(cache['data'] as Map? ?? {});
      place = WeatherPlace((cache['lat'] as num).toDouble(), (cache['lon'] as num).toDouble(), '${cache['name']}');
      stamp = '${cache['stamp']}';
    }
    unawaited(automatic());
    timer = Timer.periodic(const Duration(minutes: 15), (_) => unawaited(silentRefresh()));
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(onResume());
  }

  @override
  void dispose() {
    timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    generation++;
    super.dispose();
  }

  /// Android 上强制使用系统 LocationManager：部分国产 ROM 的 Google 融合定位
  /// 不可用（但系统定位本身正常），forceLocationManager 可以绕开它。
  LocationSettings _locationSettings() {
    if (Platform.isAndroid) {
      return AndroidSettings(
        accuracy: LocationAccuracy.low,
        timeLimit: const Duration(seconds: 15),
        forceLocationManager: true,
      );
    }
    return const LocationSettings(
      accuracy: LocationAccuracy.low,
      timeLimit: Duration(seconds: 15),
    );
  }

  /// 先取一次定位，失败再退回流式定位（两者都走 LocationManager）。
  Future<Position?> _currentPosition() async {
    try {
      return await Geolocator.getCurrentPosition(locationSettings: _locationSettings());
    } catch (e) {
      debugPrint('Weather getCurrentPosition failed: $e');
    }
    try {
      return await Geolocator.getPositionStream(locationSettings: _locationSettings())
          .first.timeout(const Duration(seconds: 12));
    } catch (e) {
      debugPrint('Weather position stream failed: $e');
    }
    return null;
  }

  static const _locationChannel = MethodChannel('kexinglu/weather_location');

  /// 直接走原生 LocationManager 取坐标（含 lastKnown），最可靠。
  Future<(double, double)?> _nativeLocation() async {
    try {
      final res = await _locationChannel.invokeMethod<Map>('getLocation');
      if (res != null) {
        final lat = res['lat'];
        final lon = res['lon'];
        final t = res['time'];
        if (lat is num && lon is num) {
          // 只接受 5 分钟内的定位，避免把上次在别的城市的位置当成当前位置。
          if (t is! num || DateTime.now().millisecondsSinceEpoch - t <= 5 * 60 * 1000) {
            return (lat.toDouble(), lon.toDouble());
          }
        }
      }
    } catch (e) {
      debugPrint('Weather native location failed: $e');
    }
    return null;
  }

  /// 依次尝试：原生 LocationManager → geolocator 上次位置 → geolocator 前台定位。
  Future<(double, double)?> _resolveLocation() async {
    final native = await _nativeLocation();
    if (native != null) return native;
    try {
      final last = await Geolocator.getLastKnownPosition();
      if (last != null) return (last.latitude, last.longitude);
    } catch (e) {
      debugPrint('Weather getLastKnownPosition failed: $e');
    }
    final current = await _currentPosition();
    if (current != null) return (current.latitude, current.longitude);
    return null;
  }

  Future<void> automatic() async {
    try {
      var permission = await Geolocator.checkPermission();
      // 打开应用就自动定位：首次进入时主动申请一次定位权限。
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      final granted = permission == LocationPermission.always || permission == LocationPermission.whileInUse;
      if (!granted) {
        if (mounted && place == null) {
          setState(() {
            error = permission == LocationPermission.deniedForever
                ? '定位权限已关闭，可在系统设置中开启，或手动选择城市'
                : '未获得定位权限，你仍可手动选择城市';
          });
        }
        return;
      }
      if (!await Geolocator.isLocationServiceEnabled()) {
        if (mounted && place == null) setState(() {error = '请开启手机定位服务，再获取当地天气';});
        return;
      }
      setState(() {busy = true; resolving = true;});
      final pos = await _resolveLocation();
      if (pos != null) {
        await applyPosition(pos.$1, pos.$2);
      } else {
        if (place == null) {
          // 实在拿不到定位：退回上次缓存的城市，保证一进来也有天气可看。
          final cache = widget.store.settings['weather_public_cache'];
          if (cache is Map && cache['lat'] is num && cache['lon'] is num) {
            place = WeatherPlace((cache['lat'] as num).toDouble(), (cache['lon'] as num).toDouble(), '${cache['name']}');
            final serial = ++generation;
            await fetch(serial);
            if (mounted) setState(() {stale = true;});
          } else if (mounted) {
            setState(() {error = '暂时无法定位，请确认系统定位开关和权限后重试，或手动选择城市';});
          }
        } else if (mounted) {
          // 有旧数据但这次没拿到新定位：标注为“上次位置”，别让用户以为是当前位置。
          setState(() {stale = true;});
        }
        if (mounted) setState(() {busy = false;});
      }
    } catch (e) {
      debugPrint('Weather automatic failed: $e');
      if (mounted) setState(() {busy = false;});
    } finally {
      if (mounted) setState(() {resolving = false;});
    }
  }

  Future<void> onResume() async {
    if (place == null || data == null) {
      unawaited(automatic());
      return;
    }
    if (lastFetch == null || DateTime.now().difference(lastFetch!) > const Duration(minutes: 10)) {
      unawaited(refresh());
    }
  }

  Future<void> silentRefresh() async {
    if (busy || place == null || !located) return;
    final serial = ++generation;
    try { await fetch(serial); } catch (_) {}
  }

  Future<void> locate({bool requestPermission = true}) async {
    if (busy) return;
    try {
      if (!await Geolocator.isLocationServiceEnabled()) throw const FormatException('请开启手机定位服务，再获取当地天气');
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied && requestPermission) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.deniedForever) throw const FormatException('定位权限已关闭，可在系统设置中开启，或手动选择城市');
      if (permission != LocationPermission.always && permission != LocationPermission.whileInUse) throw const FormatException('未获得定位权限，你仍可手动选择城市');
      final pos = await _resolveLocation();
      if (pos == null) throw const FormatException('暂时无法定位，请确认系统定位开关和权限后重试，或手动选择城市');
      await applyPosition(pos.$1, pos.$2);
    } catch (e) {
      debugPrint('Weather locate failed: $e');
      if (mounted) setState(() {error = e is FormatException ? e.message : '暂时无法定位，请确认系统定位开关和权限后重试，或手动选择城市';});
    }
  }

  Future<void> applyPosition(double lat, double lon) async {
    final serial = ++generation;
    setState(() {busy = true; error = null; stale = false;});
    try {
      final name = await service.reverseName(lat, lon);
      if (!mounted || serial != generation) return;
      if (place == null || (place!.lat - lat).abs() > .05 || (place!.lon - lon).abs() > .05) {
        data = null;
      }
      place = WeatherPlace(lat, lon, name);
      located = true;
      await fetch(serial);
    } catch (e) {
      if (mounted && serial == generation) setState(() {error = e is FormatException ? e.message : '暂时无法定位，请确认系统定位开关和权限后重试，或手动选择城市';});
    } finally { if (mounted && serial == generation) setState(() {busy = false;}); }
  }

  Future<void> fetch(int serial) async {
    try {
      final next = await service.current(place!);
      if (!mounted || serial != generation) return;
      final now = DateTime.now();
      setState(() { data = next; error = null; lastFetch = now;
        stamp = '${now.month}/${now.day} ${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}'; });
      await widget.store.setting('weather_public_cache', {'data': next,
        'lat': double.parse(place!.lat.toStringAsFixed(2)), 'lon': double.parse(place!.lon.toStringAsFixed(2)),
        'name': place!.name, 'stamp': stamp});
    } catch (_) {
      if (mounted && serial == generation) setState(() {error = '天气更新失败，可重试；已有数据仍保留';});
    }
  }

  Future<void> refresh() async {
    if (busy) return;
    if (place == null || !located) return locate();
    final serial = ++generation;
    setState(() {busy = true;});
    await fetch(serial);
    if (mounted) setState(() {busy = false;});
  }

  Future<void> choose() async {
    final next = await Navigator.push<WeatherPlace>(
      context,
      MaterialPageRoute(
        builder: (_) => WeatherSearchScreen(service: service, palette: widget.palette),
      ),
    );
    if (next == null || !mounted) return;
    final serial = ++generation;
    setState(() {place = next; located = false; busy = true; data = null; error = null; stale = false;});
    await fetch(serial);
    if (mounted && serial == generation) setState(() {busy = false;});
  }

  double? _num(dynamic v) => v is num ? v.toDouble() : null;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final temp = _num(data?['temperature']?['value']);
    final feels = _num(data?['feelsLike']?['value']);
    final humidity = _num(data?['humidity']);
    final windSpeed = _num(data?['wind']?['speed']?['value']);
    final text = data?['condition']?['text'] as String? ?? '';
    final code = data?['condition']?['code'] as String? ?? '';
    final compass = data?['wind']?['direction']?['compass'] as String?;
    final windZh = WeatherService.windDirection(compass);

    Widget metric(IconData ic, String v, String label) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
      decoration: BoxDecoration(
        color: p.background.withValues(alpha: .55),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: p.ink.withValues(alpha: .06)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 13, color: p.accent.withValues(alpha: .8)),
        const SizedBox(width: 6),
        Text(v, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 10.5, color: p.ink.withValues(alpha: .5))),
      ]),
    );

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: p.paper.withValues(alpha: .84),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: p.ink.withValues(alpha: .08)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: LocalText('天气', style: TextStyle(color: p.accent, fontSize: 13, fontWeight: FontWeight.w600))),
          IconButton(tooltip: '刷新天气', onPressed: busy ? null : refresh, icon: const Icon(Icons.refresh_rounded, size: 18)),
          IconButton(tooltip: '使用手机定位', onPressed: busy ? null : locate, icon: const Icon(Icons.my_location_rounded, size: 19)),
          TextButton(onPressed: busy ? null : choose, child: const LocalText('选择城市')),
        ]),
        if (place != null) Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Row(children: [
            Icon(Icons.pin_drop_outlined, size: 13, color: p.accent.withValues(alpha: .8)),
            const SizedBox(width: 6),
            Flexible(child: Text(place!.name, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500))),
            if (resolving || stale) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: p.accent.withValues(alpha: .10),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Text(resolving ? '定位中…' : '上次位置',
                  style: TextStyle(fontSize: 9, color: p.accent.withValues(alpha: .85))),
              ),
            ],
          ]),
        ),
        if (temp != null) ...[
          const SizedBox(height: 12),
          Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
            LocalText('${temp.round()}°', style: const TextStyle(
              fontSize: 56, height: 1.05, fontWeight: FontWeight.w300, letterSpacing: -2)),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(text.isEmpty ? '天气更新中' : text, style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w500)),
              const SizedBox(height: 4),
              LocalText('体感 ${feels?.round() ?? '—'}°', style: TextStyle(fontSize: 12, color: p.ink.withValues(alpha: .6))),
            ])),
            Icon(WeatherService.icon(code), color: p.accent, size: 54),
          ]),
          const SizedBox(height: 14),
          Row(children: [
            metric(Icons.water_drop_outlined, humidity == null ? '—' : '${humidity.clamp(0, 100).round()}%', '湿度'),
            const SizedBox(width: 8),
            metric(Icons.air, '${windZh.isNotEmpty ? '$windZh ' : ''}${windSpeed?.round() ?? '—'} m/s', '风'),
          ]),
        ] else if (!busy) ...[
          const SizedBox(height: 10),
          const LocalText('跟随你所在的地方', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          LocalText('仅用于获取当地天气，不记录移动轨迹。', style: TextStyle(fontSize: 12, color: p.ink.withValues(alpha: .6))),
          const SizedBox(height: 8),
          FilledButton.tonalIcon(onPressed: locate, icon: const Icon(Icons.near_me_outlined), label: const LocalText('定位当地天气')),
        ],
        if (busy) const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: LinearProgressIndicator(minHeight: 2)),
        if (error != null) ...[
          const SizedBox(height: 6),
          Text(error!, style: TextStyle(fontSize: 12, color: p.accent)),
          Wrap(children: [
            TextButton(onPressed: refresh, child: const LocalText('重试')),
            TextButton(onPressed: () => Geolocator.openAppSettings(), child: const LocalText('权限设置')),
            TextButton(onPressed: () => Geolocator.openLocationSettings(), child: const LocalText('定位设置')),
          ]),
        ],
      ]),
    );
  }
}

/// 城市搜索：整页、圆角卡片、软阴影，和 App 的纸页风格保持一致（不再是系统弹窗）。
class WeatherSearchScreen extends StatefulWidget {
  final WeatherService service;
  final AppPalette palette;
  const WeatherSearchScreen({super.key, required this.service, required this.palette});
  @override State<WeatherSearchScreen> createState() => _WeatherSearchScreenState();
}

class _WeatherSearchScreenState extends State<WeatherSearchScreen> {
  final input = TextEditingController();
  final focus = FocusNode();
  List<WeatherPlace> places = [];
  bool busy = false;
  String hint = '输入城市或区县名称，全国都能搜。';
  int serial = 0;
  Timer? debounce;

  @override
  void dispose() {
    debounce?.cancel();
    input.dispose();
    focus.dispose();
    serial++;
    super.dispose();
  }

  void changed(String value) {
    setState(() {});
    debounce?.cancel();
    if (value.trim().isEmpty) {
      setState(() {places = []; hint = '输入城市或区县名称，全国都能搜。';});
      return;
    }
    debounce = Timer(const Duration(milliseconds: 280), search);
  }

  Future<void> search() async {
    final id = ++serial;
    setState(() {busy = true;});
    try {
      final result = await widget.service.search(input.text);
      if (!mounted || id != serial) return;
      setState(() {
        places = result;
        hint = result.isEmpty ? '没有找到“${input.text.trim()}”，换个写法试试，或到县级名称搜索。' : '找到 ${result.length} 个地点';
      });
    } catch (_) {
      if (mounted && id == serial) setState(() {hint = '搜索暂不可用，请检查网络后重试';});
    } finally {
      if (mounted && id == serial) setState(() {busy = false;});
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return Scaffold(
      backgroundColor: p.background,
      body: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Row(children: [
              Material(
                color: p.paper,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: BorderSide(color: p.ink.withValues(alpha: .08)),
                ),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => Navigator.pop(context),
                  child: SizedBox(width: 40, height: 40,
                    child: Icon(Icons.arrow_back_rounded, size: 19, color: p.ink.withValues(alpha: .75))),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                LocalText('选择天气城市', style: TextStyle(fontSize: 18, height: 1.2,
                  fontWeight: FontWeight.w600, letterSpacing: -.4, color: p.ink)),
                const SizedBox(height: 3),
                LocalText('CITY SEARCH', style: TextStyle(fontSize: 7.5, letterSpacing: 1.8,
                  fontWeight: FontWeight.w600, color: p.accent.withValues(alpha: .7))),
              ])),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: p.paper,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: p.ink.withValues(alpha: .08)),
              ),
              child: Row(children: [
                Icon(Icons.search_rounded, size: 20, color: p.accent.withValues(alpha: .85)),
                const SizedBox(width: 8),
                Expanded(child: TextField(
                  controller: input, focusNode: focus, autofocus: true,
                  textInputAction: TextInputAction.search, onSubmitted: (_) => search(),
                  onChanged: changed,
                  style: TextStyle(fontSize: 14, color: p.ink),
                  decoration: InputDecoration(
                    hintText: '搜索城市 / 区县，如 义乌、安溪县',
                    hintStyle: TextStyle(fontSize: 13.5, color: p.ink.withValues(alpha: .35)),
                    border: InputBorder.none, isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                )),
                if (input.text.isNotEmpty) IconButton(
                  tooltip: '清空',
                  onPressed: () { input.clear(); changed(''); },
                  icon: Icon(Icons.close_rounded, size: 18, color: p.ink.withValues(alpha: .4)),
                ),
              ]),
            ),
          ),
          if (busy) Padding(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
            child: LinearProgressIndicator(minHeight: 2, color: p.accent,
              backgroundColor: p.accent.withValues(alpha: .12)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 6),
            child: Align(alignment: Alignment.centerLeft, child: Text(hint,
              style: TextStyle(fontSize: 11, height: 1.5, color: p.ink.withValues(alpha: .45)))),
          ),
          Expanded(child: places.isEmpty
            ? _empty(p)
            : ListView(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
                children: [for (final place in places) _result(p, place)],
              )),
        ]),
      ),
    );
  }

  Widget _result(AppPalette p, WeatherPlace place) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: p.paper,
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.pop(context, place),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: Row(children: [
            Container(width: 34, height: 34,
              decoration: BoxDecoration(
                color: p.accent.withValues(alpha: .1),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(Icons.location_on_outlined, size: 17, color: p.accent)),
            const SizedBox(width: 11),
            Expanded(child: Text(place.name, style: TextStyle(fontSize: 14,
              height: 1.3, fontWeight: FontWeight.w500, color: p.ink))),
            Icon(Icons.chevron_right_rounded, size: 18, color: p.ink.withValues(alpha: .3)),
          ]),
        ),
      ),
    ),
  );

  Widget _empty(AppPalette p) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.location_searching_rounded, size: 42, color: p.accent.withValues(alpha: .45)),
        const SizedBox(height: 16),
        LocalText('输入城市或区县名称', style: TextStyle(fontSize: 16,
          fontWeight: FontWeight.w600, color: p.ink)),
        const SizedBox(height: 8),
        LocalText('全国省 / 市 / 区县都能搜到，例如 义乌、安溪县、石狮。',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 12, height: 1.6, color: p.ink.withValues(alpha: .5))),
      ]),
    ),
  );
}

import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'store.dart';

class GeoPoint {
  final double lon, lat;
  final String name;
  const GeoPoint(this.lon, this.lat, this.name);
}

class AtlasData {
  Map<String, dynamic> airports = {}, stations = {}, cities = {}, china = {};
  List<dynamic> world = [];
  Future<void> load() async {
    Future<dynamic> read(String n) async =>
        jsonDecode(await rootBundle.loadString('assets/map/$n.json'));
    final data = await Future.wait(
      ['airports', 'rail-stations', 'places', 'china', 'world-land'].map(read),
    );
    airports = data[0];
    stations = data[1];
    cities = data[2];
    china = data[3];
    world = data[4] is List
        ? data[4]
        : (data[4]['rings'] ?? data[4]['land'] ?? []);
  }

  GeoPoint? locate(String name, String kind) {
    String n = name.trim();
    dynamic p;
    if (kind == 'air') {
      for (final token in RegExp(r'\b[A-Za-z]{3}\b').allMatches(n)) {
        p = airports[token.group(0)!.toUpperCase()];
        if (p != null) break;
      }
      String norm(String s) => s
          .replaceAll(RegExp(r'国际|机场|\s'), '')
          .replaceAll(RegExp(r'T\d+$', caseSensitive: false), '');
      if (p == null) {
        final matches = airports.values
            .where((a) => norm(a['name']) == norm(n))
            .toList();
        if (matches.length == 1) p = matches.first;
      }
    } else if (kind == 'rail') {
      p = stations[n.replaceAll(RegExp(r'\s|站$'), '')];
    }
    if (p != null) {
      return GeoPoint(
        (p['lon'] as num).toDouble(),
        (p['lat'] as num).toDouble(),
        n,
      );
    }
    final city = cities[n] ?? cities[n.replaceAll(RegExp(r'市$'), '')];
    return city == null
        ? null
        : GeoPoint((city[0] as num).toDouble(), (city[1] as num).toDouble(), n);
  }

  List<String> candidates(String query, String kind) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return [];
    final names = kind == 'air'
        ? airports.entries.map((e) => '${e.key} · ${e.value['name']}')
        : kind == 'rail'
        ? stations.keys
        : cities.keys;
    return names.where((n) => n.toLowerCase().contains(q)).take(8).toList();
  }
}

class RouteMap extends StatefulWidget {
  final AtlasData atlas;
  final List<Entry> records;
  final String mode;
  final Color accent;
  final bool dark, fullscreen, showControls, initialWorld;
  final String? selected;
  const RouteMap({super.key, required this.atlas, required this.records,
    required this.mode, required this.accent, this.dark = false,
    this.selected, this.fullscreen = false, this.showControls = true,
    this.initialWorld = false});
  @override State<RouteMap> createState() => _RouteMapState();
}
class _RouteMapState extends State<RouteMap> {
  final transform = TransformationController();
  late bool worldView = widget.initialWorld;
  Size? viewport;
  void frame(Size size, bool world) {
    // A single world projection: China is a camera position, never a clipped map.
    final base = math.min(size.width / 360, size.height / 145);
    final scale = world ? 1.0 : (math.min(size.width / 76, size.height / 52) / base).clamp(.5, 12.0);
    final point = world ? Offset(size.width / 2, size.height / 2)
      : Offset(size.width / 2 + 104 * base, size.height / 2 + (12.5 - 35) * base);
    transform.value = Matrix4.identity()
      ..translateByDouble(size.width / 2 - point.dx * scale, size.height / 2 - point.dy * scale, 0, 1)
      ..scaleByDouble(scale, scale, 1, 1);
  }
  @override void dispose() { transform.dispose(); super.dispose(); }
  Future<void> open() async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => _FullMap(map: widget, initialWorld: worldView)));
  }
  void zoom(double factor, Size size) {
    final old = transform.value.getMaxScaleOnAxis();
    final next = (old * factor).clamp(.5, 12.0);
    final center = Offset(size.width / 2, size.height / 2);
    final point = transform.toScene(center);
    transform.value = Matrix4.identity()
      ..translateByDouble(center.dx - point.dx * next, center.dy - point.dy * next, 0, 1)
      ..scaleByDouble(next, next, 1, 1);
  }
  @override Widget build(BuildContext context) {
    final points = <List<GeoPoint>>[];
    int? focus;
    for (final e in widget.records) {
      if (widget.mode == 'travel') {
        final lat = double.tryParse(e.text('lat')), lon = double.tryParse(e.text('lon'));
        final p = lat != null && lon != null && lat.abs() <= 90 && lon.abs() <= 180 && (lat != 0 || lon != 0)
            ? GeoPoint(lon, lat, e.text('city').isEmpty ? e.text('title') : e.text('city'))
            : widget.atlas.locate(e.text('city'), 'city');
        if (p != null) points.add([p]);
      } else {
        final a = widget.atlas.locate(e.text('from'), widget.mode), b = widget.atlas.locate(e.text('to'), widget.mode);
        if (a != null && b != null) {
          if (e.id == widget.selected) focus = points.length;
          points.add([a, b]);
        }
      }
    }
    final title = widget.mode == 'travel' ? '我的足迹' : '${widget.mode == 'air' ? '飞行' : '铁路'}轨迹';
    return ClipRRect(borderRadius: BorderRadius.circular(widget.fullscreen ? 0 : 24),
      child: ColoredBox(color: widget.dark ? const Color(0xff17282c) : const Color(0xffe6eeeb),
        child: LayoutBuilder(builder: (context, constraints) {
          final size = constraints.biggest;
          if (viewport != size) { viewport = size; frame(size, worldView); }
          Widget chrome(Widget child) => IgnorePointer(
            ignoring: !widget.showControls,
            child: AnimatedOpacity(
              opacity: widget.showControls ? 1 : 0,
              duration: const Duration(milliseconds: 220),
              child: child,
            ),
          );
          return Stack(children: [
            Positioned.fill(child: InteractiveViewer(
              key: const ValueKey('route-map-pan-zoom'), transformationController: transform,
              minScale: .5, maxScale: 12, boundaryMargin: const EdgeInsets.all(1600),
              trackpadScrollCausesScale: true,
              child: AnimatedBuilder(animation: transform, builder: (_, _) => RepaintBoundary(child: CustomPaint(
                painter: AtlasPainter(widget.atlas, points, widget.accent, widget.dark, widget.mode, focus,
                  worldView: true, zoom: transform.value.getMaxScaleOnAxis()), size: size))))),
            if (!widget.fullscreen)
              Positioned(left: 16, top: 16, child: chrome(Text(title, style: TextStyle(
                color: widget.dark ? Colors.white70 : const Color(0xff3d625b), fontWeight: FontWeight.w600)))),
            Positioned(
              left: 12,
              bottom: 12,
              child: chrome(Material(
                color: (widget.dark ? const Color(0xff243a3c) : Colors.white).withValues(alpha: .9),
                borderRadius: BorderRadius.circular(18),
                elevation: 2,
                child: InkWell(
                  onTap: () => setState(() { worldView = !worldView; frame(size, worldView); }),
                  borderRadius: BorderRadius.circular(18),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(worldView ? Icons.map_rounded : Icons.public_rounded,
                        size: 15,
                        color: widget.dark ? Colors.white70 : const Color(0xff3d625b)),
                      const SizedBox(width: 5),
                      Text(worldView ? '中国视角' : '世界地图',
                        style: TextStyle(fontSize: 11,
                          color: widget.dark ? Colors.white70 : const Color(0xff3d625b))),
                    ]),
                  ),
                ),
              )),
            ),
            Positioned(right: 12, bottom: 12, child: chrome(Material(
              color: (widget.dark ? const Color(0xff243a3c) : Colors.white).withValues(alpha: .9),
              borderRadius: BorderRadius.circular(18), elevation: 2,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                if (widget.fullscreen) ...[
                  IconButton(tooltip: '放大地图', onPressed: () => zoom(1.4, size), icon: const Icon(Icons.add)),
                  IconButton(tooltip: '缩小地图', onPressed: () => zoom(1/1.4, size), icon: const Icon(Icons.remove)),
                  IconButton(tooltip: '复位地图', onPressed: () { worldView = false; frame(size, false); }, icon: const Icon(Icons.center_focus_strong)),
                ],
                if (!widget.fullscreen) IconButton(tooltip: '全屏地图', onPressed: open, icon: const Icon(Icons.fullscreen_rounded)),
              ])))),
          ]);
        })));
  }
}
class _FullMap extends StatefulWidget {
  final RouteMap map;
  final bool initialWorld;
  const _FullMap({required this.map, this.initialWorld = true});
  @override State<_FullMap> createState() => _FullMapState();
}
class _FullMapState extends State<_FullMap> {
  bool landscape = false;
  bool controls = true;
  Timer? hideTimer;

  @override
  void initState() {
    super.initState();
    _scheduleHide();
  }

  void _scheduleHide() {
    hideTimer?.cancel();
    hideTimer = Timer(const Duration(seconds: 3), () {
      if (mounted) setState(() => controls = false);
    });
  }

  void _showControls() {
    if (!mounted) return;
    setState(() => controls = true);
    _scheduleHide();
  }

  void _toggleControls() {
    if (controls) {
      hideTimer?.cancel();
      setState(() => controls = false);
    } else {
      _showControls();
    }
  }

  Future<void> rotate() async {
    final next = !landscape;
    await SystemChrome.setPreferredOrientations(next
      ? [DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]
      : [DeviceOrientation.portraitUp]);
    if (mounted) setState(() {landscape = next; controls = true;});
    _scheduleHide();
  }

  @override
  void dispose() {
    hideTimer?.cancel();
    // Restore the normal app's system-controlled orientation on every exit.
    SystemChrome.setPreferredOrientations([]);
    super.dispose();
  }

  Widget _button(IconData icon, String tip, VoidCallback onTap) => Material(
    color: Colors.black.withValues(alpha: .46),
    shape: const CircleBorder(),
    clipBehavior: Clip.antiAlias,
    child: IconButton(
      tooltip: tip,
      onPressed: onTap,
      icon: Icon(icon, color: Colors.white, size: 20),
    ),
  );

  Widget _pill(IconData icon, String label, VoidCallback onTap) => Material(
    color: Colors.black.withValues(alpha: .46),
    shape: const StadiumBorder(),
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: Colors.white, size: 17),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500)),
        ]),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.black,
    body: Listener(onPointerDown: (_) { if (controls) _scheduleHide(); }, child: Stack(fit: StackFit.expand, children: [
      GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: _toggleControls,
        child: RouteMap(
          atlas: widget.map.atlas,
          records: widget.map.records,
          mode: widget.map.mode,
          accent: widget.map.accent,
          dark: widget.map.dark,
          selected: widget.map.selected,
          fullscreen: true,
          showControls: controls,
          initialWorld: widget.initialWorld,
        ),
      ),
      IgnorePointer(
        ignoring: !controls,
        child: AnimatedOpacity(
          opacity: controls ? 1 : 0,
          duration: const Duration(milliseconds: 220),
          child: SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
                child: Row(children: [
                  _button(Icons.close_rounded, '退出全屏地图', () => Navigator.pop(context)),
                  const Spacer(),
                  _pill(
                    landscape ? Icons.screen_lock_portrait_rounded : Icons.screen_rotation_rounded,
                    landscape ? '竖屏' : '横屏',
                    rotate,
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    ])),
  );
}

class AtlasPainter extends CustomPainter {
  final AtlasData data;
  final List<List<GeoPoint>> routes;
  final Color accent;
  final bool dark;
  final String mode;
  final int? focus;
  final bool worldView;
  final double zoom;
  AtlasPainter(
    this.data,
    this.routes,
    this.accent,
    this.dark,
    this.mode,
    this.focus, {
    this.worldView = false,
    this.zoom = 1,
  });
  @override
  void paint(Canvas canvas, Size size) {
    // Geometry shares the map transform; screen-space strokes, labels and markers
    // compensate for zoom so close-up routes remain crisp instead of giant ribbons.
    final unit = 1 / zoom.clamp(.5, 12.0);
    final all = routes.expand((r) => r).toList();
    final worldwide = all.any(
      (p) => p.lon < 72 || p.lon > 136 || p.lat < 15 || p.lat > 55,
    );
    final broad = worldView || worldwide;
    double left = broad ? -180 : 72,
        right = broad ? 180 : 136,
        bottom = broad ? -60 : 15,
        top = broad ? 85 : 55;
    // 国内地图固定为完整中国视野，不再按轨迹裁切，避免地图被切掉一块。
    final scale = math.min(
      size.width / (right - left),
      size.height / (top - bottom),
    );
    Offset xy(double lon, double lat) => Offset(
      (lon - (left + right) / 2) * scale + size.width / 2,
      ((top + bottom) / 2 - lat) * scale + size.height / 2,
    );
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    void ring(List<dynamic> raw) {
      if (raw.isEmpty) return;
      final path = Path();
      for (var i = 0; i < raw.length; i++) {
        final p = xy(
          (raw[i][0] as num).toDouble(),
          (raw[i][1] as num).toDouble(),
        );
        i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
      }
      path.close();
      canvas.drawPath(
        path,
        Paint()
          ..color = dark ? const Color(0xff243a3c) : const Color(0xfff6f3eb),
      );
      canvas.drawPath(
        path,
        Paint()
          ..color = (dark ? Colors.white : accent).withValues(alpha: .16)
          ..style = PaintingStyle.stroke
          ..strokeWidth = .65 * unit,
      );
    }

    // 世界陆地始终作为底图，再叠中国省界，任何视野下都不是“只有中国”。
    for (final r in data.world) {
      if (r is List) ring(r);
    }
    for (final province in (data.china['provinces'] ?? [])) {
      for (final r in province['rings']) {
        ring(r);
      }
    }
    final seen = <String>{};
    for (final indexed in routes.asMap().entries) {
      final route = indexed.value;
      final routeColor = focus == null || focus == indexed.key
          ? accent
          : accent.withValues(alpha: .25);
      if (route.length == 2) {
        final a = xy(route[0].lon, route[0].lat),
            b = xy(route[1].lon, route[1].lat),
            mid = (a + b) / 2,
            delta = b - a;
        final control = mid + Offset(delta.dy * .22, -delta.dx * .22);
        final path = Path()
          ..moveTo(a.dx, a.dy)
          ..quadraticBezierTo(control.dx, control.dy, b.dx, b.dy);
        canvas.drawPath(
          path,
          Paint()
            ..color = routeColor.withValues(alpha: .12)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 8 * unit,
        );
        canvas.drawPath(
          path,
          Paint()
            ..color = routeColor
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.8 * unit,
        );
      }
      for (final p in route) {
        if (!seen.add(p.name)) continue;
        final pos = xy(p.lon, p.lat);
        canvas.drawCircle(
          pos,
          7 * unit,
          Paint()..color = dark ? const Color(0xff243a3c) : Colors.white,
        );
        if (mode == 'travel') {
          canvas.drawCircle(pos, 3.4 * unit, Paint()..color = accent);
        } else {
          final icon = mode == 'air'
              ? Icons.flight_rounded
              : Icons.train_rounded;
          final glyph = TextPainter(
            text: TextSpan(
              text: String.fromCharCode(icon.codePoint),
              style: TextStyle(
                fontFamily: icon.fontFamily,
                package: icon.fontPackage,
                fontSize: 10 * unit,
                color: accent,
              ),
            ),
            textDirection: TextDirection.ltr,
          )..layout();
          glyph.paint(canvas, pos - Offset(glyph.width / 2, glyph.height / 2));
        }
        final text = TextPainter(
          text: TextSpan(
            text: p.name.replaceAll(RegExp(r'国际机场|机场|^[A-Z]{3} · '), ''),
            style: TextStyle(
              fontSize: 9 * unit,
              color: dark ? Colors.white70 : const Color(0xff36534d),
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout(maxWidth: 100 * unit);
        text.paint(canvas, pos + Offset(-text.width / 2, 11 * unit));
      }
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant AtlasPainter old) =>
      old.zoom != zoom ||
      old.accent != accent ||
      old.dark != dark ||
      old.mode != mode ||
      old.focus != focus ||
      old.worldView != worldView ||
      old.routes
              .map((r) => r.map((p) => '${p.lon},${p.lat},${p.name}').join('|'))
              .join(';') !=
          routes
              .map((r) => r.map((p) => '${p.lon},${p.lat},${p.name}').join('|'))
              .join(';');
}

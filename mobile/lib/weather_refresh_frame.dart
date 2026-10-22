import 'package:flutter/material.dart';

/// Paint only the perimeter while fetching; the weather content stays still.
class WeatherRefreshFrame extends StatefulWidget {
  final bool refreshing, reduced;
  final Color color;
  final Widget child;
  const WeatherRefreshFrame({super.key, required this.refreshing, required this.color,
    required this.child, this.reduced = false});
  @override State<WeatherRefreshFrame> createState() => _WeatherRefreshFrameState();
}

class _WeatherRefreshFrameState extends State<WeatherRefreshFrame> with SingleTickerProviderStateMixin {
  late final controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800));
  void sync() {
    if (widget.refreshing && !widget.reduced && !MediaQuery.disableAnimationsOf(context)) {
      if (!controller.isAnimating) controller.repeat();
    } else { controller.stop(); }
  }
  @override void didChangeDependencies() { super.didChangeDependencies(); sync(); }
  @override void didUpdateWidget(WeatherRefreshFrame old) { super.didUpdateWidget(old); sync(); }
  @override void dispose() { controller.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) => Stack(children: [
    widget.child,
    if (widget.refreshing) Positioned.fill(child: IgnorePointer(child: Semantics(
      label: '正在刷新天气', liveRegion: true,
      child: RepaintBoundary(child: CustomPaint(painter: _PerimeterPainter(controller, widget.color))),
    ))),
  ]);
}

class _PerimeterPainter extends CustomPainter {
  final Animation<double> phase;
  final Color color;
  _PerimeterPainter(this.phase, this.color) : super(repaint: phase);
  @override void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final path = Path()..addRRect(RRect.fromRectAndRadius(
      (Offset.zero & size).deflate(1.5), const Radius.circular(21)));
    final metric = path.computeMetrics().first;
    final paint = Paint()..style = PaintingStyle.stroke..strokeCap = StrokeCap.round;
    canvas.drawPath(path, paint..color = color.withValues(alpha: .16)..strokeWidth = 1.5);
    // A short, fading trail follows the actual rounded border at any card size.
    for (var i = 0; i < 24; i++) {
      final start = ((phase.value + i * .009) % 1) * metric.length;
      final end = start + metric.length * .011;
      paint..color = color.withValues(alpha: .08 + .82 * i / 23)..strokeWidth = 2.2;
      canvas.drawPath(metric.extractPath(start, end.clamp(0, metric.length)), paint);
      if (end > metric.length) canvas.drawPath(metric.extractPath(0, end - metric.length), paint);
    }
  }
  @override bool shouldRepaint(_PerimeterPainter old) => old.color != color || old.phase != phase;
}

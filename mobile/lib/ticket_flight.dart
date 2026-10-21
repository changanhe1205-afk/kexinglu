import 'dart:math' as math;
import 'package:flutter/material.dart';

/// One reversible journey from the actual card bounds, respecting reduced motion.
class TicketFlight extends StatefulWidget {
  final Rect origin;
  final Widget front, back;
  final bool reduced;
  const TicketFlight({super.key, required this.origin, required this.front, required this.back, required this.reduced});
  @override State<TicketFlight> createState() => _TicketFlightState();
}
class _TicketFlightState extends State<TicketFlight> with SingleTickerProviderStateMixin {
  late final animation = AnimationController(vsync: this, duration: Duration(milliseconds: widget.reduced ? 1600 : 2800));
  @override void initState() {
    super.initState();
    animation.forward().whenComplete(() { if (mounted) Navigator.pop(context); });
  }
  @override void dispose() { animation.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) => AnimatedBuilder(animation: animation, builder: (context, _) {
    final size = MediaQuery.sizeOf(context);
    final width = math.min(size.width - 40, 560.0);
    final height = math.min(330.0, size.height - 100);
    final center = Rect.fromCenter(center: size.center(Offset.zero), width: width, height: height);
    final t = animation.value;
    final lift = widget.reduced ? 1.0 : t < .2 ? Curves.easeOutCubic.transform(t / .2)
      : t > .8 ? 1 - Curves.easeInOutCubic.transform((t - .8) / .2) : 1.0;
    final rect = Rect.lerp(widget.origin, center, lift)!;
    final flip = ((t - .22) / .22).clamp(0.0, 1.0);
    final angle = widget.reduced ? 0.0 : Curves.easeInOutCubic.transform(flip) * math.pi;
    final back = widget.reduced ? t > .3 : angle > math.pi / 2;
    return Material(color: Colors.transparent, child: Stack(children: [
      Positioned.fill(child: GestureDetector(onTap: () => Navigator.pop(context),
        child: ColoredBox(color: Colors.black.withValues(alpha: .3 * lift)))),
      Positioned.fromRect(rect: rect, child: Transform(alignment: Alignment.center,
        transform: Matrix4.identity()..setEntry(3, 2, .001)..rotateY(angle),
        child: Transform(alignment: Alignment.center, transform: Matrix4.rotationY(back && !widget.reduced ? math.pi : 0),
          child: back ? widget.back : widget.front))),
    ]));
  });
}

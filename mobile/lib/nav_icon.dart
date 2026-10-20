import 'dart:math' as math;
import 'package:flutter/material.dart';

class AnimatedNavIcon extends StatefulWidget {
  final IconData icon;
  final int index, pulse;
  final bool reduced;
  final Color color;
  const AnimatedNavIcon({super.key, required this.icon, required this.index, required this.pulse, required this.reduced, required this.color});
  @override State<AnimatedNavIcon> createState() => _AnimatedNavIconState();
}
class _AnimatedNavIconState extends State<AnimatedNavIcon> with SingleTickerProviderStateMixin {
  late final controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 650));
  @override void initState() {super.initState(); controller.value=1;}
  @override void didUpdateWidget(AnimatedNavIcon old) {
    super.didUpdateWidget(old);
    if (old.pulse != widget.pulse && !widget.reduced) controller.forward(from: 0);
    if (widget.reduced) controller.value=1;
  }
  @override void dispose() {controller.dispose(); super.dispose();}
  @override Widget build(BuildContext context) => AnimatedBuilder(animation: controller, builder: (context, _) {
    final t=Curves.easeOutCubic.transform(controller.value);
    final wave=math.sin(t*math.pi);
    final rotation=widget.index==1 ? t*math.pi*2 : widget.index==2 ? math.sin(t*math.pi*2)*.18 : 0.0;
    return Transform.translate(offset: Offset(0, widget.index==0 ? -4*wave : 0),
      child: Transform.rotate(angle: rotation, child: Transform.scale(scale: widget.index>=3 ? 1+.22*wave : 1,
        child: Icon(widget.icon, size: 22, color: widget.color))));
  });
}

import 'i18n.dart';
import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'cloud_account.dart';
import 'store.dart';

final birthdayRoutes = RouteObserver<ModalRoute<void>>();

/// Local calendar date, never UTC: February 29 only matches February 29.
bool isBirthday(dynamic value, DateTime today) {
  if (value is! String || !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) return false;
  final parts = value.split('-').map(int.parse).toList();
  final birth = DateTime(parts[0], parts[1], parts[2]);
  if (birth.year != parts[0] || birth.month != parts[1] || birth.day != parts[2] ||
      birth.isAfter(DateTime(today.year, today.month, today.day))) { return false; }
  return birth.month == today.month && birth.day == today.day;
}

String birthdayDay(DateTime date) => '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

/// Startup, returning to the app, and returning from profile/login all recheck.
/// No network request or image download is required for the celebration.
class BirthdayGate extends StatefulWidget {
  final JournalStore store;
  final Widget child;
  final DateTime Function()? clock;
  const BirthdayGate({super.key, required this.store, required this.child, this.clock});
  @override State<BirthdayGate> createState() => _BirthdayGateState();
}

class _BirthdayGateState extends State<BirthdayGate> with WidgetsBindingObserver, RouteAware {
  bool ready = false, scheduled = false;
  final shown = <String>{};
  DialogRoute<void>? celebration;
  String? activeOwner;
  final cloud = CloudAccount.instance;

  @override void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.store.addListener(schedule);
    cloud.addListener(schedule);
    ready = cloud.initialized;
    if (ready) { schedule(); }
    else { cloud.initialize().then((_) {if (mounted) {ready = true; schedule();}}); }
  }
  @override void didChangeDependencies() {
    super.didChangeDependencies();
    final route = ModalRoute.of(context);
    if (route != null) birthdayRoutes.subscribe(this, route);
  }
  @override void didPopNext() => schedule();
  @override void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) schedule();
  }
  void schedule() {
    if (!mounted || scheduled) return;
    scheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      scheduled = false;
      if (mounted) check();
    });
    WidgetsBinding.instance.ensureVisualUpdate();
  }
  void check() {
    if (!ready) return;
    final owner = cloud.uid ?? 'guest';
    if (celebration != null) {
      if (activeOwner != owner) {
        final previous = celebration!;
        celebration = null;
        previous.navigator?.removeRoute(previous);
        schedule();
      }
      return;
    }
    // Never interrupt an editor, login screen, system permission prompt or background app.
    if (ModalRoute.of(context)?.isCurrent != true ||
        (WidgetsBinding.instance.lifecycleState != null &&
         WidgetsBinding.instance.lifecycleState != AppLifecycleState.resumed)) { return; }
    final raw = widget.store.settings['personal_profile:$owner'];
    final local = raw is Map ? raw : const {};
    final remote = cloud.client?.auth.currentUser?.userMetadata?['kexinglu_profile'];
    final profile = local['pending'] == true || remote is! Map ? local : remote;
    final today = (widget.clock ?? DateTime.now)().toLocal();
    final day = birthdayDay(today);
    final key = 'birthday_seen:$owner';
    if (!isBirthday(profile['birthday'], today) || widget.store.settings[key] == day || shown.contains('$owner:$day')) return;
    shown.add('$owner:$day');
    activeOwner = owner;
    final route = DialogRoute<void>(context: context, barrierDismissible: false,
      barrierColor: const Color(0xa6223733), builder: (_) => BirthdayCard(
        nickname: '${profile['nickname'] ?? ''}', date: today,
        reduced: widget.store.settings['reduced'] == true || MediaQuery.disableAnimationsOf(context)));
    celebration = route;
    unawaited(Navigator.of(context).push(route).whenComplete(() {
      if (identical(celebration, route)) celebration = null;
      if (mounted) schedule();
    }));
    // Persist only after the card has been presented; storage failure never blocks dismissal.
    unawaited(widget.store.setting(key, day).catchError((Object _) {}));
  }
  @override void dispose() {
    birthdayRoutes.unsubscribe(this);
    WidgetsBinding.instance.removeObserver(this);
    widget.store.removeListener(schedule);
    cloud.removeListener(schedule);
    super.dispose();
  }
  @override Widget build(BuildContext context) => widget.child;
}

class BirthdayCard extends StatefulWidget {
  final String nickname;
  final DateTime date;
  final bool reduced;
  const BirthdayCard({super.key, required this.nickname, required this.date, this.reduced = false});
  @override State<BirthdayCard> createState() => _BirthdayCardState();
}

class _BirthdayCardState extends State<BirthdayCard> with SingleTickerProviderStateMixin {
  late final animation = AnimationController(vsync: this, duration: const Duration(milliseconds: 2600));
  bool wished = false;
  static const ink = Color(0xff493047);
  @override void initState() {
    super.initState();
    if (!widget.reduced) animation.forward();
  }
  @override void dispose() {animation.dispose(); super.dispose();}
  void wish() {
    if (wished) return;
    setState(() {wished = true;});
    if (!widget.reduced) animation.forward(from: 0);
  }
  @override Widget build(BuildContext context) {
    final name = widget.nickname.trim();
    return Dialog(backgroundColor: Colors.transparent, elevation: 0,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 390), child: ClipRRect(
        borderRadius: BorderRadius.circular(32), child: ColoredBox(color: const Color(0xfffffaf4),
          child: Stack(children: [
            const Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(gradient: RadialGradient(
              center: Alignment(-1, -.7), radius: 1.4, colors: [Color(0xffffdfdb), Color(0x00fffaf4)])))),
            const Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(gradient: RadialGradient(
              center: Alignment(1, .2), radius: 1.1, colors: [Color(0x55e5d8fa), Color(0x00fffaf4)])))),
            SingleChildScrollView(child: Padding(padding: const EdgeInsets.fromLTRB(24, 48, 24, 22),
              child: DefaultTextStyle(style: const TextStyle(color: ink, fontFamily: 'serif'), child: Column(mainAxisSize: MainAxisSize.min, children: [
                LocalText('${widget.date.month.toString().padLeft(2, '0')} / ${widget.date.day.toString().padLeft(2, '0')}',
                  style: const TextStyle(fontSize: 14, letterSpacing: 4)),
                const SizedBox(height: 18),
                Text(name.isEmpty ? tr('生日快乐') : '${tr('生日快乐')}, $name', textAlign: TextAlign.center, maxLines: 3, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 30, height: 1.35, fontWeight: FontWeight.w500)),
                const SizedBox(height: 10),
                const LocalText('Happy birthday', style: TextStyle(fontSize: 12, letterSpacing: 3, color: Color(0xff937b8c))),
                const SizedBox(height: 14),
                Semantics(button: true, label: wished ? '心愿已许下' : '轻触烛光，许个愿吧', child: GestureDetector(
                  key: const ValueKey('birthday-candles'), behavior: HitTestBehavior.opaque, onTap: wish,
                  child: SizedBox(height: 206, width: double.infinity, child: RepaintBoundary(child: CustomPaint(
                    painter: _Candles(animation, wished, widget.reduced)))))),
                const SizedBox(height: 8),
                Semantics(liveRegion: true, child: LocalText(wished ? '愿你的心愿，在新一岁慢慢实现' : '轻触烛光，许个愿吧', textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: Color(0xff937b8c), height: 1.6))),
                const SizedBox(height: 26),
                const LocalText('愿新一岁的你，\n有热爱，也有说走就走的勇气。', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 17, height: 1.9)),
                const SizedBox(height: 28),
                SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(context),
                  style: FilledButton.styleFrom(backgroundColor: ink, foregroundColor: const Color(0xfffffaf4),
                    padding: const EdgeInsets.symmetric(vertical: 17), textStyle: const TextStyle(fontSize: 16)),
                  child: const LocalText('收下这份祝福'))),
                const SizedBox(height: 16),
                const LocalText('客行录 · 陪你收藏每一岁', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 10, letterSpacing: 1, color: Color(0xff937b8c))),
              ])))),
            Positioned(top: 6, right: 6, child: IconButton(tooltip: '收起生日祝福', onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.close_rounded, color: ink, size: 22))),
          ])))));
  }
}

/// Vector candles keep the artwork crisp and animate only this small layer.
class _Candles extends CustomPainter {
  final Animation<double> animation;
  final bool wished, reduced;
  _Candles(this.animation, this.wished, this.reduced) : super(repaint: animation);
  @override void paint(Canvas canvas, Size size) {
    canvas.save(); canvas.scale(size.width / 300, size.height / 206);
    final t = reduced ? 1.0 : animation.value;
    final paint = Paint();
    canvas.drawOval(const Rect.fromLTWH(45, 183, 210, 18), paint..color = const Color(0x22d999b8));
    final orbit = Path()..addOval(const Rect.fromLTWH(8, 82, 284, 93));
    canvas.save(); canvas.translate(150, 128); canvas.rotate(-.27); canvas.translate(-150, -128);
    canvas.drawPath(orbit, paint..color = const Color(0x55e0a1d0)..style = PaintingStyle.stroke..strokeWidth = .8);
    canvas.restore(); paint.style = PaintingStyle.fill;
    const colors = [Color(0xffffb9c6), Color(0xffd7bfea), Color(0xffffc5aa)];
    for (var i = 0; i < 3; i++) {
      final x = 77.0 + i * 73, top = i == 1 ? 60.0 : 99.0;
      final body = Rect.fromLTRB(x - 22, top, x + 22, 191);
      paint.shader = LinearGradient(colors: [colors[i], Color.lerp(colors[i], Colors.white, .45)!]).createShader(body);
      canvas.drawRRect(RRect.fromRectAndRadius(body, const Radius.circular(12)), paint);
      paint.shader = null;
      canvas.save(); canvas.clipRRect(RRect.fromRectAndRadius(body, const Radius.circular(12)));
      for (var j = 0; j < 3; j++) {
        final y = top + 17 + j * 53;
        final stripe = Path()..moveTo(x - 24, y + 49)..cubicTo(x - 14, y + 12, x + 20, y + 20, x + 24, y - 12);
        canvas.drawPath(stripe, paint..color = const Color(0xbfffffff)..style = PaintingStyle.stroke..strokeWidth = 1);
      }
      canvas.restore(); paint.style = PaintingStyle.fill;
      canvas.drawLine(Offset(x, top + 2), Offset(x, top - 10), paint..color = const Color(0xff8d6977)..strokeWidth = 2);
      if (!wished) {
        final flicker = 1 + .06 * math.sin(t * math.pi * 9 + i);
        canvas.save(); canvas.translate(x, top - 10); canvas.scale(flicker, flicker);
        canvas.drawCircle(const Offset(0, -13), 26, paint..color = const Color(0x22ffbe68)..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14));
        paint.maskFilter = null;
        final flame = Path()..moveTo(0, -34)..cubicTo(5,-22,17,-9,7,-2)..cubicTo(-9,9,-18,-7,0,-34);
        canvas.drawPath(flame, paint..color = const Color(0xffffc270));
        canvas.drawOval(const Rect.fromLTWH(-3,-12,6,13), paint..color = const Color(0xffffefbb));
        canvas.restore();
      }
    }
    // A finite shower, never a perpetual full-screen animation.
    for (var i = 0; i < 22; i++) {
      final x = (i * 67 % 290).toDouble() + 5;
      final y = reduced || t == 1 ? (i * 37 % 175).toDouble() : ((i * 37 + t * 135) % 196);
      final opacity = wished && !reduced ? (1 - t).clamp(0.0, 1.0) : .48;
      canvas.save(); canvas.translate(x, y); canvas.rotate(i + t * 2);
      paint.color = [const Color(0xffd69f55), ...colors][i % 4].withValues(alpha: opacity);
      if (i % 3 == 0) {canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(-1,-3,2,6), const Radius.circular(1)), paint);}
      else {canvas.drawCircle(Offset.zero, i % 2 == 0 ? 2 : 1.5, paint);}
      canvas.restore();
    }
    canvas.restore();
  }
  @override bool shouldRepaint(covariant _Candles old) => old.wished != wished || old.reduced != reduced;
}

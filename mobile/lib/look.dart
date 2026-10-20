import 'i18n.dart';
import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

class AppPalette {
  final String name;
  final Color accent, background;
  final bool dark;
  const AppPalette(
    this.name,
    this.accent,
    this.background, [
    this.dark = false,
  ]);
  Color get ink => dark ? const Color(0xfff1eee6) : const Color(0xff243b36);
  Color get paper => dark
      ? Color.lerp(background, Colors.white, .06)!
      : const Color(0xfffffdf7);
  static const all = [
    AppPalette('海盐青', Color(0xff347b73), Color(0xffedf2ec)),
    AppPalette('纸间暖白', Color(0xffa66d4c), Color(0xfff4efe5)),
    AppPalette('鼠尾草', Color(0xff637b56), Color(0xffeff1e7)),
    AppPalette('经典雾蓝', Color(0xff4c78a8), Color(0xffeef2f5)),
    AppPalette('浅紫', Color(0xff8570a8), Color(0xfff1edf6)),
    AppPalette('石墨灰', Color(0xff596574), Color(0xffeef0f2)),
    AppPalette('深海青', Color(0xff8cc8c0), Color(0xff14292d), true),
    AppPalette('午夜蓝', Color(0xff96b8df), Color(0xff152335), true),
    AppPalette('可可夜色', Color(0xffd2b28e), Color(0xff2b2622), true),
    AppPalette('暮色紫', Color(0xffc0a9d0), Color(0xff25212d), true),
    AppPalette('深色石墨', Color(0xffbcc7d1), Color(0xff1c2024), true),
    AppPalette('陶土暖白', Color(0xffae7258), Color(0xfff6eee7)),
  ];
}

class Glass extends StatelessWidget {
  final Widget child;
  final double radius;
  final Color color;
  const Glass({
    super.key,
    required this.child,
    required this.color,
    this.radius = 28,
  });
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(radius),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: .12),
          blurRadius: 24,
          offset: const Offset(0, 8),
        ),
      ],
    ),
    child: ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                color.withValues(alpha: .62),
                color.withValues(alpha: .44),
              ],
            ),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: Theme.of(context).colorScheme.outline
                  .withValues(alpha: .14),
            ),
          ),
          child: child,
        ),
      ),
    ),
  );
}

class SectionHead extends StatelessWidget {
  final String kicker, title;
  final Widget? action;
  const SectionHead(this.kicker, this.title, {super.key, this.action});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(24, 18, 24, 16),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 25,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -1,
                ),
              ),
            ],
          ),
        ),
        ?action,
      ],
    ),
  );
}

class EmptyPage extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final VoidCallback onAdd;
  const EmptyPage({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onAdd,
  });
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(32),
    child: Column(
      children: [
        const SizedBox(height: 20),
        Icon(
          icon,
          size: 48,
          color: Theme.of(context).colorScheme.primary.withValues(alpha: .55),
        ),
        const SizedBox(height: 20),
        Text(
          title,
          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),
        Text(
          subtitle,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurface
                .withValues(alpha: .55),
            height: 1.6,
          ),
        ),
        const SizedBox(height: 22),
        FilledButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.add_rounded),
          label: const LocalText('开始记录'),
        ),
      ],
    ),
  );
}

class FlipCard extends StatefulWidget {
  final Widget front, back;
  final bool reduced, swipeToFlip;
  final String semanticLabel;
  final ValueChanged<bool>? onFlipped;
  const FlipCard({
    super.key,
    required this.front,
    required this.back,
    this.reduced = false,
    this.swipeToFlip = true,
    this.semanticLabel = '票根',
    this.onFlipped,
  });
  @override
  State<FlipCard> createState() => _FlipCardState();
}

class _FlipCardState extends State<FlipCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 650),
  );
  bool back = false;
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void flip() {
    back = !back;
    widget.onFlipped?.call(back);
    controller.animateTo(
      back ? 1 : 0,
      duration: Duration(milliseconds: widget.reduced ? 0 : 650),
      curve: Curves.easeInOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: '翻转${widget.semanticLabel}，查看${back ? '正面' : '背面'}',
    child: GestureDetector(
      onTap: flip,
      onHorizontalDragEnd: widget.swipeToFlip ? (e) => flip() : null,
      child: AnimatedBuilder(
        animation: controller,
        builder: (context, child) {
          final angle = controller.value * math.pi;
          final second = controller.value > .5;
          return Transform(
            alignment: Alignment.center,
            transform: Matrix4.identity()
              ..setEntry(3, 2, .0015)
              ..rotateY(angle),
            child: Transform(
              alignment: Alignment.center,
              transform: Matrix4.identity()..rotateY(second ? math.pi : 0),
              child: second ? widget.back : widget.front,
            ),
          );
        },
      ),
    ),
  );
}

class TicketPaper extends StatelessWidget {
  final String from, to, code, date, price, passenger;
  final String slogan;
  final bool rail, back;
  final Color accent;
  final Color paperColor, inkColor, backColor, backInk;
  const TicketPaper({
    super.key,
    required this.from,
    required this.to,
    required this.code,
    required this.date,
    required this.price,
    required this.accent,
    this.paperColor = const Color(0xfffffefa),
    this.inkColor = const Color(0xff203b60),
    this.backColor = const Color(0xff37596a),
    this.backInk = Colors.white,
    this.passenger = '',
    this.slogan = '抵达之后，\n故事才刚开始。',
    this.rail = false,
    this.back = false,
  });
  @override
  Widget build(BuildContext context) => ClipPath(
    clipper: _TicketCut(),
    child: Container(
      decoration: BoxDecoration(
        color: back ? backColor : paperColor,
        borderRadius: BorderRadius.circular(22),
      ),
      padding: const EdgeInsets.all(24),
      child: DefaultTextStyle(
        style: TextStyle(color: back ? backInk : inkColor),
        child: back
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const LocalText(
                    'THE JOURNEY CONTINUES',
                    style: TextStyle(fontSize: 10, letterSpacing: 2),
                  ),
                  const Spacer(),
                  Text(
                    slogan,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 24,
                      height: 1.45,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(),
                  Row(
                    children: [
                      const Expanded(
                        child: LocalText(
                          '客行录 / 旅途珍藏',
                          style: TextStyle(fontSize: 11),
                        ),
                      ),
                      Icon(
                        rail ? Icons.train_rounded : Icons.flight_rounded,
                        color: backInk.withValues(alpha: .7),
                        size: 32,
                      ),
                    ],
                  ),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        rail
                            ? Icons.train_rounded
                            : Icons.flight_takeoff_rounded,
                        color: accent,
                        size: 24,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        rail ? 'RAILWAY JOURNAL' : 'BOARDING MEMORIES',
                        style: TextStyle(
                          color: accent,
                          fontSize: 9,
                          letterSpacing: 1.1,
                        ),
                      ),
                      const Spacer(),
                      const LocalText(
                        '客行录',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          from.isEmpty
                              ? '出发'
                              : from.replaceAll(
                                  RegExp(r'国际机场|机场|^[A-Z]{3} · '),
                                  '',
                                ),
                          style: const TextStyle(
                            fontSize: 23,
                            fontWeight: FontWeight.w600,
                          ),
                          maxLines: 2,
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        child: Icon(Icons.east_rounded, color: accent),
                      ),
                      Expanded(
                        child: Text(
                          to.isEmpty
                              ? '抵达'
                              : to.replaceAll(
                                  RegExp(r'国际机场|机场|^[A-Z]{3} · '),
                                  '',
                                ),
                          textAlign: TextAlign.right,
                          style: const TextStyle(
                            fontSize: 23,
                            fontWeight: FontWeight.w600,
                          ),
                          maxLines: 2,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        code.isEmpty ? '待填写' : code,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          letterSpacing: 2,
                        ),
                      ),
                      Text(date, style: const TextStyle(fontSize: 12)),
                    ],
                  ),
                  const Spacer(),
                  CustomPaint(
                    size: const Size(double.infinity, 1),
                    painter: _Dashes(accent.withValues(alpha: .35)),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        passenger.isEmpty ? '每一次抵达，都值得收藏' : passenger,
                        style: const TextStyle(fontSize: 10),
                      ),
                      Text(
                        price.isEmpty ? 'CNY —' : 'CNY $price',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 18,
                    child: CustomPaint(
                      size: const Size(double.infinity, 18),
                      painter: _Barcode(inkColor),
                    ),
                  ),
                ],
              ),
      ),
    ),
  );
}

class _TicketCut extends CustomClipper<Path> {
  @override
  Path getClip(Size s) {
    final base = Path()
      ..addRRect(
        RRect.fromRectAndRadius(Offset.zero & s, const Radius.circular(22)),
      );
    final holes = Path()
      ..addOval(Rect.fromCircle(center: Offset(0, s.height * .71), radius: 9))
      ..addOval(
        Rect.fromCircle(center: Offset(s.width, s.height * .71), radius: 9),
      );
    return Path.combine(PathOperation.difference, base, holes);
  }

  @override
  bool shouldReclip(_TicketCut old) => false;
}

class _Dashes extends CustomPainter {
  final Color color;
  _Dashes(this.color);
  @override
  void paint(Canvas c, Size s) {
    for (double x = 0; x < s.width; x += 8) {
      c.drawLine(Offset(x, 0), Offset(x + 4, 0), Paint()..color = color);
    }
  }

  @override
  bool shouldRepaint(_Dashes old) => old.color != color;
}

class _Barcode extends CustomPainter {
  final Color ink;
  _Barcode(this.ink);
  @override
  void paint(Canvas c, Size s) {
    for (double x = 0; x < s.width; x += 4) {
      c.drawRect(
        Rect.fromLTWH(x, 0, (x.toInt() % 3) + 1, s.height),
        Paint()..color = ink.withValues(alpha: .6),
      );
    }
  }

  @override
  bool shouldRepaint(_Barcode old) => old.ink != ink;
}

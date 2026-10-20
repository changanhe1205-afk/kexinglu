import 'i18n.dart';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'look.dart';

/// 我的 · 纸页组件
///
/// 这一页刻意不用 ListTile / ExpansionTile / Divider 那套系统默认长相：
/// 卡片是压边的纸页，分隔线是虚线的装订线，展开由自定义的箭头完成。
/// 颜色全部取自当前 [AppPalette]，所以 12 套主题和深浅色都能直接跟随。

class ProfilePaper extends StatelessWidget {
  final Widget child;
  final AppPalette palette;
  final EdgeInsetsGeometry padding;
  final double radius;
  final Color? color;

  const ProfilePaper({
    super.key,
    required this.child,
    required this.palette,
    this.padding = const EdgeInsets.all(18),
    this.radius = 26,
    this.color,
  });

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: padding,
    decoration: BoxDecoration(
      color: color ?? palette.paper,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(
        color: palette.ink.withValues(alpha: palette.dark ? .13 : .07),
      ),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: palette.dark ? .22 : .07),
          blurRadius: 22,
          offset: const Offset(0, 9),
        ),
      ],
    ),
    child: child,
  );
}

class ProfileSectionHead extends StatelessWidget {
  final String kicker;
  final String title;
  final AppPalette palette;
  final Widget? trailing;

  const ProfileSectionHead({
    super.key,
    required this.kicker,
    required this.title,
    required this.palette,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 0, 4, 0),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LocalText(
                kicker,
                style: TextStyle(
                  fontSize: 9,
                  height: 1.2,
                  letterSpacing: 2.4,
                  fontWeight: FontWeight.w600,
                  color: palette.accent.withValues(alpha: .78),
                ),
              ),
              const SizedBox(height: 7),
              LocalText(
                title,
                style: TextStyle(
                  fontSize: 24,
                  height: 1.1,
                  letterSpacing: -.9,
                  fontWeight: FontWeight.w600,
                  color: palette.ink,
                ),
              ),
            ],
          ),
        ),
        ?trailing,
      ],
    ),
  );
}

/// 装订线：一条短虚线，用来代替系统 Divider。
class DashedRule extends StatelessWidget {
  final AppPalette palette;
  final double dash;
  final double gap;
  final EdgeInsetsGeometry? margin;

  const DashedRule({
    super.key,
    required this.palette,
    this.dash = 4,
    this.gap = 5,
    this.margin,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: margin ?? EdgeInsets.zero,
    child: SizedBox(
      height: 1,
      width: double.infinity,
      child: CustomPaint(
        painter: _DashPainter(
          palette.ink.withValues(alpha: palette.dark ? .18 : .13),
          dash,
          gap,
        ),
      ),
    ),
  );
}

class _DashPainter extends CustomPainter {
  final Color color;
  final double dash;
  final double gap;

  _DashPainter(this.color, this.dash, this.gap);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1;
    for (double x = 0; x < size.width; x += dash + gap) {
      canvas.drawLine(
        Offset(x, .5),
        Offset(math.min(x + dash, size.width), .5),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_DashPainter old) =>
      old.color != color || old.dash != dash || old.gap != gap;
}

class ProfileIconBadge extends StatelessWidget {
  final IconData icon;
  final AppPalette palette;
  final double size;
  final Color? color;

  const ProfileIconBadge({
    super.key,
    required this.icon,
    required this.palette,
    this.size = 40,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final tone = color ?? palette.accent;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: tone.withValues(alpha: palette.dark ? .16 : .10),
        borderRadius: BorderRadius.circular(size * .32),
        border: Border.all(color: tone.withValues(alpha: .16)),
      ),
      child: Icon(icon, size: size * .46, color: tone),
    );
  }
}

/// 一行“可点”的档案条目：图标徽章 + 标题 + 说明 + 自定义尾部。
class ProfileActionRow extends StatelessWidget {
  final AppPalette palette;
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry padding;

  const ProfileActionRow({
    super.key,
    required this.palette,
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.padding = const EdgeInsets.symmetric(horizontal: 2, vertical: 14),
  });

  @override
  Widget build(BuildContext context) {
    final body = Padding(
      padding: padding,
      child: Row(
        children: [
          ProfileIconBadge(icon: icon, palette: palette),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LocalText(
                  title,
                  style: TextStyle(
                    fontSize: 14.5,
                    height: 1.3,
                    fontWeight: FontWeight.w600,
                    color: palette.ink,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    subtitle!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11.5,
                      height: 1.45,
                      color: palette.ink.withValues(alpha: .55),
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[const SizedBox(width: 10), trailing!],
        ],
      ),
    );
    if (onTap == null) return body;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        splashColor: palette.accent.withValues(alpha: .06),
        highlightColor: palette.accent.withValues(alpha: .04),
        child: body,
      ),
    );
  }
}

class ProfileStatData {
  final IconData icon;
  final String label;
  final int value;

  const ProfileStatData(this.icon, this.label, this.value);
}

/// 四个数字排成一条窄纸带，像旧车票上的里程栏。
class ProfileStatStrip extends StatelessWidget {
  final AppPalette palette;
  final List<ProfileStatData> items;

  const ProfileStatStrip({
    super.key,
    required this.palette,
    required this.items,
  });

  @override
  Widget build(BuildContext context) => ProfilePaper(
    palette: palette,
    padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 2),
    radius: 22,
    child: Row(
      children: [
        for (var i = 0; i < items.length; i++) ...[
          if (i > 0)
            Container(
              width: 1,
              height: 30,
              color: palette.ink.withValues(alpha: .08),
            ),
          Expanded(
            child: Column(
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      items[i].icon,
                      size: 13,
                      color: palette.accent.withValues(alpha: .85),
                    ),
                    const SizedBox(width: 5),
                    LocalText(
                      '${items[i].value}',
                      style: TextStyle(
                        fontSize: 21,
                        height: 1.1,
                        fontWeight: FontWeight.w600,
                        color: palette.ink,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 5),
                Text(
                  items[i].label,
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: .8,
                    color: palette.ink.withValues(alpha: .52),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    ),
  );
}

/// 头像：纸白内圈 + 手绘虚线外圈，压在封面与资料卡之间。
class ProfileAvatar extends StatelessWidget {
  final Widget child;
  final AppPalette palette;
  final double size;
  final VoidCallback? onTap;

  const ProfileAvatar({
    super.key,
    required this.child,
    required this.palette,
    this.size = 86,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) => Semantics(
    button: onTap != null,
    label: '头像',
    child: GestureDetector(
      onTap: onTap,
      child: SizedBox(
        width: size + 12,
        height: size + 12,
        child: Stack(
          alignment: Alignment.center,
          children: [
            CustomPaint(
              size: Size.square(size + 12),
              painter: _DashedRingPainter(
                palette.accent.withValues(alpha: .5),
              ),
            ),
            Container(
              width: size,
              height: size,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: palette.paper,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: .18),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: ClipOval(child: child),
            ),
          ],
        ),
      ),
    ),
  );
}

class _DashedRingPainter extends CustomPainter {
  final Color color;

  _DashedRingPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..strokeCap = StrokeCap.round;
    final rect = (Offset.zero & size).deflate(1.5);
    const count = 30;
    for (var i = 0; i < count; i++) {
      final start = i * (2 * math.pi / count);
      canvas.drawArc(rect, start, .105, false, paint);
    }
  }

  @override
  bool shouldRepaint(_DashedRingPainter old) => old.color != color;
}

class ProfileStatusPill extends StatelessWidget {
  final AppPalette palette;
  final String label;
  final Color tone;

  const ProfileStatusPill({
    super.key,
    required this.palette,
    required this.label,
    required this.tone,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
    decoration: BoxDecoration(
      color: tone.withValues(alpha: palette.dark ? .14 : .09),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: tone.withValues(alpha: .22)),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 5,
          height: 5,
          decoration: BoxDecoration(color: tone, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        LocalText(
          label,
          style: TextStyle(
            fontSize: 10,
            height: 1.2,
            fontWeight: FontWeight.w500,
            color: tone,
          ),
        ),
      ],
    ),
  );
}

class ProfileEditPill extends StatelessWidget {
  final AppPalette palette;
  final String label;
  final VoidCallback onTap;

  const ProfileEditPill({
    super.key,
    required this.palette,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Material(
    color: palette.accent.withValues(alpha: palette.dark ? .18 : .10),
    borderRadius: BorderRadius.circular(30),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(30),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.edit_outlined, size: 13, color: palette.accent),
            const SizedBox(width: 4),
            LocalText(
              label,
              style: TextStyle(
                fontSize: 11,
                height: 1.2,
                fontWeight: FontWeight.w600,
                color: palette.accent,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class ProfileSwitchRow extends StatelessWidget {
  final AppPalette palette;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const ProfileSwitchRow({
    super.key,
    required this.palette,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LocalText(
              title,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
                color: palette.ink,
              ),
            ),
            const SizedBox(height: 2),
            LocalText(
              subtitle,
              style: TextStyle(
                fontSize: 10.5,
                color: palette.ink.withValues(alpha: .5),
              ),
            ),
          ],
        ),
      ),
      Transform.scale(
        scale: .78,
        child: Switch(
          value: value,
          onChanged: onChanged,
          activeThumbColor: palette.accent,
          activeTrackColor: palette.accent.withValues(alpha: .38),
          inactiveThumbColor: palette.ink.withValues(alpha: .45),
          inactiveTrackColor: palette.ink.withValues(alpha: .12),
        ),
      ),
    ],
  );
}

class ProfileChoicePill extends StatelessWidget {
  final AppPalette palette;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const ProfileChoicePill({
    super.key,
    required this.palette,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Material(
    color: selected
        ? palette.accent.withValues(alpha: palette.dark ? .18 : .10)
        : palette.background.withValues(alpha: .6),
    borderRadius: BorderRadius.circular(20),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? palette.accent.withValues(alpha: .55)
                : palette.ink.withValues(alpha: .07),
          ),
        ),
        child: LocalText(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? palette.accent : palette.ink.withValues(alpha: .7),
          ),
        ),
      ),
    ),
  );
}

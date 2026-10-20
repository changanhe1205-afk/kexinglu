import 'i18n.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'backup.dart';
import 'look.dart';
import 'profile_ui.dart';
import 'store.dart';

/// 我的 · 二级页共用顶栏：返回 + 标题 + 小字眉题。
class ProfilePageHeader extends StatelessWidget {
  final String title;
  final String kicker;
  final AppPalette palette;

  const ProfilePageHeader({
    super.key,
    required this.title,
    required this.kicker,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
    child: Row(children: [
      Material(
        color: palette.paper,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: palette.ink.withValues(alpha: .08)),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => Navigator.pop(context),
          child: SizedBox(
            width: 40,
            height: 40,
            child: Icon(
              Icons.arrow_back_rounded,
              size: 19,
              color: palette.ink.withValues(alpha: .75),
            ),
          ),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LocalText(
              title,
              style: TextStyle(
                fontSize: 18,
                height: 1.2,
                fontWeight: FontWeight.w600,
                letterSpacing: -.4,
                color: palette.ink,
              ),
            ),
            const SizedBox(height: 3),
            LocalText(
              kicker,
              style: TextStyle(
                fontSize: 7.5,
                letterSpacing: 1.8,
                fontWeight: FontWeight.w600,
                color: palette.accent.withValues(alpha: .7),
              ),
            ),
          ],
        ),
      ),
    ]),
  );
}

/// 系统主题的放大选择卡：左边是主题的迷你预览，右边/下方是名称与选中态。
class ThemePreviewCard extends StatelessWidget {
  final AppPalette current;
  final AppPalette option;
  final bool selected;
  final VoidCallback onTap;

  const ThemePreviewCard({
    super.key,
    required this.current,
    required this.option,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: current.paper,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected
                ? current.accent
                : current.ink.withValues(alpha: .08),
            width: selected ? 2 : 1,
          ),
          boxShadow: selected
              ? [BoxShadow(color: current.accent.withValues(alpha: .22), blurRadius: 14, offset: const Offset(0, 6))]
              : null,
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            height: 56,
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: option.background,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: option.ink.withValues(alpha: .08)),
            ),
            child: Row(children: [
              Container(
                width: 34,
                height: 38,
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: option.paper,
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(height: 4, width: 16, decoration: BoxDecoration(
                      color: option.accent, borderRadius: BorderRadius.circular(2))),
                    const SizedBox(height: 5),
                    Container(height: 4, width: 13, decoration: BoxDecoration(
                      color: option.ink.withValues(alpha: .3), borderRadius: BorderRadius.circular(2))),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(height: 6, width: double.infinity, decoration: BoxDecoration(
                      color: option.ink.withValues(alpha: .75), borderRadius: BorderRadius.circular(3))),
                    const SizedBox(height: 7),
                    Container(height: 4, width: 40, decoration: BoxDecoration(
                      color: option.ink.withValues(alpha: .35), borderRadius: BorderRadius.circular(2))),
                    const SizedBox(height: 7),
                    Container(height: 12, width: 34, decoration: BoxDecoration(
                      color: option.accent, borderRadius: BorderRadius.circular(4))),
                  ],
                ),
              ),
            ]),
          ),
          const SizedBox(height: 10),
          Row(children: [
            Text(option.name, style: TextStyle(fontSize: 12, height: 1.2,
              fontWeight: FontWeight.w600, color: current.ink)),
            const Spacer(),
            Icon(
              selected ? Icons.check_circle_rounded : Icons.circle_outlined,
              size: 16,
              color: selected ? current.accent : current.ink.withValues(alpha: .3),
            ),
          ]),
        ]),
      ),
    ),
  );
}

class ProfileSettingsScreen extends StatefulWidget {
  final JournalStore store;
  const ProfileSettingsScreen({super.key, required this.store});
  @override State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  AppPalette get p => AppPalette.all[
    (widget.store.settings['theme'] as int? ?? 0).clamp(0, AppPalette.all.length - 1)];

  Future<void> pick(int i) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await widget.store.setting('theme', i);
      if (mounted) setState(() {});
    } catch (_) {
      messenger.showSnackBar(const SnackBar(content: LocalText('主题未保存，请重试')));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: p.background,
    body: SafeArea(
      child: Column(children: [
        ProfilePageHeader(title: '设置', kicker: 'PREFERENCES', palette: p),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 34),
            children: [
              ProfileSectionHead(kicker: 'APPEARANCE', title: '系统主题', palette: p,
                trailing: Text(p.name, style: TextStyle(fontSize: 11, color: p.ink.withValues(alpha: .5)))),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                initialValue: AppLanguage.current,
                decoration: const InputDecoration(labelText: '语言 / Language'),
                items: [for (final entry in AppLanguage.names.entries)
                  DropdownMenuItem(value: entry.key, child: Text(entry.value))],
                onChanged: (value) async {
                  if (value == null) return;
                  await widget.store.setting('language', value);
                  if (mounted) setState(() {});
                }),
              const SizedBox(height: 16),
              LocalText('选一个喜欢的配色，立即生效并记住。',
                style: TextStyle(fontSize: 11.5, height: 1.5, color: p.ink.withValues(alpha: .5))),
              const SizedBox(height: 14),
              LayoutBuilder(builder: (context, constraints) {
                final width = (constraints.maxWidth - 12) / 2;
                return Wrap(spacing: 12, runSpacing: 12, children: [
                  for (var i = 0; i < AppPalette.all.length; i++)
                    SizedBox(
                      width: width,
                      child: ThemePreviewCard(
                        current: p,
                        option: AppPalette.all[i],
                        selected: AppPalette.all[i].name == p.name,
                        onTap: () => pick(i),
                      ),
                    ),
                ]);
              }),
              const SizedBox(height: 28),
              ProfileSectionHead(kicker: 'MOTION', title: '动效', palette: p),
              const SizedBox(height: 12),
              ProfilePaper(
                palette: p,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: ProfileSwitchRow(
                  palette: p,
                  title: '减少动态效果',
                  subtitle: '减少轮播与翻转动画',
                  value: widget.store.settings['reduced'] == true,
                  onChanged: (v) async {
                    final messenger = ScaffoldMessenger.of(context);
                    try {
                      await widget.store.setting('reduced', v);
                      if (mounted) setState(() {});
                    } catch (_) {
                      messenger.showSnackBar(const SnackBar(content: LocalText('设置未保存，请重试')));
                    }
                  },
                ),
              ),
              const SizedBox(height: 12),
              LocalText('关闭后，票夹轮播、卡片翻转等动画会静止，页面切换更轻快。',
                style: TextStyle(fontSize: 10.5, height: 1.6, color: p.ink.withValues(alpha: .42))),
            ],
          ),
        ),
      ]),
    ),
  );
}

class ProfileBackupScreen extends StatelessWidget {
  final JournalStore store;
  const ProfileBackupScreen({super.key, required this.store});

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.all[
      (store.settings['theme'] as int? ?? 0).clamp(0, AppPalette.all.length - 1)];
    return Scaffold(
      backgroundColor: p.background,
      body: SafeArea(
        child: Column(children: [
          ProfilePageHeader(title: '数据备份', kicker: 'BACKUP', palette: p),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 34),
              children: [
                const SizedBox(height: 8),
                LocalText('把记录连同照片收进一份文件，需要时再导回。',
                  style: TextStyle(fontSize: 13, height: 1.6, color: p.ink.withValues(alpha: .6))),
                const SizedBox(height: 18),
                ProfilePaper(
                  palette: p,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: ProfileActionRow(
                    palette: p,
                    icon: Icons.save_alt_rounded,
                    title: '导出本地备份',
                    subtitle: '生成一份包含照片的 JSON 文件，可保存到任意位置',
                    onTap: () => backupData(context, store),
                    trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
                  ),
                ),
                const SizedBox(height: 12),
                ProfilePaper(
                  palette: p,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: ProfileActionRow(
                    palette: p,
                    icon: Icons.restore_rounded,
                    title: '从备份导入',
                    subtitle: '合并记录，不会清空现有内容',
                    onTap: () => backupData(context, store, restore: true),
                    trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
                  ),
                ),
                const SizedBox(height: 20),
                Padding(
                  padding: const EdgeInsets.fromLTRB(6, 0, 6, 0),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(Icons.shield_outlined, size: 14, color: p.ink.withValues(alpha: .35)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: LocalText('备份文件只保存在你选择的位置，客行录不会上传或接触它。建议导出后另存一份到电脑或云端盘。',
                        style: TextStyle(fontSize: 11.5, height: 1.7, color: p.ink.withValues(alpha: .45))),
                    ),
                  ]),
                ),
              ],
            ),
          ),
        ]),
      ),
    );
  }
}

class ProfileAboutScreen extends StatelessWidget {
  const ProfileAboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final palette = Theme.of(context).brightness == Brightness.dark
        ? AppPalette.all.firstWhere((e) => e.dark, orElse: () => AppPalette.all[6])
        : AppPalette.all.first;
    return Scaffold(
      backgroundColor: palette.background,
      body: SafeArea(
        child: Column(children: [
          ProfilePageHeader(title: '关于', kicker: 'ABOUT', palette: palette),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 34),
              children: [
                Center(
                  child: Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      color: palette.accent.withValues(alpha: .10),
                      borderRadius: BorderRadius.circular(26),
                    ),
                    child: Center(
                      child: SvgPicture.asset('assets/app-mark.svg', width: 46, height: 46,
                        colorFilter: ColorFilter.mode(palette.accent, BlendMode.srcIn)),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                LocalText('客行录', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 30, height: 1.1, letterSpacing: -1,
                    fontWeight: FontWeight.w700, color: palette.ink)),
                const SizedBox(height: 6),
                LocalText('KEXINGLU · TRAVEL JOURNAL', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 9, letterSpacing: 2.4, fontWeight: FontWeight.w600,
                    color: palette.accent.withValues(alpha: .75))),
                const SizedBox(height: 18),
                Center(child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: palette.background.withValues(alpha: .6),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: palette.ink.withValues(alpha: .07)),
                  ),
                  child: LocalText('Android · 1.0.0', style: TextStyle(fontSize: 11,
                    fontWeight: FontWeight.w500, color: palette.ink.withValues(alpha: .65))),
                )),
                const SizedBox(height: 24),
                LocalText('把旅途与日常收进书里。', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 15, height: 1.6, fontWeight: FontWeight.w500, color: palette.ink)),
                const SizedBox(height: 6),
                LocalText('记录地点、票根、食光、影视与手账。', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, height: 1.7, color: palette.ink.withValues(alpha: .55))),
                const SizedBox(height: 22),
                ProfilePaper(
                  palette: palette,
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    LocalText('关于数据与隐私', style: TextStyle(fontSize: 13,
                      fontWeight: FontWeight.w600, color: palette.ink)),
                    const SizedBox(height: 8),
                    LocalText('资料默认只保存在本机；登录后可手动同步到你的账号。卸载前请先备份重要内容。',
                      style: TextStyle(fontSize: 12, height: 1.7, color: palette.ink.withValues(alpha: .5))),
                  ]),
                ),
                const SizedBox(height: 28),
                LocalText('客行录 · 本地珍藏', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 10, letterSpacing: 1.6, color: palette.ink.withValues(alpha: .38))),
              ],
            ),
          ),
        ]),
      ),
    );
  }
}

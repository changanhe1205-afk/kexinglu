import 'i18n.dart';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'account_screen.dart';
import 'cloud_account.dart';
import 'cloud_sync.dart';
import 'look.dart';
import 'profile_pages.dart';
import 'profile_ui.dart';
import 'store.dart';

const profileCovers = {'lakeside.png': '湖畔', 'forest.svg': '林间', 'sea.svg': '海岸', 'sunset.svg': '日落', 'dunes.svg': '沙丘', 'stars.svg': '星夜'};
Widget profileImage(String path, {BoxFit fit = BoxFit.cover}) {
  if (path.startsWith('preset:')) {
    final name = path.substring(7);
    final safe = profileCovers.containsKey(name) ? name : 'lakeside.png';
    return safe.endsWith('.svg') ? SvgPicture.asset('assets/backgrounds/$safe', fit: fit)
      : Image.asset('assets/backgrounds/$safe', fit: fit);
  }
  return Image.file(File(path), fit: fit, cacheWidth: 1200,
    errorBuilder: (_, _, _) => const ColoredBox(color: Color(0xff9ebbb5), child: Center(child: Icon(Icons.person_outline, size: 40))));
}

/// Profile is separate from journal records; account-scoped cache prevents mixing users.
class ProfileRepository {
  final JournalStore store;
  final String? uid;
  ProfileRepository(this.store, this.uid);
  String get key => 'personal_profile:${uid ?? 'guest'}';
  Map<String, dynamic> get local => Map<String, dynamic>.from(store.settings[key] as Map? ?? {});
  Future<Map<String, dynamic>> load() async {
    if (uid == null || local['pending'] == true) return local;
    final cloud = CloudAccount.instance;
    if (cloud.uid != uid) return local;
    try {
      final user = await cloud.client!.auth.getUser().timeout(const Duration(seconds: 8));
      final raw = user.user?.userMetadata?['kexinglu_profile'];
      if (raw is! Map || cloud.uid != uid) return local;
      final next = Map<String, dynamic>.from(raw);
      final sync = CloudSync(store, owner: uid);
      for (final field in ['avatar', 'cover']) {
        final value = next[field];
        if (value is Map) {
          try {next[field] = await sync.asset(value, true);} catch (_) {next[field] = local[field] ?? ''; next['${field}_remote'] = value;}
        }
      }
      if (cloud.uid != uid) return local;
      await store.setting(key, next);
      return next;
    } catch (_) {return local;}
  }
  Future<bool> save(Map<String, dynamic> value) async {
    final next = {...value, 'pending': uid != null};
    await store.setting(key, next); // Keep edits even if uploading fails.
    if (uid == null) return true;
    final cloud = CloudAccount.instance;
    if (cloud.uid != uid) return false;
    try {
      final remote = {...value}..remove('pending');
      final sync = CloudSync(store, owner: uid);
      for (final field in ['avatar','cover']) {
        final path = remote[field];
        if ((path == null || path == '') && remote['${field}_remote'] is Map) {remote[field] = remote.remove('${field}_remote'); continue;}
        remote.remove('${field}_remote');
        if (path is String && path.isNotEmpty && !path.startsWith('preset:')) remote[field] = await sync.asset(path, false);
      }
      if (cloud.uid != uid) return false;
      await cloud.client!.auth.updateUser(UserAttributes(data: {'kexinglu_profile': remote}));
      if (cloud.uid != uid) return false;
      await store.setting(key, {...value, 'pending': false});
      return true;
    } catch (_) { return false; }
  }
}

class PersonalProfile extends StatefulWidget {
  final JournalStore store;
  final AppPalette palette;
  const PersonalProfile({super.key, required this.store, required this.palette});
  @override State<PersonalProfile> createState() => _PersonalProfileState();
}

class _PersonalProfileState extends State<PersonalProfile> {
  late final repo = ProfileRepository(widget.store, CloudAccount.instance.uid);
  Map<String, dynamic> data = {};
  bool uploading = false;

  @override void initState() {
    super.initState(); data = repo.local;
    repo.load().then((v) {if (mounted) setState(() {data = v;});});
  }

  Future<void> edit() async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => ProfileEditor(repository: repo)));
    if (mounted) setState(() {data = repo.local;});
  }

  Future<void> retryUpload() async {
    if (uploading) return;
    setState(() => uploading = true);
    try {
      final ok = await repo.save(data);
      if (!mounted) return;
      setState(() {data = repo.local; uploading = false;});
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? '个人资料已同步' : '资料保留在本机，云端暂时不可用')));
    } catch (_) {
      if (!mounted) return;
      setState(() => uploading = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('同步未完成，资料仍保留在本机')));
    }
  }

  Widget _cover(AppPalette p, String cover, int total) => SizedBox(
    height: 300,
    child: Stack(fit: StackFit.expand, children: [
      ClipRRect(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(36)),
        child: profileImage(cover),
      ),
      ClipRRect(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(36)),
        child: const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter,
          colors: [Color(0x66000000), Color(0x00000000), Color(0x88000000)],
          stops: [0, .42, 1]))),
      ),
      Positioned(top: 16, left: 20, child: _fileBadge()),
      Positioned(top: 14, right: 18, child: _coverEditButton()),
      if (total > 0) Positioned(right: 26, bottom: 58, child: _stamp(total)),
    ]),
  );

  Widget _fileBadge() => Container(
    padding: const EdgeInsets.fromLTRB(10, 6, 11, 6),
    decoration: BoxDecoration(
      color: Colors.black.withValues(alpha: .30),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: Colors.white.withValues(alpha: .18)),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 5, height: 5, decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .8), shape: BoxShape.circle)),
      const SizedBox(width: 7),
      LocalText('客行录 · 旅人档案', style: TextStyle(fontSize: 10, height: 1.2,
        letterSpacing: .8, color: Colors.white.withValues(alpha: .92))),
    ]),
  );

  Widget _coverEditButton() => Tooltip(
    message: '编辑资料与背景',
    child: Material(
      color: Colors.black.withValues(alpha: .30),
      shape: CircleBorder(side: BorderSide(color: Colors.white.withValues(alpha: .22))),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: edit,
        child: const SizedBox(width: 42, height: 42,
          child: Icon(Icons.tune_rounded, size: 19, color: Colors.white)),
      ),
    ),
  );

  Widget _stamp(int total) => Transform.rotate(
    angle: -.14,
    child: Container(
      width: 78, height: 78,
      decoration: BoxDecoration(shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withValues(alpha: .55), width: 1.2)),
      child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        LocalText('珍藏', style: TextStyle(fontSize: 9, height: 1.2, letterSpacing: 4,
          color: Colors.white.withValues(alpha: .78))),
        LocalText('$total', style: TextStyle(fontSize: 23, height: 1.05, fontWeight: FontWeight.w700,
          color: Colors.white, fontFeatures: const [FontFeature.tabularFigures()])),
        LocalText('MEMORIES', style: TextStyle(fontSize: 6.5, height: 1.2, letterSpacing: 1.2,
          color: Colors.white.withValues(alpha: .58))),
      ])),
    ),
  );

  Widget _identity(AppPalette p, String nickname, String signature,
      String avatar, bool signed) {
    final pending = data['pending'] == true;
    return SizedBox(
      width: double.infinity,
      child: Stack(clipBehavior: Clip.none, children: [
      ProfilePaper(
        palette: p,
        radius: 28,
        padding: const EdgeInsets.fromLTRB(20, 18, 18, 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(height: 56),
          Text(nickname, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 28, height: 1.1, letterSpacing: -1,
              fontWeight: FontWeight.w700, color: p.ink)),
          const SizedBox(height: 8),
          ProfileStatusPill(palette: p, label: signed ? '已登录 · 个人资料可同步' : '本地珍藏 · 未登录',
            tone: signed ? p.accent : p.ink.withValues(alpha: .55)),
          const SizedBox(height: 9),
          Text(signature, maxLines: 3, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 13, height: 1.65, color: p.ink.withValues(alpha: .62))),
          if (pending) ...[
            const SizedBox(height: 12),
            Material(color: Colors.transparent, child: InkWell(
              onTap: retryUpload,
              borderRadius: BorderRadius.circular(14),
              child: Container(
                padding: const EdgeInsets.fromLTRB(12, 9, 10, 9),
                decoration: BoxDecoration(
                  color: p.accent.withValues(alpha: .07),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: p.accent.withValues(alpha: .24)),
                ),
                child: Row(children: [
                  Icon(Icons.cloud_upload_outlined, size: 17, color: p.accent),
                  const SizedBox(width: 9),
                  Expanded(child: LocalText('个人资料待上传 · 点击重试',
                    style: TextStyle(fontSize: 11.5, height: 1.3,
                      fontWeight: FontWeight.w500, color: p.ink.withValues(alpha: .8)))),
                  if (uploading) SizedBox(width: 14, height: 14,
                    child: CircularProgressIndicator(strokeWidth: 1.6, color: p.accent))
                  else Icon(Icons.refresh_rounded, size: 16, color: p.accent.withValues(alpha: .8)),
                ]),
              ),
            )),
          ],
        ]),
      ),
      Positioned(left: 18, top: -46, child: ProfileAvatar(
        palette: p, size: 86, onTap: edit,
        child: avatar.isEmpty
          ? ColoredBox(color: p.background, child: Icon(Icons.person_outline, color: p.accent, size: 38))
          : profileImage(avatar),
      )),
      Positioned(right: 16, top: 14,
        child: ProfileEditPill(palette: p, label: '编辑资料', onTap: edit)),
    ]),
    );
  }

  Widget _tools(AppPalette p, bool signed) => ProfilePaper(
    palette: p,
    radius: 28,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    child: Column(children: [
      ProfileActionRow(
        palette: p, icon: Icons.cloud_outlined, title: '账号与同步',
        subtitle: signed ? '已登录 · 管理同步资料' : '登录后同步你的旅行与收藏',
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => AccountScreen(store: widget.store))),
        trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
      ),
      DashedRule(palette: p),
      ProfileActionRow(
        palette: p, icon: Icons.tune_rounded, title: '设置', subtitle: '主题、动效与显示',
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProfileSettingsScreen(store: widget.store))),
        trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
      ),
      DashedRule(palette: p),
      ProfileActionRow(
        palette: p, icon: Icons.inventory_2_outlined, title: '数据备份', subtitle: '导出或导入本机记录',
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProfileBackupScreen(store: widget.store))),
        trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
      ),
      DashedRule(palette: p),
      ProfileActionRow(
        palette: p, icon: Icons.info_outline_rounded, title: '关于', subtitle: '版本 1.0.0 · 本地珍藏',
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfileAboutScreen())),
        trailing: Icon(Icons.chevron_right_rounded, size: 21, color: p.ink.withValues(alpha: .35)),
      ),
    ]),
  );

  Widget _footer(AppPalette p) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 28, 16, 8),
    child: Column(children: [
      LocalText('客行录 · 本地珍藏', style: TextStyle(fontSize: 10, letterSpacing: 1.6,
        color: p.ink.withValues(alpha: .38))),
      const SizedBox(height: 5),
      LocalText('资料只保存在这台设备，登录后可手动同步。', textAlign: TextAlign.center,
        style: TextStyle(fontSize: 10.5, height: 1.6, color: p.ink.withValues(alpha: .34))),
    ]),
  );

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final signed = repo.uid != null;
    final avatar = '${data['avatar'] ?? ''}';
    final cover = '${data['cover'] ?? 'preset:lakeside.png'}';
    final nickname = '${data['nickname'] ?? ''}'.isEmpty
      ? (signed ? '旅行者' : '我的客行录') : '${data['nickname']}';
    final signature = '${data['signature'] ?? ''}'.isEmpty
      ? '把日子，慢慢收藏。' : '${data['signature']}';
    final stats = [
      ProfileStatData(Icons.confirmation_number_outlined, '票夹', widget.store.of('ticket').length),
      ProfileStatData(Icons.explore_outlined, '旅途', widget.store.of('travel').length),
      ProfileStatData(Icons.restaurant_outlined, '食光', widget.store.of('food').length),
      ProfileStatData(Icons.movie_filter_outlined, '影视', widget.store.of('movie').length),
    ];
    final total = stats.fold<int>(0, (sum, item) => sum + item.value);

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        Stack(children: [
          Positioned(top: 0, left: 0, right: 0, child: _cover(p, cover.isEmpty ? 'preset:lakeside.png' : cover, total)),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 258, 20, 0),
            child: Column(children: [
              _identity(p, nickname, signature, avatar, signed),
              const SizedBox(height: 16),
              ProfileStatStrip(palette: p, items: stats),
              const SizedBox(height: 30),
              ProfileSectionHead(kicker: 'PACK & PREFERENCES', title: '行囊与设置', palette: p,
                trailing: LocalText('LOCAL ONLY', style: TextStyle(fontSize: 8.5,
                  letterSpacing: 1.8, fontWeight: FontWeight.w600, color: p.ink.withValues(alpha: .32)))),
              const SizedBox(height: 14),
              _tools(p, signed),
              _footer(p),
              const SizedBox(height: 128),
            ]),
          ),
        ]),
      ],
    );
  }
}

class ProfileEditor extends StatefulWidget {
  final ProfileRepository repository;
  const ProfileEditor({super.key, required this.repository});
  @override State<ProfileEditor> createState() => _ProfileEditorState();
}

class _ProfileEditorState extends State<ProfileEditor> {
  late final initial = widget.repository.local;
  late final nickname = TextEditingController(text: '${initial['nickname'] ?? ''}');
  late final signature = TextEditingController(text: '${initial['signature'] ?? ''}');
  late String avatar = '${initial['avatar'] ?? ''}', cover = '${initial['cover'] ?? 'preset:lakeside.png'}',
    birthday = '${initial['birthday'] ?? ''}', gender = '${initial['gender'] ?? '不公开'}';
  bool busy = false;
  @override void dispose() {nickname.dispose(); signature.dispose(); super.dispose();}

  Future<void> image(bool isAvatar) async {
    try {
      final photo = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: isAvatar ? 640 : 1800, imageQuality: 85);
      if (photo == null) return;
      final path = await JournalStore.keepPhoto(photo.path);
      if (mounted) setState(() {isAvatar ? avatar = path : cover = path;});
    } catch (_) {if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('图片导入失败，请重新选择')));}
  }

  Future<void> save() async {
    if (busy) return;
    setState(() {busy = true;});
    try {
      final ok = await widget.repository.save({...initial, 'nickname': nickname.text.trim(), 'signature': signature.text.trim(),
        'avatar': avatar, 'cover': cover, 'birthday': birthday, 'gender': gender});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? '个人资料已保存' : '已保存到本机，个人资料待上传')));
      Navigator.pop(context);
    } catch (_) {if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('保存失败，请重试，编辑内容仍保留')));}
    finally {if (mounted) setState(() {busy = false;});}
  }

  InputDecoration _field(String label, AppPalette p) => InputDecoration(
    labelText: label,
    filled: true,
    fillColor: p.background.withValues(alpha: .55),
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
    contentPadding: const EdgeInsets.fromLTRB(14, 16, 14, 16),
  );

  Widget _topBar(AppPalette p) => Padding(
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
        LocalText('编辑资料', style: TextStyle(fontSize: 18, height: 1.2,
          fontWeight: FontWeight.w600, letterSpacing: -.4, color: p.ink)),
        const SizedBox(height: 3),
        LocalText('PROFILE & COVER', style: TextStyle(fontSize: 7.5, letterSpacing: 1.8,
          fontWeight: FontWeight.w600, color: p.accent.withValues(alpha: .7))),
      ])),
      TextButton(
        onPressed: busy ? null : save,
        style: TextButton.styleFrom(
          foregroundColor: p.accent,
          backgroundColor: p.accent.withValues(alpha: .1),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
        child: Text(busy ? '保存中…' : '保存', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
      ),
    ]),
  );

  Widget _coverPreview(AppPalette p) => SizedBox(
    height: 190,
    child: ClipRRect(
      borderRadius: BorderRadius.circular(26),
      child: Stack(fit: StackFit.expand, children: [
        profileImage(cover.isEmpty ? 'preset:lakeside.png' : cover),
        const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter,
          colors: [Color(0x00000000), Color(0x99000000)],
          stops: [.45, 1]))),
        Positioned(left: 16, bottom: 14, child: Row(children: [
          Icon(Icons.wallpaper_outlined, size: 14, color: Colors.white.withValues(alpha: .82)),
          const SizedBox(width: 6),
          LocalText('个性背景', style: TextStyle(fontSize: 11, letterSpacing: 1,
            color: Colors.white.withValues(alpha: .9))),
        ])),
        Positioned(right: 12, bottom: 10, child: Material(
          color: Colors.black.withValues(alpha: .35),
          shape: const StadiumBorder(),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => image(false),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(11, 7, 12, 7),
              child: Row(children: [
                const Icon(Icons.add_photo_alternate_outlined, size: 14, color: Colors.white),
                const SizedBox(width: 5),
                LocalText('更换背景', style: TextStyle(fontSize: 10.5,
                  color: Colors.white.withValues(alpha: .92))),
              ]),
            ),
          ),
        )),
      ]),
    ),
  );

  Widget _avatarRow(AppPalette p) => Row(children: [
    ProfileAvatar(
      palette: p, size: 72, onTap: () => image(true),
      child: avatar.isEmpty
        ? ColoredBox(color: p.background, child: Center(child: Icon(Icons.add_a_photo_outlined, size: 28, color: p.accent)))
        : profileImage(avatar),
    ),
    const SizedBox(width: 12),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      LocalText('头像', style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600, color: p.ink)),
      const SizedBox(height: 3),
      LocalText('从相册选择一张照片', style: TextStyle(fontSize: 10.5, height: 1.4,
        color: p.ink.withValues(alpha: .5))),
    ])),
    TextButton(
      onPressed: () => image(true),
      style: TextButton.styleFrom(foregroundColor: p.accent,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8)),
      child: const LocalText('选择头像', style: TextStyle(fontSize: 11.5)),
    ),
  ]);

  Widget _basicCard(AppPalette p) => ProfilePaper(
    palette: p,
    padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
    child: Column(children: [
      TextField(
        controller: nickname, maxLength: 30,
        decoration: _field('昵称', p),
        style: TextStyle(fontSize: 14, color: p.ink),
      ),
      const SizedBox(height: 2),
      TextField(
        controller: signature, maxLength: 160, minLines: 2, maxLines: 4,
        decoration: _field('个性签名', p),
        style: TextStyle(fontSize: 14, height: 1.5, color: p.ink),
      ),
      const SizedBox(height: 4),
      _birthdayRow(p),
      const SizedBox(height: 8),
      Padding(
        padding: const EdgeInsets.fromLTRB(4, 0, 4, 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          LocalText('性别', style: TextStyle(fontSize: 10.5, color: p.ink.withValues(alpha: .5))),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final option in ['不公开', '男', '女', '其他'])
              ProfileChoicePill(palette: p, label: option, selected: gender == option,
                onTap: () => setState(() => gender = option)),
          ]),
        ]),
      ),
    ]),
  );

  Widget _birthdayRow(AppPalette p) {
    final has = birthday.isNotEmpty;
    return Material(color: Colors.transparent, child: InkWell(
      onTap: () async {
        final now = DateTime.now();
        final existing = DateTime.tryParse(birthday);
        final date = await showDatePicker(context: context,
          initialDate: existing != null && !existing.isAfter(now) ? existing : DateTime(2000),
          firstDate: DateTime(1900), lastDate: now);
        if (date != null && mounted) {
          setState(() {birthday = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';});
        }
      },
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
        child: Row(children: [
          ProfileIconBadge(icon: Icons.cake_outlined, palette: p, size: 34),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            LocalText('出生年月日', style: TextStyle(fontSize: 10.5, color: p.ink.withValues(alpha: .5))),
            const SizedBox(height: 2),
            Text(has ? birthday : '未设置', style: TextStyle(fontSize: 13,
              fontWeight: FontWeight.w500, color: p.ink)),
          ])),
          if (has) IconButton(
            tooltip: '清除生日',
            visualDensity: VisualDensity.compact,
            onPressed: () => setState(() {birthday = '';}),
            icon: Icon(Icons.close_rounded, size: 16, color: p.ink.withValues(alpha: .4)),
          ),
          Icon(Icons.chevron_right_rounded, size: 18, color: p.ink.withValues(alpha: .3)),
        ]),
      ),
    ));
  }

  Widget _coverThumb(AppPalette p, String key, String name) {
    final selected = cover == 'preset:$key';
    return GestureDetector(
      onTap: () => setState(() => cover = 'preset:$key'),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 108, height: 78,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: selected ? p.accent : p.ink.withValues(alpha: .08),
            width: selected ? 2 : 1),
          boxShadow: selected ? [BoxShadow(color: p.accent.withValues(alpha: .22),
            blurRadius: 12, offset: const Offset(0, 5))] : null,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: Stack(fit: StackFit.expand, children: [
            profileImage('preset:$key'),
            const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
              begin: Alignment.topCenter, end: Alignment.bottomCenter,
              colors: [Color(0x00000000), Color(0x99000000)],
              stops: [.4, 1]))),
            Positioned(left: 9, bottom: 7, child: Text(name, style: const TextStyle(
              fontSize: 10.5, fontWeight: FontWeight.w600, color: Colors.white))),
            if (selected) const Positioned(top: 6, right: 6,
              child: Icon(Icons.check_circle_rounded, size: 15, color: Colors.white)),
          ]),
        ),
      ),
    );
  }

  Widget _coverPicker(AppPalette p) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    LocalText('选一张预设，或从相册上传自己的照片。',
      style: TextStyle(fontSize: 11, height: 1.5, color: p.ink.withValues(alpha: .5))),
    const SizedBox(height: 12),
    SizedBox(
      height: 80,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: profileCovers.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final entry = profileCovers.entries.elementAt(i);
          return _coverThumb(p, entry.key, entry.value);
        },
      ),
    ),
    const SizedBox(height: 6),
    TextButton.icon(
      onPressed: () => image(false),
      style: TextButton.styleFrom(foregroundColor: p.accent),
      icon: const Icon(Icons.add_photo_alternate_outlined, size: 17),
      label: const LocalText('上传自己的背景图', style: TextStyle(fontSize: 12)),
    ),
  ]);

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.all[(widget.repository.store.settings['theme'] as int? ?? 0)
        .clamp(0, AppPalette.all.length - 1)];
    return Scaffold(
      backgroundColor: p.background,
      body: SafeArea(
        child: AbsorbPointer(
          absorbing: busy,
          child: Column(children: [
            _topBar(p),
            Expanded(child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 34),
              children: [
                _coverPreview(p),
                const SizedBox(height: 14),
                _avatarRow(p),
                const SizedBox(height: 22),
                ProfileSectionHead(kicker: 'BASICS', title: '基本信息', palette: p),
                const SizedBox(height: 12),
                _basicCard(p),
                const SizedBox(height: 22),
                ProfileSectionHead(kicker: 'COVER', title: '个性背景', palette: p),
                const SizedBox(height: 10),
                _coverPicker(p),
                const SizedBox(height: 22),
                SizedBox(
                  width: double.infinity, height: 52,
                  child: FilledButton(
                    onPressed: busy ? null : save,
                    style: FilledButton.styleFrom(
                      backgroundColor: p.accent,
                      foregroundColor: p.dark ? p.background : Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    child: Text(busy ? '保存中…' : '保存资料',
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                  ),
                ),
                const SizedBox(height: 12),
                Center(child: LocalText('资料保存在本机，登录后会自动同步到你的账号。',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 10.5, height: 1.6, color: p.ink.withValues(alpha: .38)))),
              ],
            )),
          ]),
        ),
      ),
    );
  }
}

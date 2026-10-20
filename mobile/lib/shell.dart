import 'i18n.dart';
import 'adaptive_layout.dart';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import 'atlas.dart';
import 'cloud_account.dart';
import 'profile_screen.dart';
import 'nav_icon.dart';
import 'editor.dart';
import 'look.dart';
import 'home_screen.dart';
import 'notebook.dart';
import 'store.dart';
import 'ticket_screen.dart';
import 'collection_screen.dart';

class JournalShell extends StatefulWidget {
  final JournalStore store;
  final AtlasData atlas;
  final AppPalette palette;
  const JournalShell({
    super.key,
    required this.store,
    required this.atlas,
    required this.palette,
  });
  @override
  State<JournalShell> createState() => _JournalShellState();
}

class _JournalShellState extends State<JournalShell> {
  int selected = 0;
  final navPulses = List.filled(5, 0);
  String collectionKind = 'movie';
  Entry? recovered;
  JournalStore get store => widget.store;
  AppPalette get p => widget.palette;
  bool get reduced =>
      store.settings['reduced'] == true ||
      MediaQuery.disableAnimationsOf(context);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => recoverPhoto());
  }

  Future<void> recoverPhoto() async {
    if (!Platform.isAndroid) return;
    try {
      final response = await ImagePicker().retrieveLostData();
      final pending = store.settings['pending_photo'];
      if (response.files?.isNotEmpty == true && pending is Map) {
        final image = await JournalStore.keepPhoto(response.files!.first.path);
        recovered = Entry(
          pending['id'],
          pending['kind'],
          Map<String, dynamic>.from(pending['data'])..['image'] = image,
        );
        if (mounted) setState(() {});
      }
      if (response.exception == null) {
        await store.setting('pending_photo', null);
      }
    } catch (_) {
      /* Keep the recovery metadata if the platform cannot retrieve it yet. */
    }
  }

  void go(int n) {
    if (n == selected) {setState(() {navPulses[n]++;}); return;}
    if (!reduced) HapticFeedback.selectionClick();
    setState(() {selected = n; navPulses[n]++;});
  }

  Future<void> edit(String kind, {Entry? entry}) =>
      editEntry(context, store, widget.atlas, kind, entry: entry);
  void books() => Navigator.push(
    context,
    MaterialPageRoute(
      builder: (c) => BookShelf(store: store, palette: p, reduced: reduced),
    ),
  );
  Widget photo(Entry e, {double? height}) => e.text('image').isEmpty
      ? Container(
          height: height,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [p.accent.withValues(alpha: .18), p.paper],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Center(
            child: Icon(
              e.kind == 'movie'
                  ? Icons.movie_outlined
                  : Icons.restaurant_rounded,
              size: 44,
              color: p.accent.withValues(alpha: .5),
            ),
          ),
        )
      : Image.file(
          File(e.text('image')),
          height: height,
          width: double.infinity,
          fit: BoxFit.cover,
          cacheWidth: 900,
          errorBuilder: (c, e, s) => Container(
            height: height,
            color: p.paper,
            child: const Icon(Icons.image_not_supported_outlined),
          ),
        );
  List<dynamic> travelPhotos(Entry e) {
    final values = <dynamic>[];
    final seen = <String>{};
    void add(dynamic v) {
      if (v == null || v == '') return;
      if (seen.add(v.toString())) values.add(v);
    }
    add(e.data['image']);
    for (final item in e.data['photos'] as List? ?? []) {
      if (item is Map) add(item['image']);
    }
    return values;
  }

  Widget travelPhoto(dynamic value, {double height = 112, double? width}) {
    final pending = value is! String;
    Widget placeholder() => Container(
      height: height, width: width, color: p.accent.withValues(alpha: .07),
      child: Center(child: Icon(pending ? Icons.cloud_download_outlined : Icons.landscape_outlined,
        color: p.accent)),
    );
    return ClipRRect(borderRadius: BorderRadius.circular(14), child: pending
      ? placeholder()
      : Image.file(File(value), height: height, width: width, fit: BoxFit.cover,
          cacheWidth: 900, errorBuilder: (_, error, stack) => placeholder()));
  }

  Widget noteCard(Entry e) {
    final photos = travelPhotos(e);
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 0, 24, 12),
      child: Material(color: p.paper, borderRadius: BorderRadius.circular(20),
        clipBehavior: Clip.antiAlias,
        child: InkWell(onTap: () => detail(e), child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (photos.isNotEmpty) ...[
              travelPhoto(photos.first, width: 88, height: 108),
              const SizedBox(width: 14),
            ],
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(e.text('title'), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              LocalText('${e.text('city').isEmpty ? e.text('place') : e.text('city')} · ${e.text('date')}',
                style: TextStyle(fontSize: 11, color: p.accent)),
              if (e.text('note').isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(e.text('note'), maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, height: 1.5, color: p.ink.withValues(alpha: .65))),
              ],
              if (photos.isNotEmpty) ...[
                const SizedBox(height: 8),
                LocalText('${photos.length} 张照片${photos.any((v) => v is Map) ? ' · 部分待同步' : ''}',
                  style: TextStyle(fontSize: 11, color: p.accent)),
              ],
            ])),
          ]),
        )),
      ),
    );
  }
  Future<void> detail(Entry e) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (c) => FractionallySizedBox(
        heightFactor: .88,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 30),
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    e.text('title'),
                    style: const TextStyle(
                      fontSize: 27,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () {
                    Navigator.pop(c);
                    edit(e.kind, entry: e);
                  },
                  icon: const Icon(Icons.edit_outlined),
                ),
              ],
            ),
            LocalText(
              '${e.text('date')} · ${e.text('city')}${e.text('place')}',
              style: TextStyle(color: p.accent),
            ),
            const SizedBox(height: 20),
            if (e.kind == 'travel')
              ...travelPhotos(e).map((value) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(children: [
                  travelPhoto(value, height: 240, width: double.infinity),
                  if (value is Map) const Padding(padding: EdgeInsets.all(8),
                    child: LocalText('照片待下载，请在账号与同步中重试')),
                ]),
              ))
            else if (e.text('image').isNotEmpty)
              ClipRRect(borderRadius: BorderRadius.circular(18), child: photo(e, height: 240)),
            const SizedBox(height: 20),
            Text(
              e.text('note').isEmpty ? '这一页，留给以后的故事。' : e.text('note'),
              style: const TextStyle(fontSize: 16, height: 1.9),
            ),
            const SizedBox(height: 28),
            TextButton.icon(
              onPressed: () => remove(e, c),
              icon: const Icon(Icons.delete_outline_rounded),
              label: const LocalText('删除这条记录'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> remove(Entry e, BuildContext sheet) async {
    final yes = await showDialog<bool>(
      context: sheet,
      builder: (c) => AlertDialog(
        title: const LocalText('删除这条记录？'),
        content: const LocalText('确认后可在底部提示中撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const LocalText('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: const LocalText('删除'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await store.remove(e);
      if (sheet.mounted) Navigator.pop(sheet);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const LocalText('记录已删除'),
            action: SnackBarAction(
              label: '撤销',
              onPressed: () async {
                try {
                  await store.save(e);
                } catch (_) {
                  if (mounted) {
                    ScaffoldMessenger.of(
                      context,
                    ).showSnackBar(const SnackBar(content: LocalText('恢复失败，请重试。')));
                  }
                }
              },
            ),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('删除未成功，原记录已保留。')));
      }
    }
  }

  Widget stat(String value, String label, VoidCallback tap) => InkWell(
    onTap: tap,
    borderRadius: BorderRadius.circular(18),
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w400),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(color: p.ink.withValues(alpha: .55), fontSize: 11),
          ),
        ],
      ),
    ),
  );
  Widget home() => JournalHome(store: store, atlas: widget.atlas, palette: p,
    onTravel: () => go(1), onTickets: () => go(2), onBooks: books,
    onFood: () {collectionKind = 'food'; go(3);},
    onMovies: () {collectionKind = 'movie'; go(3);},
    recovery: recovered == null ? null : MaterialBanner(
      content: const LocalText('已找回刚才选择的图片'), actions: [TextButton(onPressed: () {
        final e = recovered!; setState(() => recovered = null); edit(e.kind, entry: e);
      }, child: const LocalText('继续编辑'))]),
  );
  Widget travel() => JournalWorkspace(
    mapIndex: 1,
    children: [
      SectionHead(
        'PLACES & MEMORIES',
        '去过的地方',
        action: IconButton.filled(
          onPressed: () => edit('travel'),
          icon: const Icon(Icons.add_rounded),
        ),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: SizedBox(
          height: 280,
          child: RouteMap(
            atlas: widget.atlas,
            records: store.of('travel'),
            mode: 'travel',
            accent: p.accent,
            dark: p.dark,
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(26, 14, 26, 0),
        child: Row(children: [
          LocalText(
            '${store.of('travel').length} 段旅程',
            style: TextStyle(fontSize: 12, color: p.accent),
          ),
          const Spacer(),
          LocalText('地图可拖动 · 双指缩放 · 点右下角全屏',
            style: TextStyle(fontSize: 10, color: p.ink.withValues(alpha: .42))),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 18),
        child: Material(
          color: p.accent.withValues(alpha: p.dark ? .18 : .09),
          borderRadius: BorderRadius.circular(22),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: books,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: p.paper,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(Icons.menu_book_rounded, size: 24, color: p.accent),
                  ),
                  const SizedBox(width: 13),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const LocalText(
                          '旅行手账',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 3),
                        LocalText(
                          '把照片、文字和贴纸排成书页，像一本书一样翻阅',
                          style: TextStyle(fontSize: 10.5, height: 1.4, color: p.ink.withValues(alpha: .55)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      LocalText('${store.of('book').length} 本',
                        style: TextStyle(fontSize: 11, color: p.accent)),
                      const SizedBox(height: 2),
                      Icon(Icons.chevron_right_rounded, size: 20,
                        color: p.accent.withValues(alpha: .7)),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      if (store.of('travel').isEmpty)
        EmptyPage(
          icon: Icons.explore_outlined,
          title: '故事从一个地点开始',
          subtitle: '记录文字和照片，让地图慢慢亮起来。',
          onAdd: () => edit('travel'),
        )
      else
        ...store.of('travel').map(noteCard),
    ],
  );
  Widget profile() => ListenableBuilder(listenable: CloudAccount.instance, builder: (context, _) =>
    PersonalProfile(key: ValueKey(CloudAccount.instance.uid ?? 'guest'), store: store, palette: p));
  @override
  Widget build(BuildContext context) {
    final pages = [
      home(),
      travel(),
      TicketScreen(
        store: store,
        atlas: widget.atlas,
        palette: p,
        reduced: reduced,
        onEdit: ({Entry? entry, String initialMode = 'air'}) => editEntry(
          context,
          store,
          widget.atlas,
          'ticket',
          entry: entry,
          initialMode: initialMode,
        ),
      ),
      CollectionScreen(
        key: ValueKey(collectionKind), initialKind: collectionKind,
        store: store,
        palette: p,
        reduced: reduced,
        photo: photo,
        card: noteCard,
        onEdit: edit,
        onDetail: detail,
      ),
      profile(),
    ];
    final nav = Row(
      children: List.generate(5, (i) {
        const icons = [
          Icons.home_outlined,
          Icons.explore_outlined,
          Icons.confirmation_number_outlined,
          Icons.bookmarks_outlined,
          Icons.person_outline_rounded,
        ];
        const labels = ['首页', '旅途', '票夹', '收藏', '我的'];
        return Expanded(
          child: Semantics(
            selected: selected == i,
            button: true,
            label: labels[i],
            child: InkWell(
              onTap: () => go(i),
              borderRadius: BorderRadius.circular(24),
              child: AnimatedContainer(
                duration: Duration(milliseconds: reduced ? 0 : 250),
                margin: const EdgeInsets.all(6),
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: selected == i
                      ? p.accent.withValues(alpha: .12)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(22),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    AnimatedNavIcon(
                      icon: icons[i], index: i, pulse: navPulses[i], reduced: reduced,
                      color: selected == i
                          ? p.accent
                          : p.ink.withValues(alpha: .45),
                    ),
                    const SizedBox(height: 3),
                    LocalText(
                      labels[i],
                      style: TextStyle(
                        fontSize: 9,
                        color: selected == i
                            ? p.accent
                            : p.ink.withValues(alpha: .5),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }),
    );
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: p.dark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
      child: Scaffold(
        extendBody: true,
        resizeToAvoidBottomInset: false,
        body: Stack(
          fit: StackFit.expand,
          children: [
            if (selected == 0) Positioned.fill(child: Image.asset('assets/backgrounds/lakeside.png', fit: BoxFit.cover,
              color: p.background.withValues(alpha: p.dark ? .9 : .18), colorBlendMode: BlendMode.srcATop)),
            SafeArea(
              bottom: false,
              child: AnimatedSwitcher(
                duration: Duration(milliseconds: reduced ? 0 : 300),
                switchInCurve: Curves.easeOutCubic,
                transitionBuilder: (child, a) => FadeTransition(
                  opacity: a,
                  child: SlideTransition(
                    position: Tween(
                      begin: const Offset(0, .018),
                      end: Offset.zero,
                    ).animate(a),
                    child: child,
                  ),
                ),
                child: KeyedSubtree(
                  key: ValueKey(selected),
                  child: Align(alignment: Alignment.topCenter,
                    child: ConstrainedBox(
                      constraints: BoxConstraints(maxWidth: selected == 3 || selected == 4 ? 760 : 1440),
                      child: pages[selected],
                    )),
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: SafeArea(
                key: const ValueKey('main-floating-navigation'),
                top: false,
                maintainBottomViewPadding: true,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: Center(child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 680),
                    child: Glass(
                    color: p.paper,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 76),
                      child: nav,
                    ),
                  ))),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

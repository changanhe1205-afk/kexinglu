import 'i18n.dart';
import 'dart:async';

import 'package:flutter/material.dart';

import 'look.dart';
import 'store.dart';

class CollectionScreen extends StatefulWidget {
  final String initialKind;
  final JournalStore store;
  final AppPalette palette;
  final bool reduced;
  final Widget Function(Entry, {double? height}) photo;
  final Widget Function(Entry) card;
  final Future<void> Function(String, {Entry? entry}) onEdit;
  final Future<void> Function(Entry) onDetail;
  const CollectionScreen({
    super.key,
    this.initialKind = 'movie',
    required this.store,
    required this.palette,
    required this.reduced,
    required this.photo,
    required this.card,
    required this.onEdit,
    required this.onDetail,
  });
  @override
  State<CollectionScreen> createState() => _CollectionScreenState();
}

class _CollectionScreenState extends State<CollectionScreen>
    with WidgetsBindingObserver {
  late String kind = widget.initialKind;
  final controller = PageController(viewportFraction: .82);
  Timer? timer;
  bool interacting = false, resumed = true;
  final flipped = <String>{};
  double position = 0;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    controller.addListener(() {
      if (mounted) setState(() => position = controller.page ?? 0);
    });
    timer = Timer.periodic(const Duration(seconds: 6), (_) {
      final n = widget.store.of('movie').length;
      if (!mounted ||
          !resumed ||
          widget.reduced ||
          interacting ||
          kind != 'movie' ||
          flipped.isNotEmpty ||
          n < 2 ||
          !controller.hasClients ||
          !(ModalRoute.of(context)?.isCurrent ?? false)) {
        return;
      }
      controller.animateToPage(
        ((controller.page ?? 0).round() + 1) % n,
        duration: const Duration(milliseconds: 750),
        curve: Curves.easeInOutCubic,
      );
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    resumed = state == AppLifecycleState.resumed;
  }

  @override
  void dispose() {
    timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    controller.dispose();
    super.dispose();
  }

  Future<void> remove(Entry e) async {
    final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: const LocalText('删除这条收藏？'), actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const LocalText('取消')),
        TextButton(onPressed: () => Navigator.pop(c, true), child: const LocalText('删除'))]));
    if (yes != true) return;
    try {
      await widget.store.remove(e);
      flipped.remove(e.id);
      if (mounted) {ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: const LocalText('收藏已删除'),
        action: SnackBarAction(label: '撤销', onPressed: () async {
          try {await widget.store.save(e);} catch (_) {
            if (mounted) {ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('恢复失败，请重试')));}
          }
        })));}
    } catch (_) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('删除失败，记录仍保留'))); }
  }
  Widget collectionCard(Entry e) {
    final p = widget.palette;
    final desktop = e.data['_desktop'] as Map? ?? {};
    final basic = <String, String>{
      '日期': e.text('date'), '评分': e.text('rating').isEmpty ? '' : '${e.text('rating')} / 5',
      if (e.kind == 'movie') ...{'类别': e.text('category'), '导演': '${desktop['director'] ?? ''}',
        '主演': '${desktop['actors'] ?? desktop['cast'] ?? ''}', '类型': '${desktop['genre'] ?? ''}',
        '地区': '${desktop['country'] ?? ''}', '年份': '${desktop['year'] ?? ''}'},
      if (e.kind == 'food') ...{'地点': e.text('place'), '价格': e.text('price')},
    }..removeWhere((_, v) => v.isEmpty);
    Widget paper(Widget child) => Container(clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: p.paper, borderRadius: BorderRadius.circular(24),
        border: Border.all(color: p.accent.withValues(alpha: .12)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .08), blurRadius: 16, offset: const Offset(0, 6))]), child: child);
    return FlipCard(key: ValueKey('collection-${e.id}'), semanticLabel: '收藏',
      reduced: widget.reduced, swipeToFlip: false,
      onFlipped: (back) => setState(() {back ? flipped.add(e.id) : flipped.remove(e.id);}),
      front: paper(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(child: widget.photo(e)), Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(e.text('title'), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8), LocalText('${e.text('date')}  ·  轻触查看感悟', style: TextStyle(fontSize: 11, color: p.accent)),
        ]))])),
      back: paper(Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(e.text('title'), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
        const SizedBox(height: 14),
        Expanded(child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final row in basic.entries) Padding(padding: const EdgeInsets.only(bottom: 7), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 52, child: Text(row.key, style: TextStyle(fontSize: 12, color: p.ink.withValues(alpha: .55)))),
            Expanded(child: Text(row.value, style: const TextStyle(fontSize: 12, height: 1.5)))])),
          const Divider(height: 26), Text(e.kind == 'movie' ? '观看感悟' : '食光感想', style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8), Text(e.text('note').isEmpty ? '还没有写下感想，点击编辑补充。' : e.text('note'), style: const TextStyle(height: 1.7, fontSize: 14)),
        ]))),
        const SizedBox(height: 8), Row(children: [
          TextButton.icon(onPressed: () => widget.onEdit(e.kind, entry: e), icon: const Icon(Icons.edit_outlined, size: 16), label: const LocalText('编辑')),
          const Spacer(), IconButton(tooltip: '删除收藏', onPressed: () => remove(e), icon: const Icon(Icons.delete_outline_rounded, size: 19))]),
        LocalText('轻触空白处翻回封面', style: TextStyle(fontSize: 10, color: p.ink.withValues(alpha: .5))),
      ]))));
  }
  @override
  Widget build(BuildContext context) {
    final list = widget.store.of(kind);
    final deck = SizedBox(
      height: 440,
      child: Listener(
        onPointerDown: (_) => interacting = true,
        onPointerUp: (_) => interacting = false,
        onPointerCancel: (_) => interacting = false,
        child: PageView.builder(
          controller: controller,
          itemCount: list.length,
          itemBuilder: (c, i) {
            final e = list[i], d = (i - position).clamp(-1.0, 1.0);
            return Transform(
              alignment: Alignment.center,
              transform: Matrix4.identity()
                ..setEntry(3, 2, .0015)
                ..rotateY(widget.reduced ? 0 : d * -.18)
                ..translateByDouble(0, d.abs() * 18, 0, 1),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 9,
                  vertical: 10,
                ),
                child: collectionCard(e),
              ),
            );
          },
        ),
      ),
    );
    return ListView(
      padding: const EdgeInsets.only(bottom: 130),
      children: [
        SectionHead(
          'THE THINGS THAT STAY',
          '生活的余韵',
          action: IconButton.filled(
            onPressed: () => widget.onEdit(kind),
            icon: const Icon(Icons.add_rounded),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: 'movie',
                label: LocalText('影视收藏'),
                icon: Icon(Icons.movie_outlined),
              ),
              ButtonSegment(
                value: 'food',
                label: LocalText('食光小记'),
                icon: Icon(Icons.restaurant_outlined),
              ),
            ],
            selected: {kind},
            onSelectionChanged: (s) => setState(() {kind = s.first; flipped.clear();}),
          ),
        ),
        const SizedBox(height: 28),
        if (list.isEmpty)
          EmptyPage(
            icon: kind == 'movie'
                ? Icons.theaters_outlined
                : Icons.local_dining_outlined,
            title: kind == 'movie' ? '留住散场后的感受' : '记得那一口的味道',
            subtitle: '从一张照片、一句话开始。',
            onAdd: () => widget.onEdit(kind),
          )
        else if (kind == 'food')
          ...list.map((e) => Padding(padding: const EdgeInsets.fromLTRB(24, 0, 24, 18),
            child: SizedBox(height: 380, child: collectionCard(e))))
        else ...[
          deck,
          const SizedBox(height: 18),
          Center(
            child: LocalText(
              '轻触翻面查看感悟 · 左右滑动切换',
              style: const TextStyle(fontSize: 11),
            ),
          ),
        ],
      ],
    );
  }
}

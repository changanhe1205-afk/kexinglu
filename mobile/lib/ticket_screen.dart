import 'i18n.dart';
import 'airlines.dart';
import 'ticket_colors.dart';

import 'package:flutter/material.dart';

import 'atlas.dart';
import 'look.dart';
import 'store.dart';

class TicketScreen extends StatefulWidget {
  final JournalStore store;
  final AtlasData atlas;
  final AppPalette palette;
  final bool reduced;
  final void Function({Entry? entry, String initialMode}) onEdit;
  const TicketScreen({
    super.key,
    required this.store,
    required this.atlas,
    required this.palette,
    required this.reduced,
    required this.onEdit,
  });
  @override
  State<TicketScreen> createState() => _TicketScreenState();
}

class _TicketScreenState extends State<TicketScreen> {
  String mode = 'air';
  final controller = PageController(viewportFraction: .88);
  double page = 0;
  @override
  void initState() {
    super.initState();
    controller.addListener(() {
      if (mounted) setState(() => page = controller.page ?? 0);
    });
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  TicketPaper paper(Entry e, {bool back = false}) => TicketPaper(
    from: e.text('from'),
    to: e.text('to'),
    code: e.text('code'),
    date: e.text('date'),
    price: e.text('price'),
    passenger: e.text('passenger'),
    slogan: mode == 'air'
        ? (airlineSlogan(e.text('airline')) ?? '抵达之后，\n故事才刚开始。')
        : '抵达之后，\n故事才刚开始。',
    accent: TicketColors.fromData(e.data).ink,
    paperColor: TicketColors.fromData(e.data).paper,
    inkColor: TicketColors.fromData(e.data).ink,
    backColor: TicketColors.fromData(e.data).back,
    backInk: TicketColors.fromData(e.data).backInk,
    rail: mode == 'rail',
    back: back,
  );
  Future<void> remove(Entry e, BuildContext sheet) async {
    final yes = await showDialog<bool>(
      context: sheet,
      builder: (d) => AlertDialog(
        title: const LocalText('删除这张票根？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d, false),
            child: const LocalText('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(d, true),
            child: const LocalText('删除'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await widget.store.remove(e);
      if (sheet.mounted) Navigator.pop(sheet);
    } catch (_) {
      if (sheet.mounted) {
        ScaffoldMessenger.of(sheet)
            .showSnackBar(const SnackBar(content: LocalText('删除失败，请重试。')));
      }
    }
  }

  Future<void> open(Entry e) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (c) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 10),
            SizedBox(
              height: 330,
              child: FlipCard(
                front: paper(e),
                back: paper(e, back: true),
                reduced: widget.reduced,
              ),
            ),
            const SizedBox(height: 18),
            const LocalText('轻点或左右滑动翻看背面', style: TextStyle(fontSize: 11)),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Navigator.pop(c);
                      widget.onEdit(entry: e);
                    },
                    icon: const Icon(Icons.edit_outlined),
                    label: const LocalText('编辑票根'),
                  ),
                ),
                const SizedBox(width: 12),
                IconButton(
                  onPressed: () => remove(e, c),
                  icon: const Icon(Icons.delete_outline_rounded),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = widget.store
        .of('ticket')
        .where((e) => e.text('mode') == mode)
        .toList();
    final p = widget.palette;
    final unresolved = items
        .where(
          (e) =>
              widget.atlas.locate(e.text('from'), mode) == null ||
              widget.atlas.locate(e.text('to'), mode) == null,
        )
        .length;
    return ListView(
      padding: const EdgeInsets.only(bottom: 130),
      children: [
        SectionHead(
          'A COLLECTION OF ARRIVALS',
          '每一次抵达',
          action: IconButton.filled(
            onPressed: () => widget.onEdit(initialMode: mode),
            icon: const Icon(Icons.add_rounded),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: 'air',
                label: LocalText('飞机'),
                icon: Icon(Icons.flight_rounded),
              ),
              ButtonSegment(
                value: 'rail',
                label: LocalText('高铁 / 火车'),
                icon: Icon(Icons.train_rounded),
              ),
            ],
            selected: {mode},
            onSelectionChanged: (v) {
              setState(() => mode = v.first);
              if (controller.hasClients) controller.jumpToPage(0);
            },
          ),
        ),
        const SizedBox(height: 20),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: SizedBox(
            height: 240,
            child: RouteMap(
              atlas: widget.atlas,
              records: items,
              selected: items.isEmpty
                  ? null
                  : items[page.round().clamp(0, items.length - 1)].id,
              mode: mode,
              accent: p.accent,
              dark: p.dark,
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(26, 14, 26, 8),
          child: LocalText(
            '${items.length} 张票根 · ${items.length - unresolved} 条轨迹${unresolved > 0 ? ' · $unresolved 张待定位' : ''}',
            style: TextStyle(fontSize: 11, color: p.accent),
          ),
        ),
        if (items.isEmpty)
          EmptyPage(
            icon: mode == 'air'
                ? Icons.flight_takeoff_rounded
                : Icons.train_outlined,
            title: '把旅途留成一张票',
            subtitle: '添加票根后，地图会自动连起出发与抵达。',
            onAdd: () => widget.onEdit(initialMode: mode),
          )
        else
          SizedBox(
            height: 320,
            child: PageView.builder(
              controller: controller,
              itemCount: items.length,
              itemBuilder: (context, i) {
                final d = (i - page).clamp(-1.0, 1.0);
                return Transform(
                  alignment: Alignment.center,
                  transform: Matrix4.identity()
                    ..setEntry(3, 2, .001)
                    ..rotateY(widget.reduced ? 0 : d * -.12)
                    ..scaleByDouble(1 - d.abs() * .05, 1 - d.abs() * .05, 1, 1),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 7,
                      vertical: 12,
                    ),
                    child: GestureDetector(
                      onTap: () => open(items[i]),
                      child: paper(items[i]),
                    ),
                  ),
                );
              },
            ),
          ),
        if (items.isNotEmpty)
          const Center(
            child: LocalText('左右滑动收藏 · 点击翻看票根', style: TextStyle(fontSize: 10)),
          ),
      ],
    );
  }
}

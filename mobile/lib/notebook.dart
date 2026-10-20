import 'i18n.dart';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'look.dart';
import 'store.dart';

const bookStyles = [
  ('纸上旅途', 0xfff6f0df, 0xff865a42, false),
  ('海岸活页', 0xffedf5ef, 0xff367c78, false),
  ('复古牛皮', 0xffe7d2ad, 0xff72553c, false),
  ('蔷薇压花', 0xffffedf0, 0xffa85f77, false),
  ('黑白影集', 0xfff5f4ef, 0xff303c3c, false),
  ('夜行拾光', 0xff293c44, 0xff99bfb3, true),
  ('晨雾蓝', 0xffeaf1f6, 0xff3b5a75, false),
  ('苔原绿', 0xffeef2e6, 0xff4f6b45, false),
  ('落日橘', 0xfffbeade, 0xffa85a32, false),
  ('樱花粉', 0xfffdeef2, 0xff9c5c74, false),
  ('咖啡棕', 0xfff0e4d6, 0xff6b4a35, false),
  ('极简白', 0xfffbfaf7, 0xff2f3a38, false),
];
const stickers = [
  '✦',
  '✧',
  '☀',
  '☁',
  '☾',
  '❀',
  '✿',
  '♡',
  '♥',
  '★',
  '☆',
  '❋',
  '🍃',
  '🌿',
  '🌼',
  '🌷',
  '🌻',
  '🌵',
  '🍋',
  '🍒',
  '🍓',
  '☕',
  '🍵',
  '🥐',
  '🍰',
  '📷',
  '🎞',
  '✈',
  '🚆',
  '🧳',
  '🏕',
  '⛺',
  '🌊',
  '🐚',
  '🦋',
  '🐈',
  '📮',
  '🎫',
  '🧭',
  '🎧',
  '📚',
  '🗝',
];
Map<String, dynamic> element(
  String text, {
  String kind = 'text',
  double x = .12,
  double y = .12,
  double size = 24,
}) => {
  'id': JournalStore.newId(),
  'kind': kind,
  'text': text,
  'x': x,
  'y': y,
  'size': size,
  'rotation': 0.0,
  'width': kind == 'image' ? .55 : .76,
};

class BookShelf extends StatelessWidget {
  final JournalStore store;
  final AppPalette palette;
  final bool reduced;
  const BookShelf({
    super.key,
    required this.store,
    required this.palette,
    required this.reduced,
  });
  void open(BuildContext context, Entry book, {bool fresh = false}) =>
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (c) => NotebookEditor(
            store: store,
            book: book,
            palette: palette,
            reduced: reduced,
            fresh: fresh,
          ),
        ),
      );
  void create(BuildContext context, List<Entry> source) {
    final pages = source.isEmpty
        ? [
            {'elements': <dynamic>[]},
          ]
        : source
              .map(
                (e) => {
                  'elements': [
                    element(e.text('title'), size: 28),
                    element(
                      '${e.text('city')} / ${e.text('date')}',
                      y: .22,
                      size: 12,
                    ),
                    if (e.text('image').isNotEmpty)
                      element(e.text('image'), kind: 'image', y: .31),
                    element(
                      e.text('note'),
                      y: e.text('image').isNotEmpty ? .65 : .34,
                      size: 16,
                    ),
                  ],
                },
              )
              .toList();
    open(
      context,
      Entry(JournalStore.newId(), 'book', {
        'title': source.length == 1
            ? '${source.first.text('city')}手记'
            : '我的旅行手账',
        'style': 0,
        'pages': pages,
      }),
      fresh: true,
    );
  }

  Future<void> choose(BuildContext context) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (c) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          children: [
            const ListTile(
              title: LocalText(
                '从哪里开始这一册？',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.note_add_outlined),
              title: const LocalText('新建空白手账'),
              subtitle: const LocalText('每一页都由你自由设计'),
              onTap: () {
                Navigator.pop(c);
                create(context, []);
              },
            ),
            if (store.of('travel').isNotEmpty) ...[
              ListTile(
                leading: const Icon(Icons.public_rounded),
                title: const LocalText('全部旅行汇总'),
                onTap: () {
                  Navigator.pop(c);
                  create(context, store.of('travel'));
                },
              ),
              const Divider(),
              ...store
                  .of('travel')
                  .map(
                    (e) => ListTile(
                      leading: const Icon(Icons.place_outlined),
                      title: Text(e.text('title')),
                      subtitle: Text(e.text('city')),
                      onTap: () {
                        Navigator.pop(c);
                        create(context, [e]);
                      },
                    ),
                  ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const LocalText('旅行手账'),
      actions: [
        IconButton(
          onPressed: () => choose(context),
          icon: const Icon(Icons.add_rounded),
        ),
      ],
    ),
    body: ListenableBuilder(
      listenable: store,
      builder: (c, child) {
        final books = store.of('book');
        return books.isEmpty
            ? EmptyPage(
                icon: Icons.auto_stories_outlined,
                title: '给回忆一册纸页',
                subtitle: '空白创作、单次旅程或全部足迹。\n每一页都可以重新排版。',
                onAdd: () => choose(context),
              )
            : GridView.builder(
                padding: const EdgeInsets.all(24),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 20,
                  mainAxisSpacing: 28,
                  childAspectRatio: .68,
                ),
                itemCount: books.length,
                itemBuilder: (c, i) {
                  final b = books[i],
                      style =
                          bookStyles[(b.data['style'] as int? ?? 0) %
                              bookStyles.length];
                  return GestureDetector(
                    onTap: () => open(context, b),
                    child: Transform(
                      alignment: Alignment.center,
                      transform: Matrix4.identity()
                        ..setEntry(3, 2, .001)
                        ..rotateY(-.12),
                      child: Container(
                        decoration: BoxDecoration(
                          color: Color(style.$3),
                          borderRadius: const BorderRadius.horizontal(
                            left: Radius.circular(4),
                            right: Radius.circular(14),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: .16),
                              blurRadius: 18,
                              offset: const Offset(7, 12),
                            ),
                          ],
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 10,
                              color: Colors.black.withValues(alpha: .13),
                            ),
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.all(18),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const LocalText(
                                      '客 行 录',
                                      style: TextStyle(
                                        color: Colors.white60,
                                        fontSize: 10,
                                      ),
                                    ),
                                    const Spacer(),
                                    Text(
                                      b.text('title'),
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 23,
                                        height: 1.5,
                                      ),
                                    ),
                                    const Spacer(),
                                    LocalText(
                                      '${(b.data['pages'] as List).length} 页 / ${style.$1}',
                                      style: const TextStyle(
                                        color: Colors.white70,
                                        fontSize: 9,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              );
      },
    ),
  );
}

class NotebookEditor extends StatefulWidget {
  final JournalStore store;
  final Entry book;
  final AppPalette palette;
  final bool reduced, fresh;
  const NotebookEditor({
    super.key,
    required this.store,
    required this.book,
    required this.palette,
    required this.reduced,
    this.fresh = false,
  });
  @override
  State<NotebookEditor> createState() => _NotebookEditorState();
}

class _NotebookEditorState extends State<NotebookEditor> {
  late Entry book = widget.book.copy();
  late bool editing = widget.fresh, dirty = widget.fresh;
  bool busy = false, leaving = false;
  final controller = PageController(viewportFraction: .92);
  final canvasKey = GlobalKey();
  double position = 0;
  int page = 0;
  String? selected;
  Offset gestureOrigin = Offset.zero, gestureFocal = Offset.zero;
  double gestureRotation = 0, gestureSize = 24, gestureWidth = .55;
  List<dynamic> get pages => book.data['pages'];
  List<dynamic> get elements => pages[page]['elements'];
  int get styleIndex => (book.data['style'] as int? ?? 0) % bookStyles.length;
  Map<String, dynamic>? get item {
    for (final e in elements) {
      if (e['id'] == selected) return e;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    controller.addListener(() {
      if (mounted) setState(() => position = controller.page ?? 0);
    });
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void change(VoidCallback action) {
    setState(() {
      action();
      dirty = true;
    });
  }

  void append(Map<String, dynamic> e) {
    change(() {
      elements.add(e);
      selected = e['id'];
    });
    if (!widget.reduced) HapticFeedback.selectionClick();
  }

  Future<void> finish() async {
    if (busy) return;
    if (dirty) {
      final result = await showDialog<String>(
        context: context,
        builder: (c) => AlertDialog(
          title: const LocalText('这一页，保存下来吗？'),
          content: const LocalText('放弃修改会保留之前保存的原稿。'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, 'stay'),
              child: const LocalText('继续编辑'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(c, 'discard'),
              child: const LocalText('放弃修改'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(c, 'save'),
              child: const LocalText('保存退出'),
            ),
          ],
        ),
      );
      if (result == null || result == 'stay') return;
      if (result == 'save' && !await save()) return;
    }
    if (mounted) {
      setState(() => leaving = true);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) Navigator.pop(context);
      });
    }
  }

  Future<bool> save() async {
    if (busy) return false;
    setState(() => busy = true);
    try {
      await widget.store.save(book);
      if (mounted) {
        setState(() {
          dirty = false;
          busy = false;
        });
      }
      return true;
    } catch (_) {
      if (mounted) {
        setState(() => busy = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('保存未成功，内容仍保留在编辑器中。')));
      }
      return false;
    }
  }

  Future<void> text({bool title = false}) async {
    final target = item;
    final c = TextEditingController(
      text: title ? book.text('title') : target?['text'] ?? '记下此刻',
    );
    final value = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title ? '手账名称' : '编辑文字'),
        content: TextField(
          controller: c,
          autofocus: true,
          maxLines: title ? 1 : 5,
          decoration: const InputDecoration(hintText: '写下你想留下的文字'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d),
            child: const LocalText('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(d, c.text),
            child: const LocalText('完成'),
          ),
        ],
      ),
    );
    c.dispose();
    if (value == null || value.trim().isEmpty) return;
    if (title) {
      change(() => book.data['title'] = value.trim());
    } else if (target != null && target['kind'] == 'text') {
      change(() => target['text'] = value);
    } else {
      append(element(value));
    }
  }

  Future<void> photo() async {
    try {
      final picked = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        maxWidth: 2000,
        imageQuality: 88,
      );
      if (picked == null) return;
      final path = await JournalStore.keepPhoto(picked.path);
      if (mounted) append(element(path, kind: 'image', y: .3));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('图片未导入，请重试。')));
      }
    }
  }

  void drop(DragTargetDetails<String> d) {
    final box = canvasKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null) return;
    final pos = box.globalToLocal(d.offset);
    append(
      element(
        d.data,
        kind: 'sticker',
        x: (pos.dx / box.size.width).clamp(0, .8),
        y: (pos.dy / box.size.height).clamp(0, .8),
        size: 42,
      ),
    );
  }

  Future<void> export() async {
    try {
      const esc = HtmlEscape();
      final sections = <String>[];
      for (final page in pages) {
        final children = <String>[];
        for (final raw in page['elements']) {
          final e = raw as Map;
          String content;
          if (e['kind'] == 'image') {
            final path = '${e['text']}';
            final bytes = await File(path).readAsBytes();
            final mime = path.toLowerCase().endsWith('.png')
                ? 'image/png'
                : path.toLowerCase().endsWith('.webp')
                ? 'image/webp'
                : 'image/jpeg';
            content =
                '<img src="data:$mime;base64,${base64Encode(bytes)}" style="width:100%;height:auto">';
          } else {
            content = esc.convert('${e['text']}');
          }
          children.add(
            '<div style="position:absolute;left:${(e['x'] as num) * 100}%;top:${(e['y'] as num) * 100}%;width:${(e['width'] as num) * 100}%;font-size:${e['size']}px;transform:rotate(${e['rotation']}rad);white-space:pre-wrap">$content</div>',
          );
        }
        sections.add('<article>${children.join()}</article>');
      }
      final paper = bookStyles[styleIndex].$2.toRadixString(16).substring(2);
      final ink = bookStyles[styleIndex].$4 ? 'e7f0e7' : '263b36';
      final html =
          '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc.convert(book.text('title'))}</title><style>body{margin:0;background:#243b36;color:#$ink;font-family:sans-serif}main{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:24px;padding:24px}article{position:relative;flex:0 0 86vw;max-width:520px;aspect-ratio:3/4;background:#$paper;border-radius:6px;scroll-snap-align:center;overflow:hidden;box-shadow:8px 10px 25px #0005}h1{color:#fff;font-size:18px;padding:20px 24px 0}p{color:#cbdad2;padding:0 24px;font-size:12px}</style><h1>${esc.convert(book.text('title'))}</h1><p>左右滑动翻页 · 客行录</p><main>${sections.join()}</main>';
      final f = File(
        '${(await getTemporaryDirectory()).path}/kexinglu-notebook.html',
      );
      await f.writeAsString(html);
      await SharePlus.instance.share(
        ShareParams(files: [XFile(f.path)], text: book.text('title')),
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('导出未成功，请确认图片仍可读取后重试。')));
      }
    }
  }

  Future<void> chooseStyle() async {
    final colors = Theme.of(context).colorScheme;
    final picked = await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      backgroundColor: colors.surface,
      builder: (c) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const LocalText('手账主题', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              LocalText('选一个纸色，整本手账都会跟着换。',
                style: TextStyle(fontSize: 12, color: colors.onSurface.withValues(alpha: .55))),
              const SizedBox(height: 16),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.35,
                children: [
                  for (var i = 0; i < bookStyles.length; i++)
                    GestureDetector(
                      onTap: () => Navigator.pop(c, i),
                      child: Container(
                        decoration: BoxDecoration(
                          color: Color(bookStyles[i].$2),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: i == styleIndex
                                ? colors.primary
                                : Colors.black.withValues(alpha: .08),
                            width: i == styleIndex ? 2 : 1,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            bookStyles[i].$1,
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: bookStyles[i].$4
                                  ? const Color(0xffe7f0e7)
                                  : Color(bookStyles[i].$3),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    if (picked != null && mounted) {
      change(() => book.data['style'] = picked);
    }
  }

  Widget sheet(int index) {
    final style = bookStyles[styleIndex];
    final contents = pages[index]['elements'] as List;
    return LayoutBuilder(
      builder: (context, box) {
        final width = box.maxWidth, height = box.maxHeight;
        final paper = Container(
          key: index == page ? canvasKey : null,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: Color(style.$2),
            borderRadius: BorderRadius.circular(7),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: .18),
                blurRadius: 18,
                offset: const Offset(5, 10),
              ),
            ],
          ),
          child: Stack(
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: PaperLines(Color(style.$3).withValues(alpha: .075)),
                ),
              ),
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: 16,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.black.withValues(alpha: .10),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
              ...contents.map((raw) {
                final e = raw as Map<String, dynamic>;
                final focus = selected == e['id'] && editing;
                final ew = e['kind'] == 'sticker'
                    ? (e['size'] as num).toDouble() * 1.5
                    : (e['width'] as num).toDouble() * width;
                Widget content = e['kind'] == 'image'
                    ? Image.file(
                        File(e['text']),
                        width: ew,
                        fit: BoxFit.contain,
                        cacheWidth: 1000,
                        errorBuilder: (c, e, s) =>
                            const Icon(Icons.broken_image_outlined),
                      )
                    : LocalText(
                        '${e['text']}',
                        style: TextStyle(
                          fontSize: (e['size'] as num).toDouble() * width / 360,
                          color: style.$4
                              ? const Color(0xffe7f0e7)
                              : Color(style.$3),
                          height: 1.45,
                        ),
                        maxLines: 12,
                        overflow: TextOverflow.ellipsis,
                      );
                return Positioned(
                  left: (e['x'] as num) * width,
                  top: (e['y'] as num) * height,
                  width: ew,
                  child: Transform.rotate(
                    angle: (e['rotation'] as num).toDouble(),
                    child: GestureDetector(
                      key: ValueKey('element-${e['id']}'),
                      onTap: editing
                          ? () => setState(() => selected = e['id'])
                          : null,
                      onDoubleTap: editing && e['kind'] == 'text'
                          ? () {
                              selected = e['id'];
                              text();
                            }
                          : null,
                      onScaleStart: editing
                          ? (d) {
                              selected = e['id'];
                              gestureOrigin = Offset(
                                (e['x'] as num).toDouble(),
                                (e['y'] as num).toDouble(),
                              );
                              gestureFocal = d.focalPoint;
                              gestureRotation = (e['rotation'] as num)
                                  .toDouble();
                              gestureSize = (e['size'] as num).toDouble();
                              gestureWidth = (e['width'] as num).toDouble();
                            }
                          : null,
                      onScaleUpdate: editing
                          ? (d) => change(() {
                              final delta = d.focalPoint - gestureFocal;
                              e['x'] = (gestureOrigin.dx + delta.dx / width)
                                  .clamp(0, .9);
                              e['y'] = (gestureOrigin.dy + delta.dy / height)
                                  .clamp(0, .94);
                              e['rotation'] = gestureRotation + d.rotation;
                              e['size'] = (gestureSize * d.scale).clamp(
                                10,
                                100,
                              );
                              if (e['kind'] == 'image') {
                                e['width'] = (gestureWidth * d.scale).clamp(
                                  .12,
                                  .95,
                                );
                              }
                            })
                          : null,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: focus
                                ? widget.palette.accent
                                : Colors.transparent,
                          ),
                          color: focus
                              ? widget.palette.accent.withValues(alpha: .03)
                              : null,
                        ),
                        child: content,
                      ),
                    ),
                  ),
                );
              }),
              Positioned(
                bottom: 12,
                left: 20,
                right: 20,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    LocalText(
                      '客行录 / ${book.text('title')}',
                      style: TextStyle(
                        fontSize: 8,
                        color: Color(style.$3).withValues(alpha: .5),
                      ),
                    ),
                    LocalText(
                      '${index + 1}'.padLeft(2, '0'),
                      style: TextStyle(fontSize: 9, color: Color(style.$3)),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
        return editing && index == page
            ? DragTarget<String>(
                onAcceptWithDetails: drop,
                builder: (c, a, r) => paper,
              )
            : paper;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return PopScope(
      canPop: leaving,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) finish();
      },
      child: Scaffold(
        backgroundColor: p.dark
            ? const Color(0xff182629)
            : const Color(0xffdce4db),
        appBar: AppBar(
          leading: IconButton(
            onPressed: finish,
            icon: const Icon(Icons.arrow_back_rounded),
          ),
          title: GestureDetector(
            onTap: () => text(title: true),
            child: Text(
              book.text('title'),
              style: const TextStyle(fontSize: 17),
            ),
          ),
          actions: [
            IconButton(
              onPressed: () => setState(() {
                editing = !editing;
                selected = null;
              }),
              tooltip: editing ? '翻页阅读' : '自由编辑',
              icon: Icon(
                editing ? Icons.auto_stories_outlined : Icons.edit_outlined,
              ),
            ),
            IconButton(
              onPressed: export,
              tooltip: '导出手账',
              icon: const Icon(Icons.ios_share_rounded),
            ),
            TextButton(
              onPressed: busy ? null : () => save(),
              child: Text(
                busy
                    ? '保存中'
                    : dirty
                    ? '保存'
                    : '已保存',
              ),
            ),
          ],
        ),
        body: SafeArea(
          top: false,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: page == 0
                          ? null
                          : () => controller.previousPage(
                              duration: Duration(
                                milliseconds: widget.reduced ? 0 : 550,
                              ),
                              curve: Curves.easeInOutCubic,
                            ),
                      icon: const Icon(Icons.chevron_left_rounded),
                    ),
                    Expanded(
                      child: LocalText(
                        '${page + 1} / ${pages.length}   ·   ${editing ? '拖动排版 / 双指旋转' : '左右滑动翻页'}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 11),
                      ),
                    ),
                    IconButton(
                      onPressed: page >= pages.length - 1
                          ? null
                          : () => controller.nextPage(
                              duration: Duration(
                                milliseconds: widget.reduced ? 0 : 550,
                              ),
                              curve: Curves.easeInOutCubic,
                            ),
                      icon: const Icon(Icons.chevron_right_rounded),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Center(
                  child: AspectRatio(
                    aspectRatio: 3 / 4,
                    child: PageView.builder(
                      controller: controller,
                      itemCount: pages.length,
                      physics: editing
                          ? const NeverScrollableScrollPhysics()
                          : const BouncingScrollPhysics(),
                      onPageChanged: (i) => setState(() {
                        page = i;
                        selected = null;
                      }),
                      itemBuilder: (c, i) {
                        final d = (i - position).clamp(-1.0, 1.0);
                        return Padding(
                          padding: const EdgeInsets.fromLTRB(7, 5, 7, 20),
                          child: Transform(
                            alignment: d < 0
                                ? Alignment.centerRight
                                : Alignment.centerLeft,
                            transform: Matrix4.identity()
                              ..setEntry(3, 2, .0013)
                              ..rotateY(widget.reduced ? 0 : -d * .9),
                            child: sheet(i),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),
              if (editing) ...[
                if (item != null)
                  SizedBox(
                    height: 40,
                    child: Row(
                      children: [
                        const SizedBox(width: 16),
                        if (item!['kind'] == 'text')
                          IconButton(
                            onPressed: () => text(),
                            icon: const Icon(Icons.edit_outlined, size: 19),
                          ),
                        Expanded(
                          child: Slider(
                            value: (item!['size'] as num).toDouble().clamp(
                              10,
                              100,
                            ),
                            min: 10,
                            max: 100,
                            onChanged: (v) => change(() => item!['size'] = v),
                          ),
                        ),
                        IconButton(
                          onPressed: () => change(() {
                            elements.removeWhere((e) => e['id'] == selected);
                            selected = null;
                          }),
                          tooltip: '删除选中素材',
                          icon: const Icon(
                            Icons.delete_outline_rounded,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: 12),
                      ],
                    ),
                  ),
                SizedBox(
                  height: 64,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 18),
                    scrollDirection: Axis.horizontal,
                    itemCount: stickers.length,
                    separatorBuilder: (_, i) => const SizedBox(width: 12),
                    itemBuilder: (c, i) => Draggable<String>(
                      data: stickers[i],
                      feedback: Material(
                        color: Colors.transparent,
                        child: Text(
                          stickers[i],
                          style: const TextStyle(fontSize: 48),
                        ),
                      ),
                      childWhenDragging: Opacity(
                        opacity: .3,
                        child: Text(
                          stickers[i],
                          style: const TextStyle(fontSize: 32),
                        ),
                      ),
                      child: GestureDetector(
                        onTap: () => append(
                          element(
                            stickers[i],
                            kind: 'sticker',
                            size: 42,
                            y: .35,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            stickers[i],
                            style: const TextStyle(fontSize: 30),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                  child: Row(
                    children: [
                      TextButton.icon(
                        onPressed: () {
                          selected = null;
                          text();
                        },
                        icon: const Icon(Icons.text_fields_rounded),
                        label: const LocalText('文字'),
                      ),
                      TextButton.icon(
                        onPressed: photo,
                        icon: const Icon(Icons.add_photo_alternate_outlined),
                        label: const LocalText('图片'),
                      ),
                      TextButton.icon(
                        onPressed: chooseStyle,
                        icon: const Icon(Icons.palette_outlined),
                        label: Text(bookStyles[styleIndex].$1),
                      ),
                      TextButton.icon(
                        onPressed: () {
                          change(() => pages.add({'elements': <dynamic>[]}));
                          WidgetsBinding.instance.addPostFrameCallback((_) {
                            controller.animateToPage(
                              pages.length - 1,
                              duration: const Duration(milliseconds: 350),
                              curve: Curves.easeOutCubic,
                            );
                          });
                        },
                        icon: const Icon(Icons.note_add_outlined),
                        label: const LocalText('加页'),
                      ),
                    ],
                  ),
                ),
              ] else
                const Padding(
                  padding: EdgeInsets.only(bottom: 20),
                  child: LocalText('纸页之间，都是你留下的片刻。', style: TextStyle(fontSize: 11)),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class PaperLines extends CustomPainter {
  final Color color;
  PaperLines(this.color);
  @override
  void paint(Canvas c, Size s) {
    for (double y = 30; y < s.height; y += 24) {
      c.drawLine(
        Offset(18, y),
        Offset(s.width - 18, y),
        Paint()
          ..color = color
          ..strokeWidth = .5,
      );
    }
  }

  @override
  bool shouldRepaint(PaperLines old) => old.color != color;
}

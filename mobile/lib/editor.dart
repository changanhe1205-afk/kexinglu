import 'i18n.dart';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'airlines.dart';
import 'atlas.dart';
import 'store.dart';

Future<void> editEntry(
  BuildContext context,
  JournalStore store,
  AtlasData atlas,
  String kind, {
  Entry? entry,
  String initialMode = 'air',
}) async {
  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: Theme.of(context).colorScheme.surface,
    builder: (context) => RecordEditor(
      store: store,
      atlas: atlas,
      kind: kind,
      entry: entry,
      initialMode: initialMode,
    ),
  );
}

class RecordEditor extends StatefulWidget {
  final JournalStore store;
  final AtlasData atlas;
  final String kind;
  final Entry? entry;
  final String initialMode;
  const RecordEditor({
    super.key,
    required this.store,
    required this.atlas,
    required this.kind,
    this.entry,
    this.initialMode = 'air',
  });
  @override
  State<RecordEditor> createState() => _RecordEditorState();
}

class _RecordEditorState extends State<RecordEditor> {
  final form = GlobalKey<FormState>();
  final fields = <String, TextEditingController>{};
  late String mode = widget.entry?.text('mode') ?? widget.initialMode;
  late String image = widget.entry?.text('image') ?? '';
  late double rating = double.tryParse(widget.entry?.text('rating') ?? '') ?? 4;
  bool dirty = false, busy = false;
  TextEditingController field(String key) => fields.putIfAbsent(
    key,
    () => TextEditingController(text: widget.entry?.text(key) ?? ''),
  );
  @override
  void initState() {
    super.initState();
    field('date').text = widget.entry?.text('date') ?? date(DateTime.now());
  }

  final fromFocus = FocusNode(), toFocus = FocusNode(), cityFocus = FocusNode(),
      airlineFocus = FocusNode();
  @override
  void dispose() {
    for (final c in fields.values) {
      c.dispose();
    }
    fromFocus.dispose();
    toFocus.dispose();
    cityFocus.dispose();
    airlineFocus.dispose();
    super.dispose();
  }

  String date(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  Map<String, dynamic> values() => {
    ...?widget.entry?.data,
    for (final pair in fields.entries) pair.key: pair.value.text.trim(),
    'mode': mode,
    'image': image == (widget.entry?.text('image') ?? '')
        ? (widget.entry?.data['image'] ?? image) : image,
    'rating': rating.toInt(),
  };
  Entry snapshot() =>
      Entry(widget.entry?.id ?? JournalStore.newId(), widget.kind, values());
  Future<void> close() async {
    if (busy) return;
    if (dirty) {
      final leave = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: const LocalText('保留这次修改吗？'),
          content: const LocalText('放弃后不会修改原来的记录。'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const LocalText('继续编辑'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(c, true),
              child: const LocalText('放弃修改'),
            ),
          ],
        ),
      );
      if (leave != true) return;
    }
    leaveEditor();
  }

  void leaveEditor() {
    if (!mounted) return;
    setState(() {
      dirty = false;
      busy = false;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) Navigator.pop(context);
    });
  }

  Future<void> save() async {
    if (busy || !form.currentState!.validate()) return;
    setState(() => busy = true);
    try {
      await widget.store.save(snapshot());
      leaveEditor();
    } catch (e) {
      if (mounted) {
        setState(() => busy = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('保存未成功，请重试；原记录未被删除。')));
      }
    }
  }

  Future<void> photo() async {
    if (busy) return;
    try {
      final draft = snapshot();
      await widget.store.setting('pending_photo', {
        'id': draft.id,
        'kind': draft.kind,
        'data': draft.data,
      });
      final picked = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        maxWidth: 2200,
        imageQuality: 88,
      );
      if (picked != null) {
        final path = await JournalStore.keepPhoto(picked.path);
        if (mounted) {
          setState(() {
            image = path;
            dirty = true;
          });
        }
      }
      await widget.store.setting('pending_photo', null);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: LocalText('图片未导入，可重新选择相册图片。')));
      }
    }
  }

  Widget input(
    String key,
    String label, {
    bool required = false,
    int lines = 1,
    TextInputType? keyboard,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      controller: field(key),
      minLines: lines,
      maxLines: lines == 1 ? 1 : 5,
      keyboardType: keyboard,
      onChanged: (_) => dirty = true,
      decoration: InputDecoration(labelText: tr(label), alignLabelWithHint: true),
      validator: (v) =>
          required && (v ?? '').trim().isEmpty ? '请填写$label' : null,
    ),
  );
  Widget place(String key, String label, String type) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: RawAutocomplete<String>(
      textEditingController: field(key),
      focusNode: key == 'from'
          ? fromFocus
          : key == 'to'
          ? toFocus
          : cityFocus,
      optionsBuilder: (v) => widget.atlas.candidates(v.text, type),
      onSelected: (s) {
        field(key).text = s;
        dirty = true;
      },
      fieldViewBuilder: (c, controller, focus, onSubmitted) => TextFormField(
        controller: controller,
        focusNode: focus,
        decoration: InputDecoration(
          labelText: tr(label),
          suffixIcon: const Icon(Icons.search_rounded),
        ),
        onChanged: (_) => dirty = true,
        validator: (v) => (v ?? '').trim().isEmpty ? '请填写$label' : null,
      ),
      optionsViewBuilder: (c, select, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          elevation: 8,
          borderRadius: BorderRadius.circular(16),
          child: SizedBox(
            width: MediaQuery.sizeOf(c).width - 48,
            height: (options.length * 52.0).clamp(0, 208),
            child: ListView(
              padding: EdgeInsets.zero,
              children: options
                  .map(
                    (o) => ListTile(
                      dense: true,
                      title: Text(o),
                      onTap: () => select(o),
                    ),
                  )
                  .toList(),
            ),
          ),
        ),
      ),
    ),
  );
  Widget airline() => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: RawAutocomplete<String>(
      textEditingController: field('airline'),
      focusNode: airlineFocus,
      optionsBuilder: (v) => airlineCandidates(v.text),
      onSelected: (s) {
        field('airline').text = s;
        dirty = true;
      },
      fieldViewBuilder: (c, controller, focus, onSubmitted) => TextFormField(
        controller: controller,
        focusNode: focus,
        decoration: const InputDecoration(
          labelText: '航空公司（选填，背面自动配宣传语）',
          suffixIcon: Icon(Icons.search_rounded),
        ),
        onChanged: (_) => dirty = true,
      ),
      optionsViewBuilder: (c, select, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          elevation: 8,
          borderRadius: BorderRadius.circular(16),
          child: SizedBox(
            width: MediaQuery.sizeOf(c).width - 48,
            height: (options.length * 52.0).clamp(0, 208),
            child: ListView(
              padding: EdgeInsets.zero,
              children: options
                  .map(
                    (o) => ListTile(
                      dense: true,
                      title: Text(o),
                      onTap: () => select(o),
                    ),
                  )
                  .toList(),
            ),
          ),
        ),
      ),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final ticket = widget.kind == 'ticket';
    final label =
        {
          'travel': '旅行日志',
          'ticket': mode == 'air' ? '机票' : '铁路票根',
          'food': '食光小记',
          'movie': '影视收藏',
        }[widget.kind] ??
        '记录';
    return PopScope(
      canPop: !dirty && !busy,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) close();
      },
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .92,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 20, 10),
              child: Row(
                children: [
                  IconButton(
                    onPressed: close,
                    icon: const Icon(Icons.close_rounded),
                  ),
                  Expanded(
                    child: LocalText(
                      '${widget.entry == null ? '新增' : '编辑'}$label',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  FilledButton(
                    onPressed: busy ? null : save,
                    child: LocalText(busy ? '保存中' : '保存'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Form(
                key: form,
                child: ListView(
                  padding: EdgeInsets.fromLTRB(
                    24,
                    8,
                    24,
                    MediaQuery.viewInsetsOf(context).bottom + 30,
                  ),
                  children: [
                    if (ticket) ...[
                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment(
                            value: 'air',
                            label: LocalText('飞机'),
                            icon: Icon(Icons.flight_rounded),
                          ),
                          ButtonSegment(
                            value: 'rail',
                            label: LocalText('铁路'),
                            icon: Icon(Icons.train_rounded),
                          ),
                        ],
                        selected: {mode},
                        onSelectionChanged: (s) => setState(() {
                          mode = s.first;
                          dirty = true;
                        }),
                      ),
                      const SizedBox(height: 24),
                      place('from', mode == 'air' ? '出发机场' : '出发车站', mode),
                      place('to', mode == 'air' ? '到达机场' : '到达车站', mode),
                      if (mode == 'air') airline(),
                      input(
                        'code',
                        mode == 'air' ? '航班号' : '车次',
                        required: true,
                      ),
                      input('seat', '座位 / 舱位'),
                      input('passenger', '乘客姓名（选填）'),
                      input(
                        'price',
                        '票价 · CNY',
                        keyboard: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                      ),
                    ] else ...[
                      input(
                        'title',
                        {
                          'travel': '地点名称',
                          'food': '食物名称',
                          'movie': '片名 / 剧名',
                        }[widget.kind]!,
                        required: true,
                      ),
                      if (widget.kind == 'travel')
                        place('city', '所在城市', 'city'),
                      if (widget.kind == 'food') input('place', '店铺 / 地点'),
                      if (widget.kind == 'movie')
                        input('category', '电影 / 剧集 / 其他'),
                    ],
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: TextFormField(
                        controller: field('date'),
                        readOnly: true,
                        decoration: const InputDecoration(
                          labelText: '日期',
                          suffixIcon: Icon(Icons.calendar_today_rounded),
                        ),
                        onTap: () async {
                          final d = await showDatePicker(
                            context: context,
                            initialDate:
                                DateTime.tryParse(field('date').text) ??
                                DateTime.now(),
                            firstDate: DateTime(1950),
                            lastDate: DateTime(2100),
                          );
                          if (d != null) {
                            setState(() {
                              field('date').text = date(d);
                              dirty = true;
                            });
                          }
                        },
                      ),
                    ),
                    input(
                      'note',
                      widget.kind == 'movie' ? '散场后的感受' : '记下这一刻',
                      lines: 3,
                    ),
                    if (!ticket) ...[
                      Row(
                        children: [
                          const LocalText('喜欢程度'),
                          Expanded(
                            child: Slider(
                              value: rating,
                              min: 0,
                              max: 5,
                              divisions: 5,
                              label: '${rating.toInt()} 星',
                              onChanged: (v) => setState(() {
                                rating = v;
                                dirty = true;
                              }),
                            ),
                          ),
                          LocalText('${rating.toInt()} / 5'),
                        ],
                      ),
                      InkWell(
                        onTap: photo,
                        borderRadius: BorderRadius.circular(20),
                        child: Container(
                          height: 180,
                          clipBehavior: Clip.antiAlias,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(20),
                            color: Theme.of(context).colorScheme.primary
                                .withValues(alpha: .08),
                          ),
                          child: image.isEmpty
                              ? const Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.add_photo_alternate_outlined,
                                      size: 32,
                                    ),
                                    SizedBox(height: 10),
                                    LocalText('从相册选择图片'),
                                  ],
                                )
                              : Stack(
                                  fit: StackFit.expand,
                                  children: [
                                    Image.file(
                                      File(image),
                                      fit: BoxFit.cover,
                                      errorBuilder: (c, e, s) => const Center(
                                        child: LocalText('图片暂不可用，点击重新选择'),
                                      ),
                                    ),
                                    const Positioned(
                                      bottom: 12,
                                      right: 12,
                                      child: Chip(label: LocalText('更换图片')),
                                    ),
                                  ],
                                ),
                        ),
                      ),
                    ],
                    if (ticket)
                      const Padding(
                        padding: EdgeInsets.only(top: 16),
                        child: LocalText(
                          '保存后自动生成地图轨迹。票根仅供纪念收藏。',
                          style: TextStyle(fontSize: 12),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

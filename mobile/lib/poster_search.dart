import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'store.dart';

class PosterResult {
  final String title, image, source, url;
  const PosterResult(this.title, this.image, this.source, this.url);
}

class PosterSearch {
  static final _cache = <String, List<PosterResult>>{};
  static String normalized(String value) => value.toLowerCase().replaceAll(RegExp(r'[\s·:：\-—_()（）]'), '');
  static bool matches(String title, String query) {
    final name = normalized(title), term = normalized(query);
    return term.isNotEmpty && name.contains(term);
  }
  static Future<List<PosterResult>> search(String query) async {
    final key = query.trim().toLowerCase();
    if (key.isEmpty) return [];
    if (_cache.containsKey(key)) return _cache[key]!;
    final results = <PosterResult>[];
    Future<void> wiki() async {
      final language = RegExp(r'[\u3400-\u9fff]').hasMatch(query) ? 'zh' : 'en';
      try {
        final bytes = await fetch(Uri.https('$language.wikipedia.org', '/w/api.php', {
          'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': query,
          'gsrlimit': '6', 'prop': 'pageimages', 'piprop': 'thumbnail', 'pilicense': 'any', 'pithumbsize': '500',
        }), 2 * 1024 * 1024);
        final data = jsonDecode(utf8.decode(bytes));
        final pages = ((data['query'] ?? {})['pages'] ?? {}) as Map;
        final sorted = pages.values.toList()..sort((a, b) => (a['index'] as int? ?? 0).compareTo(b['index'] as int? ?? 0));
        for (final page in sorted) {
          final thumb = page['thumbnail'];
          if (thumb is! Map || thumb['source'] is! String) continue;
          results.add(PosterResult(page['title'], thumb['source'], 'Wikipedia',
            Uri.https('$language.wikipedia.org', '/wiki/${page['title']}').toString()));
        }
      } catch (_) { /* Manual photo import remains available offline. */ }
    }
    Future<void> provider(Uri uri) async {
      try {
        final bytes = await fetch(uri, 2 * 1024 * 1024);
        final json = jsonDecode(utf8.decode(bytes));
        for (final item in json as List) {
          final data = item['show'];
          final image = data['image'] is Map ? data['image']['medium'] : null;
          final title = data['name'];
          if (image is! String || title is! String) continue;
          // TVmaze uses fuzzy matching; never suggest unrelated titles merely
          // because their spelling resembles the requested film.
          if (!matches(title, query)) continue;
          final year = '${data['premiered'] ?? ''}'.split('-').first;
          results.add(PosterResult('$title${year.isEmpty ? '' : ' · $year'}',
            image.replaceFirst('http://', 'https://'), 'TVmaze · CC BY-SA',
            '${data['url'] ?? ''}'));
        }
      } catch (_) { /* One unavailable source must not suppress the other. */ }
    }
    await Future.wait([
      provider(Uri.https('api.tvmaze.com', '/search/shows', {'q': query})),
      wiki(),
    ]);
    final unique = <String, PosterResult>{for (final r in results) r.image: r}.values.take(12).toList();
    unique.sort((a, b) {
      int rank(PosterResult r) => normalized(r.title.split(' · ').first) == normalized(query) ? 0 : 1;
      return rank(a).compareTo(rank(b));
    });
    if (unique.isNotEmpty) {
      if (_cache.length >= 40) _cache.remove(_cache.keys.first);
      _cache[key] = unique;
    }
    return unique;
  }

  static Future<List<int>> fetch(Uri uri, int limit) async {
    if (uri.scheme != 'https') throw const FormatException('需要 HTTPS 图片');
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    try {
      return await (() async {
        final request = await client.getUrl(uri);
        request.headers.set(HttpHeaders.userAgentHeader, 'Kexinglu/1.0 (https://github.com/changanhe1205-afk/kexinglu)');
        final response = await request.close();
        if (response.statusCode != 200) throw const HttpException('暂时无法连接海报来源');
        final bytes = <int>[];
        await for (final part in response) {
          bytes.addAll(part);
          if (bytes.length > limit) throw const FormatException('图片过大');
        }
        return bytes;
      })().timeout(const Duration(seconds: 6));
    } finally { client.close(force: true); }
  }
  static Future<String> save(PosterResult poster) async {
    final bytes = await fetch(Uri.parse(poster.image), 5 * 1024 * 1024);
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/poster-${JournalStore.newId()}.jpg');
    try {
      await file.writeAsBytes(bytes);
      return await JournalStore.keepPhoto(file.path);
    } finally { if (await file.exists()) await file.delete(); }
  }
}

class PosterCandidates extends StatefulWidget {
  final String query;
  final void Function(String path, PosterResult poster) onSelected;
  const PosterCandidates({super.key, required this.query, required this.onSelected});
  @override State<PosterCandidates> createState() => _PosterCandidatesState();
}
class _PosterCandidatesState extends State<PosterCandidates> {
  Timer? debounce;
  int generation = 0;
  bool busy = false, saving = false;
  String hint = '';
  List<PosterResult> results = [];
  @override void initState() { super.initState(); schedule(); }
  @override void didUpdateWidget(PosterCandidates old) { super.didUpdateWidget(old); if (old.query != widget.query) schedule(); }
  @override void dispose() { generation++; debounce?.cancel(); super.dispose(); }
  void schedule() {
    debounce?.cancel(); final serial = ++generation;
    results = []; hint = ''; busy = widget.query.trim().isNotEmpty;
    if (!busy) return;
    debounce = Timer(const Duration(milliseconds: 650), () async {
      final found = await PosterSearch.search(widget.query);
      if (!mounted || serial != generation) return;
      setState(() { results = found; busy = false; hint = found.isEmpty ? '未找到合适海报，可试试原片名或从相册选择。' : ''; });
    });
  }
  Future<void> select(PosterResult poster) async {
    if (saving) return;
    final serial = generation;
    setState(() { saving = true; hint = '正在导入海报…'; });
    try {
      final path = await PosterSearch.save(poster);
      if (mounted && serial == generation) { widget.onSelected(path, poster); setState(() => hint = '已设置封面'); }
    } catch (_) {
      if (mounted) setState(() => hint = '海报导入失败，请重试或从相册选择。');
    } finally { if (mounted) setState(() => saving = false); }
  }
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    if (busy || saving) const LinearProgressIndicator(minHeight: 2),
    if (hint.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(hint, style: const TextStyle(fontSize: 12))),
    if (results.isNotEmpty) ...[
      const Text('选一张海报作为封面', style: TextStyle(fontSize: 12)),
      const SizedBox(height: 8),
      SizedBox(height: 220, child: ListView.separated(scrollDirection: Axis.horizontal,
        itemCount: results.length, separatorBuilder: (_, _) => const SizedBox(width: 12),
        itemBuilder: (_, i) { final p = results[i]; return SizedBox(width: 110, child: Column(children: [
          InkWell(onTap: saving ? null : () => select(p), child: ClipRRect(borderRadius: BorderRadius.circular(12),
            child: Image.network(p.image, width: 110, height: 145, fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const SizedBox(height: 145, child: Icon(Icons.broken_image_outlined))))),
          Text(p.title, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
          InkWell(onTap: () => launchUrl(Uri.parse(p.url), mode: LaunchMode.externalApplication),
            child: Text(p.source, style: const TextStyle(fontSize: 10, decoration: TextDecoration.underline))),
        ])); })),
    ],
  ]);
}

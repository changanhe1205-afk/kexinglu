import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'store.dart';

class PosterResult {
  final String title, image, source, url;
  const PosterResult(this.title, this.image, this.source, this.url);
}

class PosterReport {
  final List<PosterResult> results;
  final Map<String, String> failures;
  const PosterReport(this.results, this.failures);
}

class PosterSearch {
  static final _cache = <String, PosterReport>{};
  static const agent = 'Kexinglu/1.0 (https://github.com/changanhe1205-afk/kexinglu)';
  static String normalized(String value) => value.toLowerCase().replaceAll(RegExp(r'[\s·:：\-—_()（）]'), '');
  static bool matches(String title, String query) => normalized(query).isNotEmpty && normalized(title).contains(normalized(query));
  static bool isScreenWork(String title, String description, String filename) {
    if (RegExp(r'soundtrack|disambiguation|novel|小说|小說|消歧|原声|原聲', caseSensitive: false).hasMatch('$title $description')) return false;
    if (RegExp(r'(film director|actor|actress|导演|導演|演員|演员|歌手)[.。]?$', caseSensitive: false).hasMatch(description.trim())) return false;
    return RegExp(r'\bfilm\b|television series|tv series|电视剧|電視劇|电影|電影|影集|劇集|剧集|海报|海報|poster', caseSensitive: false)
      .hasMatch('$title $description $filename');
  }
  static List<PosterResult> wikiResults(Map<String, dynamic> data, String language) {
    if (data['error'] != null) throw const FormatException('百科搜索暂不可用');
    final pages = ((data['query'] ?? {})['pages'] ?? {}) as Map;
    final sorted = pages.values.toList()..sort((a,b) => (a['index'] as int? ?? 0).compareTo(b['index'] as int? ?? 0));
    final result = <PosterResult>[];
    for (final page in sorted) {
      final thumb=page['thumbnail'];
      final description=((page['terms'] as Map?)?['description'] as List? ?? []).join(' ');
      if (thumb is! Map || thumb['source'] is! String || !isScreenWork('${page['title']}',description,'${page['pageimage'] ?? ''}')) continue;
      result.add(PosterResult(page['title'],thumb['source'],'Wikipedia', Uri.https('$language.wikipedia.org','/wiki/${page['title']}').toString()));
    }
    return result;
  }
  static String entities(String s) => s.replaceAll('&amp;', '&').replaceAll('&quot;', '"').replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>');
  static List<PosterResult> baiduResults(String html, String query, Uri url) {
    final meta=<String,String>{};
    for(final tag in RegExp(r'<meta\b[^>]*>',caseSensitive:false).allMatches(html)) {
      final attrs=<String,String>{};
      for(final attr in RegExp(r"""([\w:-]+)\s*=\s*["']([^"']*)["']""").allMatches(tag.group(0)!)) {
        attrs[attr.group(1)!.toLowerCase()]=entities(attr.group(2)!);
      }
      final key=attrs['property'] ?? attrs['name'];
      if(key!=null && attrs['content']!=null) meta[key.toLowerCase()]=attrs['content']!;
    }
    final title=(meta['og:title'] ?? query).replaceAll('_百度百科','');
    final description=meta['description'] ?? meta['og:description'] ?? '';
    final image=meta['og:image'] ?? meta['image'];
    if(image==null || !matches(title,query) || !isScreenWork(title,description,'')) return [];
    final imageUri=url.resolve(image);
    if(imageUri.scheme!='https') return [];
    return [PosterResult(title,imageUri.toString(),'百度百科',url.toString())];
  }
  static String failure(Object error) {
    if(error is TimeoutException || error is SocketException) return '连接超时或网络不可达';
    if(error is HandshakeException) return '安全连接失败';
    if(error is HttpException) return error.message;
    return '搜索响应暂不可用';
  }
  static Future<PosterReport> search(String query, {bool refresh=false, void Function(PosterReport)? onUpdate}) async {
    query=query.trim(); final key=query.toLowerCase();
    if(key.isEmpty) return const PosterReport([],{});
    if(!refresh && _cache.containsKey(key)) return _cache[key]!;
    final results=<PosterResult>[]; final failures=<String,String>{};
    PosterReport snapshot() {
      final sorted=<String,PosterResult>{for(final r in results) r.image:r}.values.toList();
      int rank(PosterResult r) {
        final base=r.title.split(RegExp(r'\s*[（(]| · ')).first;
        return normalized(base)==normalized(query)?0:1;
      }
      sorted.sort((a,b)=>rank(a).compareTo(rank(b)));
      return PosterReport(List.unmodifiable(sorted.take(12)),Map.unmodifiable(failures));
    }
    Future<void> source(String name, Future<List<PosterResult>> Function() run) async {
      try {results.addAll(await run());} catch(e) {failures[name]=failure(e);}
      onUpdate?.call(snapshot());
    }
    final chinese=RegExp(r'[\u3400-\u9fff]').hasMatch(query);
    final language=chinese?'zh':'en';
    await Future.wait([
      if(chinese) source('百度百科',() async {
        final uri=Uri.https('baike.baidu.com','/item/$query');
        final raw=await fetch(uri,3*1024*1024);
        final found=baiduResults(utf8.decode(raw),query,uri);
        if(found.isEmpty) throw const HttpException('该公开页面未提供可自动提取的影视海报，可打开百科查找');
        return found;
      }),
      source('Wikipedia',() async {
        final uri=Uri.https('$language.wikipedia.org','/w/api.php',{
          'action':'query','format':'json','generator':'search','gsrsearch':'intitle:"${query.replaceAll('"', '')}"','gsrlimit':'8',
          'prop':'pageimages|pageterms','wbptterms':'description','piprop':'thumbnail|name','pilicense':'any','pithumbsize':'500',
        });
        return wikiResults(jsonDecode(utf8.decode(await fetch(uri,2*1024*1024))),language);
      }),
      source('TVmaze',() async {
        final raw=await fetch(Uri.https('api.tvmaze.com','/search/shows',{'q':query}),2*1024*1024);
        final found=<PosterResult>[];
        for(final row in jsonDecode(utf8.decode(raw)) as List) {
          final show=row['show'];final img=show['image'];final title=show['name'];
          if(img is! Map || img['medium'] is! String || title is! String || !matches(title,query)) continue;
          final year='${show['premiered'] ?? ''}'.split('-').first;
          found.add(PosterResult('$title${year.isEmpty?'':' · $year'}',img['medium'],'TVmaze · CC BY-SA','${show['url']}'));
        }
        return found;
      }),
    ]);
    final report=snapshot();
    // A failed source must remain retryable, not frozen into a successful cache.
    if(report.results.isNotEmpty && failures.isEmpty) {
      if(_cache.length>=40) _cache.remove(_cache.keys.first);
      _cache[key]=report;
    }
    return report;
  }
  static Map<String,String> headers(String sourceUrl) => {
    HttpHeaders.userAgentHeader:agent,
    if(Uri.tryParse(sourceUrl)?.host=='baike.baidu.com') HttpHeaders.refererHeader:sourceUrl,
  };
  static Future<List<int>> fetch(Uri uri,int limit,{String sourceUrl=''}) async {
    if(uri.scheme!='https') throw const FormatException('需要 HTTPS 图片');
    final client=HttpClient()..connectionTimeout=const Duration(seconds:5);
    try {
      return await (() async {
        final request=await client.getUrl(uri);
        headers(sourceUrl).forEach(request.headers.set);
        final response=await request.close();
        if(response.statusCode!=200) throw HttpException(response.statusCode==403?'来源拒绝自动访问（403）':'来源响应 ${response.statusCode}');
        final bytes=<int>[];
        await for(final part in response) {bytes.addAll(part);if(bytes.length>limit) throw const FormatException('响应过大');}
        return bytes;
      })().timeout(const Duration(seconds:8));
    } finally {client.close(force:true);}
  }
  static Future<String> save(PosterResult poster) async {
    final bytes=await fetch(Uri.parse(poster.image),5*1024*1024,sourceUrl:poster.url);
    // Reject error HTML and corrupt images before creating a permanent photo.
    final codec=await ui.instantiateImageCodec(Uint8List.fromList(bytes),targetWidth:1000);
    codec.dispose();
    final dir=await getTemporaryDirectory();final file=File('${dir.path}/poster-${JournalStore.newId()}.jpg');
    try {await file.writeAsBytes(bytes);return await JournalStore.keepPhoto(file.path);}
    finally {if(await file.exists()) await file.delete();}
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
  Map<String, String> failures = {};
  @override void initState() { super.initState(); schedule(); }
  @override void didUpdateWidget(PosterCandidates old) { super.didUpdateWidget(old); if (old.query != widget.query) schedule(); }
  @override void dispose() { generation++; debounce?.cancel(); super.dispose(); }
  void schedule({bool refresh = false}) {
    debounce?.cancel(); final serial = ++generation;
    results = []; failures = {}; hint = ''; busy = widget.query.trim().isNotEmpty;
    if (!busy) return;
    debounce = Timer(const Duration(milliseconds: 650), () async {
      final found = await PosterSearch.search(widget.query, refresh: refresh, onUpdate: (partial) {
        if (!mounted || serial != generation) return;
        setState(() { results = partial.results; failures = partial.failures; });
      });
      if (!mounted || serial != generation) return;
      setState(() {
        results = found.results; failures = found.failures; busy = false;
        hint = results.isEmpty ? (failures.isEmpty ? '没有找到带海报的影视词条，试试完整片名或原文名。' : '部分海报来源未能连接，请重试或打开百科查找。') : '';
      });
    });
  }
  Future<void> select(PosterResult poster) async {
    if (saving) return;
    final serial = generation;
    setState(() { saving = true; hint = '正在导入海报…'; });
    try {
      final path = await PosterSearch.save(poster);
      if (mounted && serial == generation) { widget.onSelected(path, poster); setState(() => hint = '已设置封面'); }
    } catch (e) {
      if (mounted && serial == generation) setState(() => hint = '海报导入失败：${PosterSearch.failure(e)}，可重试或从相册选择。');
    } finally { if (mounted) setState(() => saving = false); }
  }
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    if (busy || saving) const LinearProgressIndicator(minHeight: 2),
    if (hint.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(hint, style: const TextStyle(fontSize: 12))),
    if (!busy && failures.isNotEmpty) ExpansionTile(
      title: const Text('查看来源状态', style: TextStyle(fontSize: 12)),
      tilePadding: EdgeInsets.zero,
      children: [for (final e in failures.entries) ListTile(dense: true, title: Text(e.key), subtitle: Text(e.value))],
    ),
    if (widget.query.trim().isNotEmpty) Wrap(spacing: 6, children: [
      TextButton.icon(onPressed: busy ? null : () => setState(() => schedule(refresh: true)), icon: const Icon(Icons.refresh, size: 16), label: const Text('重新查找')),
      TextButton(onPressed: () => launchUrl(Uri.https('baike.baidu.com', '/item/${widget.query.trim()}'), mode: LaunchMode.externalApplication), child: const Text('百度百科查找')),
      TextButton(onPressed: () => launchUrl(Uri.https(RegExp(r'[\u3400-\u9fff]').hasMatch(widget.query) ? 'zh.wikipedia.org' : 'en.wikipedia.org', '/w/index.php', {'search': widget.query.trim()}), mode: LaunchMode.externalApplication), child: const Text('维基百科查找')),
    ]),
    if (results.isNotEmpty) ...[
      const Text('选一张海报作为封面', style: TextStyle(fontSize: 12)),
      const SizedBox(height: 8),
      SizedBox(height: 220, child: ListView.separated(scrollDirection: Axis.horizontal,
        itemCount: results.length, separatorBuilder: (_, _) => const SizedBox(width: 12),
        itemBuilder: (_, i) { final p = results[i]; return SizedBox(width: 110, child: Column(children: [
          InkWell(onTap: saving ? null : () => select(p), child: ClipRRect(borderRadius: BorderRadius.circular(12),
            child: Image.network(p.image, headers: PosterSearch.headers(p.url), width: 110, height: 145, fit: BoxFit.contain,
              errorBuilder: (_, _, _) => const SizedBox(height: 145, child: Center(child: Text('图片加载失败\n点击重试导入', textAlign: TextAlign.center, style: TextStyle(fontSize: 11))))))),
          Text(p.title, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
          InkWell(onTap: () => launchUrl(Uri.parse(p.url), mode: LaunchMode.externalApplication),
            child: Text(p.source, style: const TextStyle(fontSize: 10, decoration: TextDecoration.underline))),
        ])); })),
    ],
  ]);
}

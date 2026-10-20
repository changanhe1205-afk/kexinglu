import 'dart:convert';

import 'sync_hash.dart';

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

class Entry {
  final String id;
  final String kind;
  final Map<String, dynamic> data;
  Entry(this.id, this.kind, this.data);
  String text(String key) => '${data[key] ?? ''}';
  Entry copy() =>
      Entry(id, kind, jsonDecode(jsonEncode(data)) as Map<String, dynamic>);
}

class JournalStore extends ChangeNotifier {
  Future<void> _pendingWrite = Future.value();
  Future<T> serialized<T>(Future<T> Function() action) {
    final operation = _pendingWrite.then((_) => action());
    _pendingWrite = operation.then<void>(
      (_) {},
      onError: (Object e, StackTrace s) {},
    );
    return operation;
  }

  Future<void> save(Entry entry) => serialized(() => _save(entry));
  Future<void> remove(Entry entry) => serialized(() => _remove(entry));
  Future<void> setting(String key, dynamic value) =>
      serialized(() => _setting(key, value));
  Future<void> restore(Map<String, dynamic> backup) =>
      serialized(() => _restore(backup));
  Future<bool> applyCloud(
    Entry? incoming,
    String localId,
    String expected,
    Map<String, dynamic> metadata,
  ) => serialized(() async {
    final existing = entries.where((e) => e.id == localId).firstOrNull;
    if (syncHash(existing?.data) != expected) return false;
    final deleted = {...settings['cloud_deleted'] as Map? ?? {}};
    if (incoming != null) deleted.remove(localId);
    final next = {...settings, 'cloud_meta': metadata, 'cloud_deleted': deleted};
    await database?.transaction((tx) async {
      if (incoming == null) {
        await tx.delete('entries', where: 'id = ?', whereArgs: [localId]);
      } else {
        await tx.insert('entries', {
          'id': incoming.id,
          'kind': incoming.kind,
          'payload': jsonEncode(incoming.data),
          'updated': DateTime.now().microsecondsSinceEpoch,
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }
      await tx.insert('settings', {
        'id': 1,
        'payload': jsonEncode(next),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    });
    entries.removeWhere((e) => e.id == localId);
    if (incoming != null) entries.insert(0, incoming.copy());
    settings.addAll(next);
    notifyListeners();
    return true;
  });
  final Database? database;
  final List<Entry> entries;
  final Map<String, dynamic> settings;
  JournalStore.memory() : database = null, entries = [], settings = {};
  JournalStore._(this.database, this.entries, this.settings);
  static Future<JournalStore> open() async {
    final dir = await getApplicationDocumentsDirectory();
    final db = await openDatabase(
      '${dir.path}/kexinglu-mobile.db',
      version: 1,
      onCreate: (db, version) async {
        await db.execute(
          'CREATE TABLE entries (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, updated INTEGER NOT NULL)',
        );
        await db.execute(
          'CREATE TABLE settings (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)',
        );
      },
    );
    final rows = await db.query('entries', orderBy: 'updated DESC');
    final settings = await db.query('settings');
    return JournalStore._(
      db,
      rows
          .map(
            (r) => Entry(
              r['id'] as String,
              r['kind'] as String,
              jsonDecode(r['payload'] as String),
            ),
          )
          .toList(),
      settings.isEmpty ? {} : jsonDecode(settings.first['payload'] as String),
    );
  }

  List<Entry> of(String kind) => entries.where((e) => e.kind == kind).toList();
  Future<void> _save(Entry entry) async {
    final deleted = {...settings['cloud_deleted'] as Map? ?? {}}..remove(entry.id);
    final next = {...settings, 'cloud_deleted': deleted};
    await database?.transaction((tx) async {
      await tx.insert('entries', {
        'id': entry.id, 'kind': entry.kind, 'payload': jsonEncode(entry.data),
        'updated': DateTime.now().microsecondsSinceEpoch,
      }, conflictAlgorithm: ConflictAlgorithm.replace);
      await tx.insert('settings', {'id': 1, 'payload': jsonEncode(next)},
        conflictAlgorithm: ConflictAlgorithm.replace);
    });
    entries.removeWhere((e) => e.id == entry.id);
    entries.insert(0, entry.copy());
    settings.addAll(next);
    notifyListeners();
  }
  Future<void> _remove(Entry entry) async {
    // Only an explicit user action authorizes a cloud deletion. A missing local
    // row alone can also be an interrupted import or damaged synchronization state.
    final deleted = {...settings['cloud_deleted'] as Map? ?? {}, entry.id: true};
    final next = {...settings, 'cloud_deleted': deleted};
    await database?.transaction((tx) async {
      await tx.delete('entries', where: 'id = ?', whereArgs: [entry.id]);
      await tx.insert('settings', {'id': 1, 'payload': jsonEncode(next)},
        conflictAlgorithm: ConflictAlgorithm.replace);
    });
    entries.removeWhere((e) => e.id == entry.id);
    settings.addAll(next);
    notifyListeners();
  }

  Future<void> _setting(String key, dynamic value) async {
    final next = jsonDecode(
      jsonEncode({...settings, key: value}),
    ) as Map<String, dynamic>;
    await database?.insert('settings', {
      'id': 1,
      'payload': jsonEncode(next),
    }, conflictAlgorithm: ConflictAlgorithm.replace);
    settings.addAll(next);
    notifyListeners();
  }

  Future<Map<String, dynamic>> backup() async {
    final photos = <String, String>{};
    Future<void> visit(dynamic node) async {
      if (node is Map) {
        final path = node['kind'] == 'image' ? node['text'] : node['image'];
        if (path is String && path.isNotEmpty && !photos.containsKey(path)) {
          photos[path] = base64Encode(await File(path).readAsBytes());
        }
        for (final value in node.values) {
          await visit(value);
        }
      } else if (node is List) {
        for (final value in node) {
          await visit(value);
        }
      }
    }

    final records = entries
        .map((e) => {'id': e.id, 'kind': e.kind, 'data': e.data})
        .toList();
    await visit(records);
    return {
      'format': 'kexinglu-mobile',
      'version': 1,
      'entries': records,
      'photos': photos,
    };
  }

  Future<void> _restore(Map<String, dynamic> backup) async {
    if (backup['format'] != 'kexinglu-mobile' ||
        backup['version'] != 1 ||
        backup['entries'] is! List ||
        backup['photos'] is! Map) {
      throw const FormatException('不是客行录手机版备份');
    }
    final incoming = <Entry>[];
    for (final raw in backup['entries']) {
      if (raw is! Map ||
          raw['id'] is! String ||
          raw['data'] is! Map ||
          ![
            'travel',
            'ticket',
            'movie',
            'food',
            'book',
          ].contains(raw['kind'])) {
        throw const FormatException('备份记录不完整');
      }
      if (raw['kind'] == 'book' &&
          (raw['data']['pages'] is! List ||
              (raw['data']['pages'] as List).isEmpty)) {
        throw const FormatException('手账页数据不完整');
      }
      final data = raw['data'] as Map;
      final rating = data['rating'];
      if (rating != null &&
          (rating is! num || !rating.isFinite || rating < 0 || rating > 5)) {
        throw const FormatException('评分数据无效');
      }
      if (raw['kind'] == 'ticket' && !['air', 'rail'].contains(data['mode'])) {
        throw const FormatException('票根类型无效');
      }
      void photo(dynamic path) {
        if (path != null &&
            path != '' &&
            (path is! String || !backup['photos'].containsKey(path))) {
          throw const FormatException('备份缺少图片');
        }
      }

      photo(data['image']);
      if (raw['kind'] == 'book') {
        if (data['style'] != null &&
            (data['style'] is! int || data['style'] < 0 || data['style'] > 5)) {
          throw const FormatException('手账款式无效');
        }
        for (final page in data['pages']) {
          if (page is! Map || page['elements'] is! List) {
            throw const FormatException('手账页无效');
          }
          for (final e in page['elements']) {
            if (e is! Map ||
                e['id'] is! String ||
                e['text'] is! String ||
                !['text', 'sticker', 'image'].contains(e['kind'])) {
              throw const FormatException('手账素材无效');
            }
            for (final key in ['x', 'y', 'rotation', 'size', 'width']) {
              if (e[key] is! num || !(e[key] as num).isFinite) {
                throw const FormatException('手账位置无效');
              }
            }
            if (e['x'] < 0 ||
                e['x'] > 1 ||
                e['y'] < 0 ||
                e['y'] > 1 ||
                e['size'] < 1 ||
                e['size'] > 200 ||
                e['width'] <= 0 ||
                e['width'] > 1) {
              throw const FormatException('手账尺寸无效');
            }
            if (e['kind'] == 'image') photo(e['text']);
          }
        }
      }
      incoming.add(
        Entry(raw['id'], raw['kind'], Map<String, dynamic>.from(raw['data'])),
      );
    }
    final bytes = <String, List<int>>{};
    for (final pair in (backup['photos'] as Map).entries) {
      if (pair.key is! String || pair.value is! String) {
        throw const FormatException('图片数据不完整');
      }
      bytes[pair.key] = base64Decode(pair.value);
    }
    final paths = <String, String>{};
    if (bytes.isNotEmpty) {
      final dir = Directory(
        '${(await getApplicationDocumentsDirectory()).path}/photos',
      );
      await dir.create(recursive: true);
      for (final pair in bytes.entries) {
        final ext = pair.key.split('.').last.toLowerCase();
        final file = File(
          '${dir.path}/${newId()}.${['png', 'jpg', 'jpeg', 'webp', 'heic'].contains(ext) ? ext : 'jpg'}',
        );
        await file.writeAsBytes(pair.value, flush: true);
        paths[pair.key] = file.path;
      }
    }
    dynamic rewrite(dynamic value) {
      if (value is String) return paths[value] ?? value;
      if (value is List) return value.map(rewrite).toList();
      if (value is Map) return value.map((k, v) => MapEntry(k, rewrite(v)));
      return value;
    }

    final restored = incoming
        .map(
          (e) =>
              Entry(e.id, e.kind, Map<String, dynamic>.from(rewrite(e.data))),
        )
        .toList();
    final deleted = {...settings['cloud_deleted'] as Map? ?? {}};
    for (final e in restored) { deleted.remove(e.id); }
    final next = {...settings, 'cloud_deleted': deleted};
    await database?.transaction((tx) async {
      await tx.insert('settings', {'id': 1, 'payload': jsonEncode(next)},
        conflictAlgorithm: ConflictAlgorithm.replace);
      for (final e in restored) {
        await tx.insert('entries', {
          'id': e.id,
          'kind': e.kind,
          'payload': jsonEncode(e.data),
          'updated': DateTime.now().microsecondsSinceEpoch,
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }
    });
    final ids = restored.map((e) => e.id).toSet();
    entries.removeWhere((e) => ids.contains(e.id));
    entries.insertAll(0, restored);
    settings.addAll(next);
    notifyListeners();
  }

  static String newId() => DateTime.now().microsecondsSinceEpoch.toString();
  static Future<String> keepPhoto(String path) async {
    final dir = Directory(
      '${(await getApplicationDocumentsDirectory()).path}/photos',
    );
    await dir.create(recursive: true);
    final ext = path.split('.').last.toLowerCase();
    return (await File(path).copy(
      '${dir.path}/${newId()}.${['jpg', 'jpeg', 'png', 'webp', 'heic'].contains(ext) ? ext : 'jpg'}',
    )).path;
  }
}

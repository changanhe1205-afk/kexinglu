import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'cloud_account.dart';
import 'store.dart';
import 'sync_hash.dart';

class CloudSync {
  static bool _busy = false;
  final JournalStore store;
  final void Function(String, int, int)? onProgress;
  // Keep the captured owner private while exposing a named constructor argument.
  // ignore: prefer_initializing_formals
  CloudSync(this.store, {this.onProgress, String? owner}) : _owner = owner;
  int _done = 0, _total = 0, _photos = 0;
  final _downloads = <String, Future<dynamic>>{};
  int _activeTransfers = 0;
  final _waitingTransfers = Queue<Completer<void>>();
  Future<T> _transfer<T>(Future<T> Function() action) async {
    if (_activeTransfers >= 3) {
      final ready = Completer<void>();
      _waitingTransfers.add(ready);
      await ready.future;
    } else {
      _activeTransfers++;
    }
    try {
      return await action();
    } finally {
      if (_waitingTransfers.isNotEmpty) {
        _waitingTransfers.removeFirst().complete();
      } else {
        _activeTransfers--;
      }
    }
  }

  void report(String stage, int done, int total) {
    _done = done;
    _total = total;
    onProgress?.call(stage, done, total);
  }

  bool _allowPendingTravel = false;
  final _pendingMedia = <String>{};
  Future<dynamic> resolveMedia(dynamic value, bool download) async {
    try {
      return await asset(value, download);
    } on Exception catch (e) {
      if (!download || !_allowPendingTravel) rethrow;
      _pendingMedia.add(failureReason(e));
      // Keep the original reference. Never replace a missing photo with blank data.
      return value;
    }
  }

  String? _owner;
  SupabaseClient get client {
    final c = CloudAccount.instance.client!;
    if (_owner != null && c.auth.currentUser?.id != _owner) {
      throw StateError('账号已变更，本轮同步停止');
    }
    return c;
  }

  String get uid => client.auth.currentUser!.id;
  final assetPattern = RegExp(r'^[0-9a-f]{64}\.(png|jpg|jpeg|webp|heic|bin)$');
  static String uuid() {
    final r = Random.secure();
    final b = List.generate(16, (_) => r.nextInt(256));
    b[6] = (b[6] & 15) | 64;
    b[8] = (b[8] & 63) | 128;
    final s = b.map((v) => v.toRadixString(16).padLeft(2, '0')).join();
    return '${s.substring(0, 8)}-${s.substring(8, 12)}-${s.substring(12, 16)}-${s.substring(16, 20)}-${s.substring(20)}';
  }

  bool explicitlyDeleted(String id) =>
      (store.settings['cloud_deleted'] as Map?)?[id] == true;

  Entry? find(String id) => store.entries.where((e) => e.id == id).firstOrNull;
  Map<String, dynamic> get metadata =>
      Map<String, dynamic>.from(store.settings['cloud_meta'] as Map? ?? {});
  Future<dynamic> media(
    dynamic value,
    bool download, {
    bool image = false,
  }) async {
    if (value is Map &&
        (value.containsKey(r'$asset') || value.containsKey(r'$inline'))) {
      return resolveMedia(value, download);
    }
    if (value is Map) {
      final next = <String, dynamic>{};
      for (final e in value.entries) {
        next[e.key] = await media(
          e.value,
          download,
          image:
              e.key == 'image' ||
              e.key == 'poster' ||
              (e.key == 'text' && value['kind'] == 'image'),
        );
      }
      return next;
    }
    if (value is List) {
      final next = [];
      for (var i = 0; i < value.length; i += 3) {
        final end = min(i + 3, value.length);
        next.addAll(
          await Future.wait(
            value.sublist(i, end).map((e) => media(e, download)),
          ),
        );
      }
      return next;
    }
    if (image && value != null && value != '') return resolveMedia(value, download);
    return value;
  }

  Future<dynamic> asset(dynamic value, bool download) {
    if (download &&
        value is Map &&
        assetPattern.hasMatch('${value[r'$asset']}')) {
      final name = value[r'$asset'] as String;
      return _downloads.putIfAbsent(name, () => _asset(value, true));
    }
    return _asset(value, download);
  }

  Future<dynamic> _asset(dynamic value, bool download) async {
    final bucket = client.storage.from('journal-media');
    if (download) {
      if (value is! Map || !assetPattern.hasMatch('${value[r'$asset']}')) {
        throw const FormatException('图片引用无效');
      }
      final name = value[r'$asset'] as String;
      final dir = Directory(
        '${(await getApplicationDocumentsDirectory()).path}/cloud-media',
      );
      await dir.create(recursive: true);
      final file = File('${dir.path}/$name');
      if (await file.exists() &&
          sha256.convert(await file.readAsBytes()).toString() ==
              name.split('.').first) {
        return file.path;
      }
      onProgress?.call('接收照片 · 已获取 $_photos 张', _done, _total);
      final bytes = await _transfer(() => bucket.download('$uid/$name'));
      if (bytes.length > 10 * 1024 * 1024 ||
          sha256.convert(bytes).toString() != name.split('.').first) {
        throw const FormatException('图片校验失败');
      }
      final temp = File('${file.path}.part');
      await temp.writeAsBytes(bytes, flush: true);
      await temp.rename(file.path);
      _photos++;
      onProgress?.call('接收照片 · 已获取 $_photos 张', _done, _total);
      return file.path;
    }
    if (value is Map && value.containsKey(r'$asset')) {
      if (!assetPattern.hasMatch('${value[r'$asset']}')) {
        throw const FormatException('图片引用无效');
      }
      return value;
    }
    Uint8List bytes;
    String ext;
    if (value is Map && value.containsKey(r'$inline')) {
      bytes = base64Decode(value[r'$inline']);
      ext = bytes.length > 3 && bytes[0] == 137 ? 'png' : 'jpg';
    } else {
      final file = File(value as String);
      if (await file.length() > 10 * 1024 * 1024) {
        throw const FormatException('单张图片超过 10 MiB');
      }
      bytes = await file.readAsBytes();
      ext = file.path.split('.').last.toLowerCase();
      if (!['png', 'jpg', 'jpeg', 'webp', 'heic'].contains(ext)) ext = 'bin';
    }
    if (bytes.length > 10 * 1024 * 1024) {
      throw const FormatException('单张图片超过 10 MiB');
    }
    final name = '${sha256.convert(bytes)}.$ext';
    try {
      await _transfer(
        () => bucket.uploadBinary(
          '$uid/$name',
          bytes,
          fileOptions: const FileOptions(
            upsert: false,
            contentType: 'application/octet-stream',
          ),
        ),
      );
    } on StorageException catch (e) {
      if (e.statusCode != '409' && e.error != 'Duplicate') rethrow;
    }
    return {r'$asset': name};
  }

  void validate(String kind, Map<String, dynamic> data) {
    if (!['travel', 'ticket', 'food', 'movie', 'book'].contains(kind)) {
      throw const FormatException('记录类型未知');
    }
    final rating = data['rating'];
    if (rating != null &&
        rating != '' &&
        (rating is! num || !rating.isFinite || rating < 0 || rating > 5)) {
      throw const FormatException('评分无效');
    }
    if (kind == 'book') {
      if (data['pages'] is! List ||
          (data['pages'] as List).isEmpty ||
          data['style'] is! int) {
        throw const FormatException('手账格式无效');
      }
      for (final page in data['pages']) {
        if (page is! Map || page['elements'] is! List) {
          throw const FormatException('纸页格式无效');
        }
        for (final e in page['elements']) {
          if (e is! Map ||
              e['text'] is! String ||
              e['id'] is! String ||
              !['text', 'image', 'sticker'].contains(e['kind'])) {
            throw const FormatException('素材格式无效');
          }
          for (final k in ['x', 'y', 'width', 'size', 'rotation']) {
            if (e[k] is! num || !(e[k] as num).isFinite) {
              throw const FormatException('素材位置无效');
            }
          }
          if (e['x'] < 0 ||
              e['x'] > 1 ||
              e['y'] < 0 ||
              e['y'] > 1 ||
              e['width'] <= 0 ||
              e['width'] > 1 ||
              e['size'] < 1 ||
              e['size'] > 200) {
            throw const FormatException('素材尺寸无效');
          }
        }
      }
    }
  }

  static String failureReason(Object e) {
    if (e is FormatException) return e.message;
    if (e is StorageException) {
      return '图片传输失败（${e.statusCode ?? '未知状态'}），请检查网络后重试';
    }
    if (e is PostgrestException) return '云端读写失败（${e.code ?? '未知状态'}）';
    if (e is DatabaseException) return '本机数据库写入失败（SQLite），请保留本地资料并反馈此结果';
    if (e is FileSystemException) return '本地图片无法读取，请确认原图仍存在';
    return '传输失败（${e.runtimeType}），请检查网络后重试';
  }

  Future<String> run() async {
    if (_busy) return '同步已在进行';
    if (CloudAccount.instance.uid == null) throw StateError('请先登录');
    _owner = CloudAccount.instance.uid;
    _busy = true;
    try {
      final owner = store.settings['cloud_owner'];
      if (owner != null && owner != uid) {
        throw StateError('本地资料已绑定其他账号，已停止同步以避免混入数据');
      }
      await store.setting('cloud_owner', uid);
      var meta = metadata;
      final snapshot = {for (final e in store.entries) e.id: e.copy()};
      final conflicts = <String>{};
      int uploaded = 0, downloaded = 0, cloudRecords = 0;
      final failures = <String>[];
      final uploadIds = {...snapshot.keys, ...meta.keys}.toList();
      for (var index = 0; index < uploadIds.length; index++) {
        final id = uploadIds[index];
        report('上传记录', index, uploadIds.length);
        try {
          final entry = snapshot[id];
          var old = meta[id] as Map?;
          if (entry == null && !explicitlyDeleted(id)) continue;
          final signature = syncHash(entry?.data);
          if (old != null && old['hash'] == signature) continue;
          if (old == null) {
            old = {
              'rid': uuid(),
              'kind': entry!.kind,
              'revision': 0,
              'hash': syncHash(null),
            };
            meta[id] = old;
            await store.setting('cloud_meta', meta);
          }
          final result = await client.rpc(
            'put_journal_record',
            params: {
              'record_id': old['rid'],
              'record_kind': old['kind'],
              'payload': entry == null
                  ? <String, dynamic>{}
                  : await media(entry.data, false),
              'expected_revision': old['revision'],
              'is_deleted': entry == null,
            },
          );
          if (result['accepted'] != true) {
            conflicts.add(id);
            continue;
          }
          meta[id] = {
            ...old,
            'revision': result['record']['revision'],
            'hash': signature,
            'pending_media': old['pending_media'] == true,
          };
          await store.setting('cloud_meta', meta);
          uploaded++;
        } on Exception catch (e) {
          failures.add('上传记录：${failureReason(e)}');
        }
      }
      report('上传记录', uploadIds.length, uploadIds.length);
      report('正在获取云端目录', 0, 0);
      final byRemoteId = <String, Map<String, dynamic>>{};
      String? cursor;
      while (true) {
        var query = client.from('journal_records').select();
        if (cursor != null) query = query.gt('id', cursor);
        // Keyset pagination must use the SAME direction as gt(id, cursor).
        // postgrest 2.9 defaults order() to descending; request it explicitly.
        final rows = await query.order('id', ascending: true).limit(20);
        if (rows.isEmpty) break;
        var previous = cursor;
        for (final row in rows) {
          final id = row['id'] as String;
          if (previous != null && id.compareTo(previous) <= 0) {
            throw const FormatException('云端分页顺序异常，目录核对未完成；本地资料已保留，请重试');
          }
          previous = id;
        }
        for (final row in rows) {
          byRemoteId[row['id'] as String] = row;
        }
        // Even a short page can reflect a server-side cap. Stop only on empty.
        final next = rows.last['id'] as String;
        if (cursor != null && next.compareTo(cursor) <= 0) {
          throw const FormatException('云端分页没有前进，请复制此结果反馈，未清除本地资料');
        }
        cursor = next;
      }
      final allRows = byRemoteId.values.toList();
      for (var index = 0; index < allRows.length; index++) {
        final r = allRows[index];
        report('接收记录与照片', index, allRows.length);
        if (r['deleted'] != true) cloudRecords++;
        try {
          meta = metadata;
          final ids = meta.keys.where(
            (id) => (meta[id] as Map)['rid'] == r['id'],
          );
          final id = ids.isEmpty ? 'cloud-${r['id']}' : ids.first;
          final old = meta[id] as Map?;
          final current = find(id);
          final missing = current == null && r['deleted'] != true;
          final recoverMissing = missing && !explicitlyDeleted(id);
          if (old != null && r['revision'] <= old['revision'] &&
              old['pending_media'] != true && !recoverMissing) {
            continue;
          }
          final expected = syncHash(current?.data);
          if (old != null && expected != old['hash'] && !recoverMissing) {
            conflicts.add(id);
            continue;
          }
          _pendingMedia.clear();
          _allowPendingTravel = r['kind'] == 'travel';
          Entry? incoming;
          if (r['deleted'] != true) {
            final data = Map<String, dynamic>.from(
              await media(r['data'], true),
            );
            validate(r['kind'], data);
            incoming = Entry(id, r['kind'], data);
          }
          meta[id] = {
            'rid': r['id'],
            'kind': r['kind'],
            'revision': r['revision'],
            'hash': syncHash(incoming?.data),
            'pending_media': _pendingMedia.isNotEmpty,
          };
          if (client.auth.currentUser?.id != _owner) {
            throw StateError('账号已变更');
          }
          if (await store.applyCloud(incoming, id, expected, meta)) {
            downloaded++;
            if (_pendingMedia.isNotEmpty) {
              failures.add('旅行「${incoming?.text('title') ?? ''}」文字已保存，照片待重试：${_pendingMedia.join('；')}');
            }
          } else {
            conflicts.add(id);
          }
        } on Exception catch (e) {
          failures.add(
            '接收${{'travel': '旅行', 'ticket': '票根', 'movie': '影视', 'food': '食光', 'book': '手账'}[r['kind']] ?? '记录'}：${failureReason(e)}',
          );
        } finally {
          _allowPendingTravel = false;
        }
      }
      report('同步检查完成', allRows.length, allRows.length);
      await store.setting('cloud_last_sync', DateTime.now().toIso8601String());
      // Reconcile identities, not just revision numbers or aggregate totals.
      final finalMeta = metadata;
      final present = {for (final e in store.entries) e.id};
      final missingRows = allRows.where((row) {
        if (row['deleted'] == true) return false;
        return !finalMeta.entries.any((pair) =>
          (pair.value as Map)['rid'] == row['id'] && present.contains(pair.key));
      }).toList();
      const labels = {'travel': '旅途', 'ticket': '票根', 'food': '食光', 'movie': '影视', 'book': '手账'};
      final inventory = labels.entries.map((pair) {
        final remoteCount = allRows.where((r) => r['deleted'] != true && r['kind'] == pair.key).length;
        return '${pair.value}：云端 $remoteCount / 本机 ${store.of(pair.key).length}';
      }).join('；');
      final summary =
          '本轮上传 $uploaded 条，下载 $downloaded 条。云端现有 $cloudRecords 条，本机现有 ${store.entries.length} 条。'
          '${conflicts.isEmpty ? '' : '${conflicts.length} 条存在两端修改冲突，未覆盖。'}'
          '${failures.isEmpty ? '' : '\n未完成 ${failures.length} 条，具体原因：\n${failures.toSet().join('\n')}'}'
          '\n$inventory'
          '${missingRows.isEmpty ? '' : '\n仍有 ${missingRows.length} 条云端记录未落地：${missingRows.map((r) => '${labels[r['kind']] ?? r['kind']} ${r['id']}').join('；')}'}'
          '\n客户端 1.0.0 · 本次核对 ${allRows.length} 条（含删除标记）'
          '${cloudRecords == 0 ? '云端暂时没有记录，请先在有资料的电脑上完成同步。' : ''}';
      await store.setting('cloud_last_result', summary);
      return summary;
    } finally {
      _busy = false;
    }
  }
}

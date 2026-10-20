import 'package:kexinglu_mobile/ticket_colors.dart';
import 'package:flutter/material.dart';

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/cloud_sync.dart';
import 'package:kexinglu_mobile/store.dart';
import 'package:kexinglu_mobile/sync_hash.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ParallelMedia extends CloudSync {
  int active = 0, peak = 0;
  ParallelMedia() : super(JournalStore.memory());
  @override
  Future<dynamic> asset(dynamic value, bool download) async {
    active++;
    if (active > peak) peak = active;
    await Future<void>.delayed(const Duration(milliseconds: 2));
    active--;
    return value;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('photo batches are bounded and preserve page order', () async {
    final sync = ParallelMedia();
    final input = List.generate(8, (i) => {'image': 'photo$i'});
    expect(await sync.media(input, true), input);
    expect(sync.peak, 3);
  });
  test('saved ticket colors match desktop independently of app theme', () {
    final rose = TicketColors.fromData({
      'mode': 'air',
      '_desktop': {'style': 'rose'},
    });
    expect(rose.paper, const Color(0xfffff8f9));
    expect(rose.ink, const Color(0xff6d3849));
    expect(rose.back, const Color(0xfff3e0e6));
    final midnight = TicketColors.fromData({
      'mode': 'air',
      '_desktop': {'style': 'midnight'},
    });
    expect(midnight.paper, const Color(0xff192537));
    expect(midnight.ink, const Color(0xffeef3fc));
    expect(
      TicketColors.fromData({
        'mode': 'rail',
        '_desktop': {'vehicle': '火车'},
      }).paper,
      const Color(0xfff8e9e7),
    );
    expect(
      TicketColors.fromData({'mode': 'rail'}).paper,
      const Color(0xffe9f3f9),
    );
  });
  late SupabaseClient client;
  late List<Map<String, dynamic>> rows;
  late int writes;
  int serverPageCap = 20;
  bool reversePages = false;
  int activeMedia = 0, peakMedia = 0;
  setUp(() async {
    rows = [];
    writes = 0;
    serverPageCap = 20;
    reversePages = false;
    activeMedia = peakMedia = 0;
    client = SupabaseClient(
      'https://test.supabase.co',
      'sb_publishable_test',
      authOptions: const AuthClientOptions(autoRefreshToken: false),
      httpClient: MockClient((request) async {
        expect(request.headers['Authorization'], startsWith('Bearer '));
        if (request.url.path.endsWith('/rpc/put_journal_record')) {
          writes++;
          return http.Response(
            jsonEncode({
              'accepted': true,
              'record': {'revision': 1},
            }),
            200,
            headers: {'content-type': 'application/json'},
            request: request,
          );
        }
        if (request.url.path.startsWith('/storage/v1/object/')) {
          activeMedia++;
          if (activeMedia > peakMedia) peakMedia = activeMedia;
          await Future<void>.delayed(const Duration(milliseconds: 5));
          activeMedia--;
          return http.Response(
            jsonEncode({'Key':request.url.path}),
            200,
            request: request,
            headers: {'content-type': 'application/json'},
          );
        }
        expect(request.url.path, '/rest/v1/journal_records');
        // Model PostgREST sorting as well as filtering. Ignoring `order`
        // previously hid the SDK's descending default and its lost next page.
        final selected = rows.where((r) {
          final filter = request.url.queryParameters['id'];
          return filter == null ||
              (r['id'] as String).compareTo(filter.substring(3)) > 0;
        }).toList();
        final descending = (request.url.queryParameters['order'] ?? '').contains('desc');
        selected.sort((a, b) => descending
            ? (b['id'] as String).compareTo(a['id'] as String)
            : (a['id'] as String).compareTo(b['id'] as String));
        if (reversePages) {
          selected.sort((a, b) => (b['id'] as String).compareTo(a['id'] as String));
        }
        return http.Response(
          jsonEncode(selected.take(int.parse(request.url.queryParameters['limit'] ?? '20')).take(serverPageCap).toList()),
          200,
          headers: {'content-type': 'application/json'},
          request: request,
        );
      }),
    );
    final exp = DateTime.now().millisecondsSinceEpoch ~/ 1000 + 3600;
    String part(Map<String, dynamic> data) =>
        base64Url.encode(utf8.encode(jsonEncode(data))).replaceAll('=', '');
    final token =
        '${part({'alg': 'HS256'})}.${part({'sub': 'test-owner', 'exp': exp})}.test';
    await client.auth.recoverSession(
      jsonEncode({
        'access_token': token,
        'refresh_token': 'test-refresh',
        'token_type': 'bearer',
        'expires_in': 3600,
        'user': {
          'id': 'test-owner',
          'app_metadata': {},
          'user_metadata': {},
          'aud': 'authenticated',
          'created_at': '2026-01-01T00:00:00Z',
        },
      }),
    );
    CloudAccount.instance.client = client;
  });
  tearDown(() async {
    CloudAccount.instance.client = null;
    await client.dispose();
  });

  test(
    'nested scrapbook pages keep at most three image transfers active',
    () async {
      final pages = List.generate(
        3,
        (i) => List.generate(
          3,
          (j) => {
            'image': {
              r'$inline': base64Encode([i, j, 42]),
            },
          },
        ),
      );
      await CloudSync(JournalStore.memory()).media(pages, false);
      expect(peakMedia, 3);
      expect(activeMedia, 0);
    },
  );

  test('39 cloud rows and 23 local rows recover 16 acknowledged but missing entries', () async {
    final store = JournalStore.memory();
    final meta = <String, dynamic>{};
    for (var i = 0; i < 39; i++) {
      final rid = i.toString().padLeft(3, '0');
      final id = 'cloud-$rid';
      final data = {'title': '旅途$i', 'image': ''};
      rows.add({'id': rid, 'kind': 'travel', 'revision': 1,
        'deleted': false, 'data': data});
      meta[id] = {'rid': rid, 'kind': 'travel', 'revision': 1,
        'hash': syncHash(null)};
      if (i < 23) {
        await store.save(Entry(id, 'travel', data));
        meta[id]['hash'] = syncHash(data);
      }
    }
    await store.setting('cloud_meta', meta);
    final result = await CloudSync(store).run();
    expect(result, contains('上传 0 条，下载 16 条'));
    expect(result, contains('旅途：云端 39 / 本机 39'));
    expect(result, isNot(contains('未落地')));
    expect(store.entries.length, 39);
    expect(writes, 0, reason: 'missing local rows must never delete cloud records');
    expect(await CloudSync(store).run(), contains('上传 0 条，下载 0 条'));
  });

  test('26 cloud / 23 phone retrieves Xiamen beyond the old first 20', () async {
    final store = JournalStore.memory();
    final meta = <String, dynamic>{};
    // The old descending first page contained 2 travel, 9 tickets, 1 food,
    // and 8 movies. Three more older tickets were already on the phone.
    final kinds = [
      'travel', 'movie', 'ticket', 'ticket', 'ticket', 'ticket',
      'travel', 'travel', ...List.filled(9, 'ticket'), 'food',
      ...List.filled(8, 'movie'),
    ];
    for (var i = 0; i < kinds.length; i++) {
      final rid = '00000000-0000-4000-8000-${i.toString().padLeft(12, '0')}';
      final id = 'cloud-$rid';
      final data = <String, dynamic>{'title': i == 0 ? '厦门岛' : '记录$i',
        'city': i == 0 ? '厦门' : '', 'image': '', 'photos': []};
      rows.add({'id': rid, 'kind': kinds[i], 'revision': 1,
        'deleted': false, 'data': data});
      if (i >= 3) {
        await store.save(Entry(id, kinds[i], data));
        meta[id] = {'rid': rid, 'kind': kinds[i], 'revision': 1,
          'hash': syncHash(data)};
      }
    }
    await store.setting('cloud_meta', meta);
    expect(store.entries.length, 23);
    final result = await CloudSync(store).run();
    expect(result, contains('上传 0 条，下载 3 条'));
    expect(result, contains('云端现有 26 条，本机现有 26 条'));
    expect(result, contains('旅途：云端 3 / 本机 3'));
    expect(result, contains('票根：云端 13 / 本机 13'));
    expect(result, contains('本次核对 26 条'));
    expect(store.of('travel').where((e) => e.text('city') == '厦门').single.text('title'), '厦门岛');
    expect(writes, 0);
    expect(await CloudSync(store).run(), contains('上传 0 条，下载 0 条'));
  });

  for (final total in [20, 40, 41]) {
    test('complete catalog including tombstones across $total rows and short server pages', () async {
      serverPageCap = 7;
      final store = JournalStore.memory();
      rows = List.generate(total, (i) => {
        'id': i.toString().padLeft(3, '0'), 'kind': 'travel',
        'revision': 1, 'deleted': i == 19,
        'data': {'title': '地点$i', 'image': ''},
      });
      final result = await CloudSync(store).run();
      expect(result, contains('本次核对 $total 条'));
      expect(store.entries.length, total - 1);
      expect(writes, 0);
    });
  }

  test('invalid page ordering fails explicitly instead of reporting partial success', () async {
    reversePages = true;
    rows = List.generate(26, (i) => {
      'id': i.toString().padLeft(3, '0'), 'kind': 'travel',
      'revision': 1, 'deleted': false, 'data': {'title': '地点$i'},
    });
    final store = JournalStore.memory();
    await expectLater(CloudSync(store).run(), throwsFormatException);
    expect(store.entries, isEmpty);
    expect(writes, 0);
  });

  test('missing row with old content hash is recovered without cloud deletion', () async {
    final store = JournalStore.memory();
    final data = {'title': '旧同步状态', 'image': ''};
    rows = [{'id': 'lost', 'kind': 'travel', 'revision': 2,
      'deleted': false, 'data': data}];
    await store.setting('cloud_meta', {'cloud-lost': {
      'rid': 'lost', 'kind': 'travel', 'revision': 2, 'hash': syncHash(data),
    }});
    expect(await CloudSync(store).run(), contains('上传 0 条，下载 1 条'));
    expect(writes, 0);
    expect(store.of('travel').single.text('title'), '旧同步状态');
  });

  test('explicit delete is uploaded, while undo clears deletion intent', () async {
    final store = JournalStore.memory();
    final entry = Entry('local', 'travel', {'title': 'delete test'});
    await store.save(entry);
    await store.setting('cloud_meta', {'local': {
      'rid': 'remote-delete', 'kind': 'travel', 'revision': 1, 'hash': syncHash(entry.data),
    }});
    await store.remove(entry);
    expect((store.settings['cloud_deleted'] as Map)['local'], true);
    expect(await CloudSync(store).run(), contains('上传 1 条'));
    expect(writes, 1);
    await store.save(entry);
    expect((store.settings['cloud_deleted'] as Map).containsKey('local'), false);
  });

  test('travel text survives photo failure and same revision retries without upload', () async {
    final store = JournalStore.memory();
    rows = [{
      'id': 'trip', 'kind': 'travel', 'revision': 1, 'deleted': false,
      'data': {'title': '南京', 'city': '南京', 'image': '',
        'photos': [{'image': {r'$asset': 'invalid'}, 'caption': '城墙'}]},
    }];
    final first = await CloudSync(store).run();
    expect(store.of('travel').single.text('title'), '南京');
    expect(first, contains('文字已保存，照片待重试'));
    expect(store.of('travel').single.data['photos'][0]['image'], {r'$asset': 'invalid'});
    expect((store.settings['cloud_meta'] as Map)['cloud-trip']['pending_media'], true);
    rows[0]['data']['photos'] = [];
    final second = await CloudSync(store).run();
    expect(second, contains('下载 1 条'));
    expect(second, isNot(contains('未完成')));
    expect(writes, 0);
    expect((store.settings['cloud_meta'] as Map)['cloud-trip']['pending_media'], false);
    expect(await CloudSync(store).run(), contains('下载 0 条'));
  });

  test('bad image does not block other downloads; retry recovers only failed record', () async {
    final store = JournalStore.memory();
    Map<String, dynamic> row(String id, dynamic image) => {
      'id': id,
      'kind': 'movie',
      'revision': 1,
      'deleted': false,
      'data': {
        'title': id,
        'rating': 5,
        'image': image,
        '_desktop': {'kind': '电影'},
      },
    };
    rows = [
      row('broken', {r'$asset': 'invalid'}),
      row('healthy', ''),
    ];
    final progress = <int>[];
    final first = await CloudSync(
      store,
      onProgress: (stage, done, total) {
        expect(done, lessThanOrEqualTo(total));
        progress.add(done);
      },
    ).run();
    expect(progress.last, 2);
    expect(first, contains('下载 1 条'));
    expect(first, contains('未完成 1 条'));
    expect(store.of('movie').single.text('title'), 'healthy');
    rows[0] = row('broken', '');
    final second = await CloudSync(store).run();
    expect(second, contains('下载 1 条'));
    expect(store.of('movie').length, 2);
    expect(writes, 0);
    expect(await CloudSync(store).run(), contains('下载 0 条'));
  });

  test(
    'bad upload image does not block healthy upload or cloud download',
    () async {
      final store = JournalStore.memory();
      await store.save(
        Entry('bad', 'movie', {
          'title': 'bad',
          'image': {r'$asset': 'invalid'},
        }),
      );
      await store.save(
        Entry('good', 'ticket', {'from': 'PEK', 'to': 'XUZ', 'image': ''}),
      );
      rows = [
        {
          'id': 'remote',
          'kind': 'food',
          'revision': 1,
          'deleted': false,
          'data': {'title': 'food', 'rating': 5, 'image': ''},
        },
      ];
      final message = await CloudSync(store).run();
      expect(message, contains('上传 1 条，下载 1 条'));
      expect(message, contains('未完成 1 条'));
      expect(store.of('food').length, 1);
      expect(writes, 1);
    },
  );
}

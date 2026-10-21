import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/account_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/look.dart';
import 'package:kexinglu_mobile/notebook.dart';
import 'package:kexinglu_mobile/store.dart';
import 'package:kexinglu_mobile/sync_hash.dart';

Finder field(String label) => find.byWidgetPredicate(
  (w) => w is TextField && w.decoration?.labelText == label,
);
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // Widget tests remain offline, independent of the packaged cloud project.
  setUpAll(() => CloudAccount.instance.initialize(configuration: {}));
  late AtlasData atlas;
  setUp(() async {
    atlas = AtlasData();
    await atlas.load();
  });
  test('railway and airport coordinates remain available offline', () {
    for (final n in [
      '余姚北',
      '独山东',
      '都匀东',
      '枣庄',
      '贵阳北',
      '杭州东',
      '成都东',
      '厦门北',
      '福州南',
      '济南西',
      '重庆西',
    ]) {
      expect(atlas.locate(n, 'rail'), isNotNull, reason: n);
    }
    expect(atlas.locate('枣庄', 'rail')!.lat, closeTo(34.780764, .001));
    expect(
      atlas.locate('徐州观音国际机场', 'air')!.lon,
      atlas.locate('XUZ', 'air')!.lon,
    );
    expect(atlas.locate('未知机场123', 'air'), isNull);
    expect(atlas.candidates('徐州', 'air').length, greaterThan(0));
  });
  test('editing a snapshot never changes a saved entry before save', () async {
    final store = JournalStore.memory();
    final e = Entry('one', 'book', {
      'pages': [
        {
          'elements': [element('original')],
        },
      ],
    });
    await store.save(e);
    final draft = store.entries.first.copy();
    draft.data['pages'][0]['elements'][0]['text'] = 'discard';
    expect(
      store.entries.first.data['pages'][0]['elements'][0]['text'],
      'original',
    );
    await store.save(Entry('two', 'ticket', {'code': 'CA1234'}));
    await store.save(Entry('two', 'ticket', {'code': 'CA12'}));
    expect(store.of('ticket').length, 1);
    expect(store.of('ticket').first.text('code'), 'CA12');
  });
  Future<void> start(
    WidgetTester t,
    JournalStore store, {
    Size size = const Size(390, 844),
  }) async {
    t.view.physicalSize = size;
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    await t.pumpWidget(Kexinglu(store: store, atlas: atlas));
    await t.pumpAndSettle();
  }

  testWidgets('account switches between password, email code and registration', (t) async {
    final store = JournalStore.memory();
    await start(t, store, size: const Size(360, 740));
    await t.tap(find.text('我的'));
    await t.pumpAndSettle();
    await t.tap(find.text('账号与同步'));
    await t.pumpAndSettle();
    expect(find.byType(AccountScreen), findsOneWidget);
    expect(field('邮箱账号'), findsOneWidget);
    expect(field('密码（至少 8 位）'), findsOneWidget);
    await t.tap(find.text('验证码登录'));
    await t.pumpAndSettle();
    expect(field('邮件验证码'), findsOneWidget);
    expect(field('密码（至少 8 位）'), findsNothing);
    await t.tap(find.text('还没有账号？ 注册'));
    await t.pumpAndSettle();
    expect(find.text('创建客行录账号'), findsOneWidget);
    expect(find.text('创建账号'), findsOneWidget);
    expect(find.textContaining('QQ'), findsNothing);
    expect(t.takeException(), isNull);
  });

  testWidgets('home shares desktop clock weather quote and real shortcuts', (t) async {
    await start(t, JournalStore.memory());
    expect(find.text('每日一句'), findsOneWidget);
    expect(find.text('选择城市'), findsOneWidget);
    await t.scrollUntilVisible(find.text('食光小记'), 150, scrollable: find.byType(Scrollable).first);
    await t.tap(find.text('食光小记'));
    await t.pumpAndSettle();
    expect(t.takeException(), isNull);
    expect(find.text('记得那一口的味道'), findsOneWidget);
  });

  testWidgets('travel gallery exposes every photo and pending download', (t) async {
    final store = JournalStore.memory();
    await store.save(Entry('trip-gallery', 'travel', {
      'title': '南京相册', 'city': '南京', 'date': '2026-10-18',
      'photos': [
        {'image': {r'$asset': 'one'}},
        {'image': {r'$asset': 'two'}},
      ],
    }));
    await start(t, store);
    await t.tap(find.text('旅途'));
    await t.pumpAndSettle();
    expect(find.text('2 张照片 · 部分待同步'), findsOneWidget);
    await t.tap(find.text('南京相册'));
    await t.pumpAndSettle();
    expect(find.byIcon(Icons.cloud_download_outlined), findsWidgets);
    expect(find.text('照片待下载，请在账号与同步中重试'), findsWidgets);
    expect(t.takeException(), isNull);
  });

  testWidgets('phone navigation, adding a record and discard return cleanly', (
    t,
  ) async {
    final store = JournalStore.memory();
    await start(t, store);
    expect(t.takeException(), isNull);
    await t.tap(find.text('旅途'));
    await t.pumpAndSettle();
    await t.tap(find.byIcon(Icons.add_rounded).first);
    await t.pumpAndSettle();
    await t.enterText(field('地点名称'), '湖边散步');
    await t.enterText(field('所在城市'), '杭州');
    await t.tap(find.text('保存'));
    await t.pumpAndSettle();
    expect(store.of('travel').length, 1);
    expect(find.text('新增旅行日志'), findsNothing);
    await t.tap(find.text('湖边散步'));
    await t.pumpAndSettle();
    await t.tap(find.byIcon(Icons.edit_outlined));
    await t.pumpAndSettle();
    await t.enterText(field('地点名称'), '放弃的内容');
    await t.tap(find.byIcon(Icons.close_rounded));
    await t.pumpAndSettle();
    await t.tap(find.text('放弃修改'));
    await t.pumpAndSettle();
    expect(store.of('travel').first.text('title'), '湖边散步');
    expect(field('地点名称'), findsNothing);
    expect(t.takeException(), isNull);
  });
  testWidgets('ticket deck flips and preserves flight letters during editing', (
    t,
  ) async {
    final store = JournalStore.memory();
    await store.save(
      Entry('a', 'ticket', {
        'mode': 'air',
        'from': 'PEK',
        'to': 'PVG',
        'code': 'CA1234',
        'date': '2026-10-05',
        'price': '580',
      }),
    );
    await start(t, store, size: const Size(360, 780));
    await t.tap(find.text('票夹'));
    await t.pumpAndSettle();
    expect(find.text('CNY 580'), findsOneWidget);
    await t.tap(find.text('CA1234'));
    await t.pumpAndSettle();
    expect(find.text('抵达之后，\n故事才刚开始。'), findsOneWidget);
    await t.longPress(find.text('抵达之后，\n故事才刚开始。'));
    await t.pumpAndSettle();
    await t.tap(find.text('编辑票根'));
    await t.pumpAndSettle();
    await t.enterText(field('航班号'), 'CA12');
    await t.tap(find.text('保存'));
    await t.pumpAndSettle();
    expect(store.of('ticket').first.text('code'), 'CA12');
    expect(store.of('ticket').first.text('date'), '2026-10-05');
    expect(t.takeException(), isNull);
  });
  testWidgets('new notebook opens editor, adds sticker, saves and returns', (
    t,
  ) async {
    final store = JournalStore.memory();
    await start(t, store);
    await t.scrollUntilVisible(find.text('旅行手账'), 180, scrollable: find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.tap(find.text('旅行手账'));
    await t.pumpAndSettle();
    await t.tap(find.text('开始记录'));
    await t.pumpAndSettle();
    await t.tap(find.text('新建空白手账'));
    await t.pumpAndSettle();
    await t.tap(find.text('✦').first);
    await t.pumpAndSettle();
    await t.tap(find.text('保存'));
    await t.pumpAndSettle();
    expect(store.of('book').length, 1);
    expect(store.of('book').first.data['pages'][0]['elements'].length, 1);
    await t.tap(find.byIcon(Icons.arrow_back_rounded));
    await t.pumpAndSettle();
    expect(find.text('旅行手账'), findsOneWidget);
    expect(t.takeException(), isNull);
  });
  test('backup merge and invalid book are atomic', () async {
    final source = JournalStore.memory();
    await source.save(Entry('saved', 'travel', {'title': '杭州'}));
    final target = JournalStore.memory();
    await target.restore(await source.backup());
    expect(target.entries.single.text('title'), '杭州');
    final bad = {
      'format': 'kexinglu-mobile',
      'version': 1,
      'photos': <String, String>{},
      'entries': [
        {
          'id': 'saved',
          'kind': 'travel',
          'data': {'title': '不应写入'},
        },
        {
          'id': 'bad',
          'kind': 'book',
          'data': {
            'pages': [
              {
                'elements': [
                  {'kind': 'text'},
                ],
              },
            ],
          },
        },
      ],
    };
    await expectLater(target.restore(bad), throwsFormatException);
    expect(target.entries.single.text('title'), '杭州');
  });
  testWidgets('notebook dragging remains cumulative across rendered frames', (
    t,
  ) async {
    final store = JournalStore.memory();
    final sticker = element('★', kind: 'sticker', x: .2, y: .2, size: 32);
    final book = Entry('drag-book', 'book', {
      'title': '移动测试',
      'style': 0,
      'pages': [
        {
          'elements': [sticker],
        },
      ],
    });
    await start(t, store);
    final context = t.element(find.byType(Scaffold).first);
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => NotebookEditor(
          store: store,
          book: book,
          palette: AppPalette.all.first,
          reduced: true,
          fresh: true,
        ),
      ),
    );
    await t.pumpAndSettle();
    final f = find.byKey(ValueKey('element-${sticker['id']}'));
    final gesture = await t.startGesture(t.getCenter(f));
    await gesture.moveBy(const Offset(25, 0));
    await t.pump();
    final first = t.getTopLeft(f);
    await gesture.moveBy(const Offset(20, 15));
    await t.pump();
    final second = t.getTopLeft(f);
    await gesture.moveBy(const Offset(20, 15));
    await t.pump();
    final third = t.getTopLeft(f);
    expect(second.dx - first.dx, closeTo(20, 2));
    expect(third.dx - second.dx, closeTo(20, 2));
    expect(third.dy - second.dy, closeTo(15, 2));
    await gesture.up();
    await t.pumpAndSettle();
    await t.tap(find.text('保存'));
    await t.pumpAndSettle();
    expect(
      store.of('book').single.data['pages'][0]['elements'][0]['x'],
      greaterThan(.25),
    );
    expect(t.takeException(), isNull);
  });
  testWidgets('rail category creates railway ticket without switching form', (
    t,
  ) async {
    final store = JournalStore.memory();
    await start(t, store);
    await t.tap(find.text('票夹'));
    await t.pumpAndSettle();
    await t.tap(find.text('高铁 / 火车'));
    await t.pumpAndSettle();
    await t.tap(find.byIcon(Icons.add_rounded).first);
    await t.pumpAndSettle();
    expect(find.text('新增铁路票根'), findsOneWidget);
    expect(field('出发车站'), findsOneWidget);
    expect(field('航班号'), findsNothing);
  });
  testWidgets('all themes render on small phone and preserve records', (
    t,
  ) async {
    final store = JournalStore.memory();
    await start(t, store, size: const Size(360, 780));
    for (var i = 0; i < AppPalette.all.length; i++) {
      await store.setting('theme', i);
      await t.pumpAndSettle();
      expect(t.takeException(), isNull, reason: AppPalette.all[i].name);
    }
    expect(store.entries, isEmpty);
  });
  testWidgets(
    'floating navigation stays above Android gesture area on every tab',
    (t) async {
      final store = JournalStore.memory();
      await start(t, store, size: const Size(360, 780));
      t.view.padding = const FakeViewPadding(bottom: 48);
      t.view.viewPadding = const FakeViewPadding(bottom: 48);
      addTearDown(t.view.resetPadding);
      addTearDown(t.view.resetViewPadding);
      for (final theme in [0, 6]) {
        await store.setting('theme', theme);
        await t.pumpAndSettle();
        for (final label in ['旅途', '票夹', '收藏', '我的', '首页']) {
          await t.tap(find.text(label).last);
          await t.pumpAndSettle();
          final nav = find.byKey(const ValueKey('main-floating-navigation'));
          expect(nav, findsOneWidget);
          final glass = find.descendant(of: nav, matching: find.byType(Glass));
          expect(t.getRect(glass).bottom, lessThanOrEqualTo(780 - 48 - 15));
          expect(
            find.descendant(of: glass, matching: find.byType(BackdropFilter)),
            findsOneWidget,
          );
          expect(t.takeException(), isNull);
        }
      }
      await t.tap(find.text('我的').last);
      await t.pumpAndSettle();
      await t.scrollUntilVisible(find.text('账号与同步'), 350);
      await t.pumpAndSettle();
      await t.drag(find.byType(Scrollable).first, const Offset(0, -120));
      await t.pumpAndSettle();
      await t.tap(find.text('账号与同步'));
      await t.pumpAndSettle();
      expect(find.textContaining('云端暂不可用'), findsOneWidget);
      expect(find.text('邮箱账号'), findsOneWidget);
      expect(t.takeException(), isNull);
    },
  );
  test('cloud apply cannot replace a newer local edit', () async {
    final store = JournalStore.memory();
    await store.save(Entry('one', 'movie', {'title': 'old'}));
    final before = syncHash(store.entries.single.data);
    await store.save(Entry('one', 'movie', {'title': 'new local'}));
    expect(
      await store.applyCloud(
        Entry('one', 'movie', {'title': 'remote'}),
        'one',
        before,
        {},
      ),
      isFalse,
    );
    expect(store.entries.single.text('title'), 'new local');
    expect(store.settings['cloud_meta'], isNull);
  });
}

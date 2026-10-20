import 'dart:io';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/store.dart';
import 'package:kexinglu_mobile/look.dart';

void main() {
  setUpAll(() async {
    await CloudAccount.instance.initialize(configuration: {});
    CloudAccount.instance.client = SupabaseClient('https://test.supabase.co', 'test-public', authOptions: const AuthClientOptions(autoRefreshToken: false));
  });
  tearDownAll(() async { await CloudAccount.instance.client?.dispose(); CloudAccount.instance.client = null; });
  testWidgets('capture actual phone widgets with isolated sample records', (
    t,
  ) async {
    t.view.physicalSize = const Size(390, 844);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    await t.runAsync(() async {
      final font = FontLoader('Roboto')
        ..addFont(
          File('C:/Windows/Fonts/msyh.ttc')
              .readAsBytes()
              .then((b) => ByteData.sublistView(b)),
        );
      await font.load();
      await (FontLoader('Ahem')..addFont(
            File('C:/Windows/Fonts/msyh.ttc')
                .readAsBytes()
                .then((b) => ByteData.sublistView(b)),
          ))
          .load();
      await (FontLoader('MaterialIcons')..addFont(
            File(
              'D:/Tools/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf',
            ).readAsBytes().then((b) => ByteData.sublistView(b)),
          ))
          .load();
    });
    debugPrint("font loaded");
    final atlas = AtlasData();
    await t.runAsync(() => atlas.load());
    final store = JournalStore.memory();
    debugPrint("atlas loaded");
    await store.setting('personal_profile:guest', {'nickname':'小行','signature':'把日子，慢慢收藏。','cover':'preset:lakeside.png'});
    await store.setting('weather_qweather_cache', {'lat':24.48,'lon':118.08,'name':'厦门市','stamp':'10/19 10:00',
      'data': {'condition':{'text':'少云','code':'102'},
        'temperature':{'value':25,'unit':'°C'}, 'feelsLike':{'value':26,'unit':'°C'},
        'humidity':0.68, 'wind':{'direction':{'degree':120,'compass':'se'},'speed':{'value':12,'unit':'m/s'},'scale':3}}});
    await store.save(Entry('qa-movie','movie',{'title':'海街日记','date':'2026-10-19','rating':4,'category':'电影','note':'平凡的日子里也有柔软的光。\n慢下来，记住那些与家人相处的片刻。','_desktop':{'director':'是枝裕和','genre':'剧情 / 家庭','country':'日本'}}));
    await store.save(
      Entry('qa-travel', 'travel', {
        'title': '在西湖，慢下来',
        'city': '杭州',
        'date': '2026-10-16',
        'note': '把风景写进这一页。',
      }),
    );
    await store.save(
      Entry('qa-ticket', 'ticket', {
        'mode': 'air',
        'from': '杭州萧山国际机场',
        'to': '成都天府国际机场',
        'code': 'CA1741',
        'date': '2026-10-16',
        'price': '680',
        'passenger': '旅行者',
      }),
    );
    final key = GlobalKey();
    await t.pumpWidget(
      RepaintBoundary(
        key: key,
        child: Kexinglu(store: store, atlas: atlas),
      ),
    );
    await t.pumpAndSettle();
    Future<void> shot(String name) async {
      final boundary =
          key.currentContext!.findRenderObject() as RenderRepaintBoundary;
      final image = await t.runAsync(() => boundary.toImage(pixelRatio: 2));
      final bytes = await t.runAsync(
        () => image!.toByteData(format: ui.ImageByteFormat.png),
      );
      final dir = Directory('../design/verification')..createSync(recursive: true);
      await t.runAsync(
        () => File('${dir.path}/mobile-$name.png')
            .writeAsBytes(bytes!.buffer.asUint8List()),
      );
      image!.dispose();
    }

    await t.runAsync(() => precacheImage(const AssetImage('assets/backgrounds/lakeside.png'), key.currentContext!));
    await t.pumpAndSettle();
    debugPrint('widgets rendered');
    await shot('expanded-home');
    await t.tap(find.text('票夹'));
    await t.pumpAndSettle();
    await shot('tickets');
    await t.tap(find.text('旅途'));
    await t.pumpAndSettle();
    await shot('expanded-travel');
    await t.tap(find.byTooltip('全屏地图')); await t.pumpAndSettle();
    await shot('expanded-fullmap');
    await t.tap(find.byTooltip('退出全屏地图')); await t.pumpAndSettle();
    await t.tap(find.text('收藏')); await t.pumpAndSettle();
    await t.tap(find.byType(FlipCard).first); await t.pumpAndSettle();
    await shot('expanded-collection-back');
    await t.tap(find.text('我的'));
    await t.pumpAndSettle();
    await shot('expanded-profile');
    await t.tap(find.text('编辑资料'));
    await t.pumpAndSettle();
    await shot('profile-editor');
    await t.tap(find.byIcon(Icons.arrow_back_rounded));
    await t.pumpAndSettle();
    await t.drag(find.byType(ListView).first, const Offset(0, -430));
    await t.pumpAndSettle();
    await shot('profile-tools');
    await t.tap(find.text('设置'));
    await t.pumpAndSettle();
    await shot('profile-settings');
    await t.tap(find.byIcon(Icons.arrow_back_rounded));
    await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('数据备份'), 150, scrollable: find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.tap(find.text('数据备份'));
    await t.pumpAndSettle();
    await shot('profile-backup');
    await t.tap(find.byIcon(Icons.arrow_back_rounded));
    await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('关于'), 150, scrollable: find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.tap(find.text('关于'));
    await t.pumpAndSettle();
    await shot('profile-about');
    await t.tap(find.byIcon(Icons.arrow_back_rounded));
    await t.pumpAndSettle();
    await store.setting('theme', 6);
    await t.pumpAndSettle();
    final scrollable = t.state<ScrollableState>(find.byType(Scrollable).first);
    scrollable.position.jumpTo(0);
    await t.pumpAndSettle();
    await shot('profile-dark');
    await store.setting('theme', 0);
    await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('账号与同步'), 200, scrollable: find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.drag(find.byType(Scrollable).first, const Offset(0, -120));
    await t.pumpAndSettle();
    await t.tap(find.text('账号与同步'));
    await t.pumpAndSettle();
    await shot('107-account');
    await t.tap(find.text('验证码登录'));
    await t.pumpAndSettle();
    await shot('107-account-otp');
    await store.setting('theme', 6);
    await t.pumpAndSettle();
    await shot('107-account-dark');
    expect(t.takeException(), isNull);
  }, skip: !const bool.fromEnvironment('CAPTURE_SCREENSHOTS'));
}

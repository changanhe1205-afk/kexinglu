import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/store.dart';

void main() {
  testWidgets('tablet visual QA', (t) async {
    await CloudAccount.instance.initialize(configuration:{});
    t.view.physicalSize=const Size(1280,800);t.view.devicePixelRatio=1;
    addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
    await t.runAsync(() async {
      for(final family in ['Roboto','Ahem']) {
        await (FontLoader(family)..addFont(File('C:/Windows/Fonts/msyh.ttc').readAsBytes().then(ByteData.sublistView))).load();
      }
      await (FontLoader('MaterialIcons')..addFont(File('D:/Tools/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf').readAsBytes().then(ByteData.sublistView))).load();
    });
    final atlas=AtlasData();await t.runAsync(()=>atlas.load());final store=JournalStore.memory();
    await store.setting('reduced',true);
    for(final city in ['厦门','杭州','成都']) {
      await store.save(Entry(city,'travel',{'title':'在$city，慢下来','city':city,'date':'2026-10-20','note':'把风景写进这一页，收藏旅途的光。'}));
    }
    await store.save(Entry('air','ticket',{'mode':'air','from':'杭州萧山国际机场','to':'成都天府国际机场','code':'CA1741','date':'2026-10-20','price':'680','passenger':'旅行者'}));
    final key=GlobalKey();
    await t.pumpWidget(RepaintBoundary(key:key,child:Kexinglu(store:store,atlas:atlas)));await t.pumpAndSettle();
    await t.runAsync(()=>precacheImage(const AssetImage('assets/backgrounds/lakeside.png'),key.currentContext!));
    for(final label in ['首页','旅途','票夹']) {
      await t.tap(find.text(label).last);await t.pumpAndSettle();
      final boundary=key.currentContext!.findRenderObject() as RenderRepaintBoundary;
      await t.runAsync(() async {
        final image=await boundary.toImage();final bytes=await image.toByteData(format:ui.ImageByteFormat.png);
        await File('../design/verification/tablet-$label.png').writeAsBytes(bytes!.buffer.asUint8List());image.dispose();
      });
      expect(t.takeException(),isNull);
    }
  },skip:!const bool.fromEnvironment('TABLET_VISUAL'));
}

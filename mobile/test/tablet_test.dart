import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/store.dart';
import 'package:kexinglu_mobile/look.dart';
import 'package:kexinglu_mobile/weather.dart';

void main() {
  late AtlasData atlas;
  setUpAll(() async {
    await CloudAccount.instance.initialize(configuration: {});
    atlas = AtlasData(); await atlas.load();
  });
  testWidgets('public weather humidity is displayed as a percentage once', (t) async {
    final store=JournalStore.memory();
    await store.setting('weather_public_cache',{'lat':24.48,'lon':118.08,'name':'厦门','stamp':'10/20',
      'data':{'temperature':{'value':25},'humidity':65,'condition':{'text':'晴','code':'100'}}});
    await t.pumpWidget(MaterialApp(home:Scaffold(body:WeatherPanel(store:store,palette:AppPalette.all.first))));
    await t.pumpAndSettle();
    expect(find.text('65%'),findsOneWidget);expect(find.text('6500%'),findsNothing);
    await t.pumpWidget(const SizedBox());
  });
  for (final size in [const Size(1280,800),const Size(1024,1366),const Size(800,1280),const Size(540,800)]) {
    testWidgets('tablet navigation, maps and resizing at $size', (t) async {
      t.view.physicalSize=size;t.view.devicePixelRatio=1;
      t.view.viewPadding=const FakeViewPadding(bottom:24);
      t.view.padding=const FakeViewPadding(bottom:24);
      addTearDown(t.view.resetViewPadding);addTearDown(t.view.resetPadding);
      addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
      final store=JournalStore.memory();
      await store.setting('reduced',true);
      await store.save(Entry('travel-test','travel',{'title':'厦门记录','city':'厦门'}));
      await store.save(Entry('ticket-test','ticket',{'mode':'air','from':'北京','to':'厦门','code':'CA1234'}));
      await t.pumpWidget(Kexinglu(store:store,atlas:atlas));await t.pumpAndSettle();
      expect(find.byKey(const ValueKey('tablet-home-columns')),size.width>=900?findsOneWidget:findsNothing);
      for (final label in ['旅途','票夹','收藏','我的']) {
        await t.tap(find.text(label).last);await t.pumpAndSettle();
        expect(t.takeException(),isNull,reason:label);
        if(label=='旅途'||label=='票夹') {
          expect(find.byKey(const ValueKey('tablet-map-workspace')),size.width>=900?findsOneWidget:findsNothing);
          expect(find.byType(RouteMap),findsOneWidget);
          if(size.width>=900) {
            final glass=find.descendant(of:find.byKey(const ValueKey('main-floating-navigation')),matching:find.byType(Glass));
            expect(t.getBottomRight(find.byType(RouteMap)).dy,lessThan(t.getTopLeft(glass).dy));
          }
        }
      }
      // Resize the same session like Android split screen; records and navigation survive.
      t.view.physicalSize=const Size(540,800);await t.pumpAndSettle();
      expect(find.text('我的'),findsWidgets);expect(store.entries.length,2);
      expect(t.takeException(),isNull);
    });
  }
}

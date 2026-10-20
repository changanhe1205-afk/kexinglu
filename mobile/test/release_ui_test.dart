import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/birthday.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/i18n.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/store.dart';

void main() {
  late AtlasData atlas;
  setUpAll(() async {await CloudAccount.instance.initialize(configuration:{}); atlas=AtlasData(); await atlas.load();});
  tearDown(() => AppLanguage.current='zh');
  test('birthday validates calendar date, leap day and future dates', () {
    expect(isBirthday('2000-10-19', DateTime(2026,10,19)),true);
    expect(isBirthday('2000-10-19', DateTime(2026,10,18)),false);
    expect(isBirthday('2000-02-29', DateTime(2026,2,28)),false);
    expect(isBirthday('2000-02-29', DateTime(2028,2,29)),true);
    expect(isBirthday('2001-02-29', DateTime(2028,3,1)),false);
    expect(isBirthday('2027-10-19', DateTime(2026,10,19)),false);
    expect(isBirthday('', DateTime(2026,10,19)),false);
  });
  testWidgets('birthday opens once, wish interaction and dismissal persist', (t) async {
    t.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    final store=JournalStore.memory();
    await store.setting('personal_profile:guest',{'birthday':'2000-10-19','nickname':'小行'});
    Widget app()=>MaterialApp(navigatorObservers:[birthdayRoutes],home:BirthdayGate(
      store:store,clock:()=>DateTime(2026,10,19),child:const Scaffold(body:Text('Home'))));
    await t.pumpWidget(app());await t.pumpAndSettle();
    expect(find.text('生日快乐, 小行'),findsOneWidget);
    await t.tap(find.byKey(const ValueKey('birthday-candles')));await t.pumpAndSettle();
    expect(find.text('愿你的心愿，在新一岁慢慢实现'),findsOneWidget);
    await t.tap(find.text('收下这份祝福'));await t.pumpAndSettle();
    expect(store.settings['birthday_seen:guest'],'2026-10-19');
    await t.pumpWidget(const SizedBox());await t.pumpWidget(app());await t.pumpAndSettle();
    expect(find.byType(BirthdayCard),findsNothing);
  });
  for(final mode in ['travel','air','rail']) {
    testWidgets('$mode map repaints vector overlays at gesture zoom', (t) async {
      await t.pumpWidget(MaterialApp(home:Scaffold(body:RouteMap(atlas:atlas,records:[],mode:mode,accent:Colors.teal))));
      final viewer=t.widget<InteractiveViewer>(find.byType(InteractiveViewer));
      viewer.transformationController!.value=Matrix4.identity()..scaleByDouble(4,4,1,1);
      await t.pump();
      final painters=t.widgetList<CustomPaint>(find.byType(CustomPaint)).map((w)=>w.painter).whereType<AtlasPainter>();
      expect(painters.single.zoom,4);
    });
  }
  for(final lang in ['en','ja','zh-TW']) {
    testWidgets('$lang navigation and profile update without changing records', (t) async {
      t.view.physicalSize=const Size(390,844);t.view.devicePixelRatio=1;
      addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
      final store=JournalStore.memory();
      await store.save(Entry('x','travel',{'title':'我的厦门旅行','city':'厦门'}));
      await store.setting('language',lang);
      await t.pumpWidget(Kexinglu(store:store,atlas:atlas));await t.pumpAndSettle();
      expect(find.text(tr('首页')),findsOneWidget);
      await t.tap(find.text(tr('我的')));await t.pumpAndSettle();
      expect(find.text(tr('账号与同步')),findsOneWidget);
      expect(store.entries.single.text('title'),'我的厦门旅行');
      expect(t.takeException(),isNull);
    });
  }
}

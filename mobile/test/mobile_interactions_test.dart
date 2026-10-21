import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/atlas.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/collection_screen.dart';
import 'package:kexinglu_mobile/look.dart';
import 'package:kexinglu_mobile/main.dart';
import 'package:kexinglu_mobile/profile_screen.dart';
import 'package:kexinglu_mobile/store.dart';
import 'package:kexinglu_mobile/weather.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const location = MethodChannel('flutter.baseflow.com/geolocator');
  late AtlasData atlas;
  final platformCalls = <MethodCall>[];
  setUpAll(() => CloudAccount.instance.initialize(configuration: {}));
  setUp(() async {
    atlas=AtlasData(); await atlas.load();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(location, (call) async {
      if (call.method == 'isLocationServiceEnabled') return true;
      return 0; // Denied: no device location or network needed.
    });
    platformCalls.clear();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
      platformCalls.add(call); return null;
    });
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(location, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null);
  });
  Future<void> screen(WidgetTester t, Widget child) async {
    t.view.physicalSize=const Size(390,844); t.view.devicePixelRatio=1;
    addTearDown(t.view.resetPhysicalSize); addTearDown(t.view.resetDevicePixelRatio);
    await t.pumpWidget(MaterialApp(home: Scaffold(body: child)));
    await t.pumpAndSettle();
  }
  for (final mode in ['travel','air']) {
    testWidgets('$mode map fullscreen supports pan zoom rotation and restores orientation', (t) async {
      await screen(t, SizedBox(height:280, child: RouteMap(atlas: atlas, records: [], mode: mode, accent: Colors.teal)));
      await t.tap(find.byTooltip('全屏地图')); await t.pumpAndSettle();
      expect(find.byTooltip('退出全屏地图'),findsOneWidget);
      final viewer=t.widget<InteractiveViewer>(find.byKey(const ValueKey('route-map-pan-zoom')).last);
      final chinaScale=viewer.transformationController!.value.getMaxScaleOnAxis();
      expect(chinaScale,greaterThan(1));
      await t.tap(find.byTooltip('放大地图')); await t.pumpAndSettle();
      expect(viewer.transformationController!.value.getMaxScaleOnAxis(), greaterThan(1));
      await t.drag(find.byKey(const ValueKey('route-map-pan-zoom')).last, const Offset(70,40)); await t.pumpAndSettle();
      expect(viewer.transformationController!.value.storage[12], isNot(0));
      await t.tap(find.byTooltip('复位地图')); await t.pumpAndSettle();
      expect(viewer.transformationController!.value.getMaxScaleOnAxis(),chinaScale);
      await t.tap(find.text('世界地图').last); await t.pumpAndSettle();
      expect(viewer.transformationController!.value.getMaxScaleOnAxis(),1);
      await t.tap(find.text('横屏')); await t.pumpAndSettle();
      expect(platformCalls.any((c) => c.method=='SystemChrome.setPreferredOrientations' && (c.arguments as List).contains('DeviceOrientation.landscapeLeft')),true);
      t.view.physicalSize=const Size(844,390); await t.pumpAndSettle();
      expect(t.takeException(),isNull);
      await t.tap(find.byTooltip('退出全屏地图')); await t.pumpAndSettle();
      expect(platformCalls.lastWhere((c)=>c.method=='SystemChrome.setPreferredOrientations').arguments,isEmpty);
    });
  }
  testWidgets('collection flips inline and pauses carousel while reading long notes', (t) async {
    final store=JournalStore.memory();
    await store.save(Entry('a','movie',{'title':'电影甲','note':'我的观看感悟','date':'2026-10-19','rating':4}));
    await store.save(Entry('b','movie',{'title':'电影乙','note':'另一条感悟'}));
    await screen(t, CollectionScreen(store:store,palette:AppPalette.all.first,reduced:false,
      photo: (e,{height})=>const ColoredBox(color:Colors.teal), card:(_)=>const SizedBox(),
      onEdit:(_,{entry}) async {}, onDetail:(_) async {fail('must not open bottom sheet');}));
    await t.tap(find.byType(FlipCard).first); await t.pumpAndSettle();
    expect(find.text('观看感悟'),findsOneWidget);
    expect(find.text(store.of('movie').first.text('note')),findsOneWidget);
    expect(find.byType(BottomSheet),findsNothing);
    final page=t.widget<PageView>(find.byType(PageView)).controller!;
    final before=page.page; await t.pump(const Duration(seconds:7)); await t.pumpAndSettle();
    expect(page.page,before);
    await t.tap(find.text('轻触空白处翻回封面')); await t.pumpAndSettle();
    expect(find.text('观看感悟'),findsNothing);
    expect(t.takeException(),isNull);
  });
  testWidgets('profile editor persists and settings/about remain collapsed by default', (t) async {
    final store=JournalStore.memory();
    await screen(t, PersonalProfile(store:store,palette:AppPalette.all.first));
    expect(find.text('系统主题'),findsNothing);
    expect(find.textContaining('Android · 1.0.0'),findsNothing);
    await t.tap(find.text('编辑资料')); await t.pumpAndSettle();
    Finder field(String label)=>find.byWidgetPredicate((w)=>w is TextField && w.decoration?.labelText==label);
    await t.enterText(field('昵称'),'小行'); await t.enterText(field('个性签名'),'记录生活');
    await t.tap(find.text('保存').first); await t.pumpAndSettle();
    expect(find.text('小行'),findsOneWidget); expect(find.text('记录生活'),findsOneWidget);
    expect(ProfileRepository(store,null).local['nickname'],'小行');
    await t.tap(find.text('设置')); await t.pumpAndSettle();
    expect(find.text('系统主题'),findsOneWidget);
    await t.tap(find.byIcon(Icons.arrow_back_rounded)); await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('数据备份'),150,scrollable:find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.tap(find.text('数据备份')); await t.pumpAndSettle();
    expect(find.text('导出本地备份'),findsOneWidget);
    expect(find.text('从备份导入'),findsOneWidget);
    await t.tap(find.byIcon(Icons.arrow_back_rounded)); await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('关于'),150,scrollable:find.byType(Scrollable).first);
    await t.pumpAndSettle();
    await t.tap(find.text('关于')); await t.pumpAndSettle();
    expect(find.textContaining('Android · 1.0.0'),findsOneWidget);
    expect(t.takeException(),isNull);
  });
  test('profile cache is isolated by account and offline guest needs no network', () async {
    final store=JournalStore.memory();
    await ProfileRepository(store,null).save({'nickname':'本地游客','birthday':'2000-10-05'});
    expect(ProfileRepository(store,'another-user').local,isEmpty);
    expect(ProfileRepository(store,null).local['birthday'],'2000-10-05');
  });
  testWidgets('location denial offers manual world city search without blocking home', (t) async {
    final store=JournalStore.memory();
    await screen(t, SingleChildScrollView(child:WeatherPanel(store:store,palette:AppPalette.all.first)));
    await t.tap(find.text('定位当地天气')); await t.pumpAndSettle();
    expect(find.textContaining('未获得定位权限'),findsOneWidget);
    expect(find.text('选择城市'),findsOneWidget);
    await t.tap(find.text('选择城市')); await t.pumpAndSettle();
    expect(find.text('选择天气城市'),findsOneWidget);
    expect(t.takeException(),isNull);
  });
  testWidgets('home removes brand header but retains floating navigation', (t) async {
    await t.pumpWidget(Kexinglu(store:JournalStore.memory(),atlas:atlas)); await t.pumpAndSettle();
    expect(find.text('客行录'),findsNothing);
    expect(find.byKey(const ValueKey('main-floating-navigation')),findsOneWidget);
    expect(find.text('天气'),findsOneWidget);
    await t.pumpWidget(const SizedBox());
  });
}

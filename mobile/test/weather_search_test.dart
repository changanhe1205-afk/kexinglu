import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/weather.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('bundled Chinese place index resolves cities and reverse geocoding', () async {
    final service = WeatherService();
    expect((await service.search('厦门')).map((p) => p.name), contains('厦门市'));
    expect((await service.search('阿克苏')).map((p) => p.name), contains('阿克苏地区'));
    expect((await service.search('龙岩')).map((p) => p.name), contains('龙岩市'));
    expect((await service.search('拉萨')).map((p) => p.name), contains('拉萨市'));
    // 县级 / 区级地名也必须能搜到（坐标沿用所属地级市）。
    expect((await service.search('义乌')).map((p) => p.name), contains('义乌市'));
    expect((await service.search('安溪')).map((p) => p.name), contains('安溪县'));
    expect((await service.search('石狮')).map((p) => p.name), contains('石狮市'));
    expect((await service.search('昆山')).map((p) => p.name), contains('昆山市'));
    expect(await service.reverseName(24.48, 118.08), contains('厦门'));
    expect(await service.reverseName(39.905, 116.405), contains('北京'));
  });
}

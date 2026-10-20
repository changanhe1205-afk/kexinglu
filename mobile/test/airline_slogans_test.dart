import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/airlines.dart';

void main() {
  test('airline slogans resolve by full name, short name and IATA code', () {
    expect(airlineSlogan('厦门航空'), '人生路漫漫，白鹭常相伴');
    expect(airlineSlogan('厦航'), '人生路漫漫，白鹭常相伴');
    expect(airlineSlogan('MF'), '人生路漫漫，白鹭常相伴');
    expect(airlineSlogan('四川航空'), '美丽川航，卓越时尚');
    expect(airlineSlogan('川航'), '美丽川航，卓越时尚');
    expect(airlineSlogan('东方航空'), '世界品味，东方魅力');
    expect(airlineSlogan('东航'), '世界品味，东方魅力');
    expect(airlineSlogan('国航'), '宾四海，礼天下');
    expect(airlineSlogan('南航'), '安全第一，顾客至上');
    expect(airlineSlogan('海航'), '相伴相惜，梦享飞行');
    expect(airlineSlogan('山航'), '厚道山航，品质飞翔');
    expect(airlineSlogan('深航'), '任何时候，自然体贴');
    expect(airlineSlogan('不知道的航空'), isNull);
    expect(airlineSlogan(''), isNull);
  });

  test('airline suggestions include major carriers', () {
    expect(airlineCandidates('厦'), contains('厦门航空'));
    expect(airlineCandidates('吉祥'), contains('吉祥航空'));
    expect(airlineCandidates('').length, 8);
  });
}

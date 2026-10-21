import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/poster_search.dart';

void main() {
  test('poster candidates reject fuzzy unrelated titles and preserve Chinese matching', () {
    expect(PosterSearch.matches('Deception', 'Inception'), isFalse);
    expect(PosterSearch.matches('exception', 'Inception'), isFalse);
    expect(PosterSearch.matches('Inception', 'inception'), isTrue);
    expect(PosterSearch.matches('流浪地球2', '流浪地球'), isTrue);
    expect(PosterSearch.matches('盗梦空间', ''), isFalse);
  });
}

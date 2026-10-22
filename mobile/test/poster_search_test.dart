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
  test('Wikipedia keeps screen posters and rejects people and soundtracks', () {
    final data = <String, dynamic>{'query': {'pages': {
      '1': {'title':'Inception','index':1,'pageimage':'Inception_poster.jpg','thumbnail':{'source':'https://upload.wikimedia.org/poster.jpg'},'terms':{'description':['2010 film directed by Christopher Nolan']}},
      '2': {'title':'Christopher Nolan','index':2,'pageimage':'portrait.jpg','thumbnail':{'source':'https://upload.wikimedia.org/person.jpg'},'terms':{'description':['British-American film director']}},
      '3': {'title':'Inception (soundtrack)','index':3,'thumbnail':{'source':'https://upload.wikimedia.org/album.jpg'}},
      '4': {'title':'瑯琊榜 (電視劇)','index':4,'pageimage':'Langyebang.jpg','thumbnail':{'source':'https://upload.wikimedia.org/series.jpg'},'terms':{'description':['2015年电视剧']}},
    }}};
    expect(PosterSearch.wikiResults(data,'en').map((r)=>r.title),['Inception','瑯琊榜 (電視劇)']);
  });
  test('Baidu parser requires a screen work and safe image URL', () {
    const html = '''<meta content="流浪地球_百度百科" property="og:title">
      <meta name='description' content='2019年科幻电影'>
      <meta property='og:image' content='https://example.com/poster.jpg?a=1&amp;b=2'>''';
    final rows=PosterSearch.baiduResults(html,'流浪地球',Uri.parse('https://baike.baidu.com/item/test'));
    expect(rows.single.image,'https://example.com/poster.jpg?a=1&b=2');
    expect(PosterSearch.baiduResults(html.replaceAll('2019年科幻电影','同名小说'),'流浪地球',Uri.parse('https://baike.baidu.com/item/test')),isEmpty);
    expect(PosterSearch.baiduResults('<title>验证访问</title>','流浪地球',Uri.parse('https://baike.baidu.com/item/test')),isEmpty);
  });
}

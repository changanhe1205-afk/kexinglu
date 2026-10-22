// ignore_for_file: avoid_print
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/poster_search.dart';
void main() { test('live poster sources and images', () async {
 for(final q in ['Inception','琅琊榜','流浪地球','狂飙']) {
 final watch=Stopwatch()..start();
 final report=await PosterSearch.search(q,refresh:true);
 print('$q: ${report.results.map((p)=>p.title).toList()} (${watch.elapsedMilliseconds} ms), failures: ${report.failures}');
 expect(report.results,isNotEmpty,reason:q);
 final b=await PosterSearch.fetch(Uri.parse(report.results.first.image),5242880,sourceUrl:report.results.first.url);
 expect(b.length,greaterThan(1000));
 }
 },skip:!const bool.fromEnvironment('POSTER_LIVE')); }

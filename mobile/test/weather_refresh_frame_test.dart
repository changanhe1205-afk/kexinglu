import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kexinglu_mobile/weather_refresh_frame.dart';

void main() {
  testWidgets('perimeter refresh keeps content size and stops after completion', (t) async {
    Widget app(bool busy) => MaterialApp(home: Scaffold(body: WeatherRefreshFrame(
      refreshing: busy, color: Colors.teal, child: const SizedBox(width: 320,height: 220,child: Text('23°')))));
    await t.pumpWidget(app(false));
    final size=t.getSize(find.byType(WeatherRefreshFrame));
    await t.pumpWidget(app(true)); await t.pump(const Duration(milliseconds:400));
    expect(t.getSize(find.byType(WeatherRefreshFrame)),size);
    expect(find.text('23°'),findsOneWidget);
    expect(find.byType(LinearProgressIndicator),findsNothing);
    expect(t.binding.hasScheduledFrame,isTrue);
    await t.pumpWidget(app(false));await t.pumpAndSettle();
    expect(t.binding.hasScheduledFrame,isFalse);
    expect(t.takeException(),isNull);
  });
  testWidgets('reduced motion refresh remains static', (t) async {
    await t.pumpWidget(const MaterialApp(home: WeatherRefreshFrame(refreshing:true,reduced:true,color:Colors.teal,child:SizedBox(width:320,height:220))));
    await t.pumpAndSettle();
    expect(t.binding.hasScheduledFrame,isFalse);
  });
}

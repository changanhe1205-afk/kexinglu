import 'i18n.dart';
import 'dart:async';

import 'cloud_account.dart';
import 'birthday.dart';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'atlas.dart';
import 'look.dart';
import 'shell.dart';
import 'store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  unawaited(CloudAccount.instance.initialize());
  runApp(const Launch());
}

class Launch extends StatefulWidget {
  const Launch({super.key});
  @override
  State<Launch> createState() => _LaunchState();
}

class _LaunchState extends State<Launch> {
  late Future<(JournalStore, AtlasData)> loading = load();
  Future<(JournalStore, AtlasData)> load() async {
    final atlas = AtlasData();
    await atlas.load();
    return (await JournalStore.open(), atlas);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
    future: loading,
    builder: (context, s) {
      if (s.hasData) return Kexinglu(store: s.data!.$1, atlas: s.data!.$2);
      return MaterialApp(
        home: Scaffold(
          backgroundColor: const Color(0xffedf2ec),
          body: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Image.asset('assets/app.png', width: 64),
                const SizedBox(height: 24),
                Text(
                  s.hasError ? '本地资料暂时未能打开' : '客行录',
                  style: const TextStyle(fontSize: 24),
                ),
                const SizedBox(height: 12),
                if (s.hasError)
                  FilledButton(
                    onPressed: () => setState(() => loading = load()),
                    child: const LocalText('重试，不清除数据'),
                  )
                else
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class Kexinglu extends StatelessWidget {
  final JournalStore store;
  final AtlasData atlas;
  const Kexinglu({super.key, required this.store, required this.atlas});
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: store,
    builder: (c, child) {
      final language = store.settings['language'];
      AppLanguage.current = AppLanguage.names.containsKey(language) ? language as String : 'zh';
      final p =
          AppPalette.all[(store.settings['theme'] as int? ?? 0).clamp(
            0,
            AppPalette.all.length - 1,
          )];
      return MaterialApp(
        title: '客行录',
        navigatorObservers: [birthdayRoutes],
        debugShowCheckedModeBanner: false,
        locale: AppLanguage.locale,
        supportedLocales: const [Locale('zh'), Locale('zh', 'TW'), Locale('en'), Locale('ja')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          useMaterial3: true,
          scaffoldBackgroundColor: p.background,
          colorScheme: ColorScheme.fromSeed(
            seedColor: p.accent,
            brightness: p.dark ? Brightness.dark : Brightness.light,
            surface: p.background,
            primary: p.accent,
            onSurface: p.ink,
          ),
          appBarTheme: AppBarTheme(
            backgroundColor: p.background,
            surfaceTintColor: Colors.transparent,
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: p.paper,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: BorderSide.none,
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 18,
            ),
          ),
          bottomSheetTheme: BottomSheetThemeData(
            backgroundColor: p.background,
            showDragHandle: true,
          ),
        ),
        home: BirthdayGate(store: store, child: JournalShell(store: store, atlas: atlas, palette: p)),
      );
    },
  );
}

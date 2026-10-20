import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class SecureSession extends LocalStorage {
  final String key;
  const SecureSession(this.key);
  static const vault = FlutterSecureStorage();
  @override
  Future<void> initialize() async {}
  @override
  Future<String?> accessToken() => vault.read(key: key);
  @override
  Future<bool> hasAccessToken() async => await accessToken() != null;
  @override
  Future<void> persistSession(String value) =>
      vault.write(key: key, value: value);
  @override
  Future<void> removePersistedSession() => vault.delete(key: key);
}

class CloudAccount extends ChangeNotifier {
  static final instance = CloudAccount();
  SupabaseClient? client;
  bool githubEnabled = false;
  final Set<String> enabledProviders = {};
  static const providerNames = {'github': 'GitHub', 'google': 'Google', 'azure': 'Microsoft', 'discord': 'Discord', 'gitlab': 'GitLab'};
  Future<void> refreshProviders() async {
    final http = HttpClient()..connectionTimeout = const Duration(seconds: 8);
    try {
      final config = jsonDecode(await rootBundle.loadString('assets/cloud.json')) as Map;
      final request = await http.getUrl(Uri.parse('${config['url']}/auth/v1/settings')).timeout(const Duration(seconds: 8));
      request.headers.set('apikey', '${config['publishableKey']}');
      final response = await request.close().timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) return;
      final result = jsonDecode(await response.transform(utf8.decoder).join().timeout(const Duration(seconds: 8))) as Map;
      final external = result['external'];
      if (external is! Map) return;
      enabledProviders.clear();
      enabledProviders.addAll(providerNames.keys.where((name) => external[name] == true));
      githubEnabled = enabledProviders.contains('github');
      notifyListeners();
    } catch (_) { /* Offline: retain the last verified list for this session. */ }
    finally {http.close(force: true);}
  }
  String? setupError;
  Future<void>? _initializing;
  bool initialized = false;
  bool get configured => client != null;
  String? get uid => client?.auth.currentUser?.id;
  String? get email => client?.auth.currentUser?.email;
  Future<void> initialize({Map<String, dynamic>? configuration}) =>
      _initializing ??= _load(configuration);
  Future<void> _load(Map<String, dynamic>? configuration) async {
    try {
      final config = configuration ??
          jsonDecode(await rootBundle.loadString('assets/cloud.json')) as Map;
      final url = config['url'] as String? ?? '';
      final key = config['publishableKey'] as String? ?? '';
      if (url.isEmpty || key.isEmpty) return;
      final uri = Uri.parse(url);
      if (uri.scheme != 'https' ||
          uri.host.isEmpty ||
          key.startsWith('sb_secret_')) {
        throw const FormatException('云端配置无效');
      }
      if (!key.startsWith('sb_publishable_')) {
        final claims = jsonDecode(
          utf8.decode(base64Url.decode(base64Url.normalize(key.split('.')[1]))),
        );
        if (claims['role'] != 'anon') throw const FormatException('禁止使用管理密钥');
      }
      await Supabase.initialize(
        url: url,
        publishableKey: key,
        authOptions: FlutterAuthClientOptions(
          authFlowType: AuthFlowType.pkce,
          localStorage: SecureSession('kexinglu-session-${uri.host}'),
          detectSessionInUriPredicate: (u) =>
              u.scheme == 'com.changanhe.kexinglu' &&
              u.host == 'login-callback',
        ),
      );
      client = Supabase.instance.client;
      githubEnabled = config['githubEnabled'] == true;
      unawaited(refreshProviders());
      client!.auth.onAuthStateChange.listen(
        (event) => notifyListeners(),
        onError: (Object error) {
          setupError = '登录会话需要重新验证';
          notifyListeners();
        },
      );
    } catch (_) {
      setupError = '云端暂不可用，本地记录仍可正常使用';
    } finally {
      initialized = true;
      notifyListeners();
    }
  }

  Future<void> github() async {
    return social('github');
  }
  Future<void> social(String name) async {
    if (!enabledProviders.contains(name) || client == null) throw StateError('该登录方式尚未启用');
    final provider = {'github': OAuthProvider.github, 'google': OAuthProvider.google,
      'azure': OAuthProvider.azure, 'discord': OAuthProvider.discord, 'gitlab': OAuthProvider.gitlab}[name]!;
    final opened = await client!.auth.signInWithOAuth(
      provider,
      scopes: name == 'azure' ? 'email' : null,
      redirectTo: 'com.changanhe.kexinglu://login-callback',
    );
    if (!opened) throw StateError('浏览器未能打开');
  }
}

import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kexinglu_mobile/cloud_account.dart';
import 'package:kexinglu_mobile/profile_screen.dart';
import 'package:kexinglu_mobile/store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('profile metadata round-trips and remains separate from journal records', () async {
    Map<String,dynamic> metadata={};
    final user={'id':'profile-owner','aud':'authenticated','app_metadata':{},'created_at':'2026-01-01T00:00:00Z'};
    final client=SupabaseClient('https://test.supabase.co','test-public',
      authOptions:const AuthClientOptions(autoRefreshToken:false),
      httpClient:MockClient((req) async {
        expect(req.url.path,'/auth/v1/user');
        if(req.method=='PUT') metadata=Map<String,dynamic>.from(jsonDecode(req.body)['data']);
        return http.Response(jsonEncode({...user,'user_metadata':metadata}),200,
          headers:{'content-type':'application/json'},request:req);
      }));
    addTearDown(() async {CloudAccount.instance.client=null; await client.dispose();});
    final exp=DateTime.now().millisecondsSinceEpoch~/1000+3600;
    String part(Map<String,dynamic> v)=>base64Url.encode(utf8.encode(jsonEncode(v))).replaceAll('=','');
    await client.auth.recoverSession(jsonEncode({'access_token':'${part({'alg':'HS256'})}.${part({'sub':'profile-owner','exp':exp})}.test',
      'refresh_token':'test-refresh','token_type':'bearer','expires_in':3600,'user':{...user,'user_metadata':{}}}));
    CloudAccount.instance.client=client;
    final local=JournalStore.memory();
    final profile={'nickname':'小行','signature':'旅行与日常','birthday':'2000-10-05','gender':'不公开','cover':'preset:sea.svg','avatar':''};
    expect(await ProfileRepository(local,'profile-owner').save(profile),true);
    expect(metadata['kexinglu_profile'],profile);
    final second=JournalStore.memory();
    expect(await ProfileRepository(second,'profile-owner').load(),profile);
    expect(second.entries,isEmpty);
    expect(ProfileRepository(second,'someone-else').local,isEmpty);
  });
  test('account change keeps edits pending without sending to another account',() async {
    final local=JournalStore.memory();
    CloudAccount.instance.client=null;
    expect(await ProfileRepository(local,'old-account').save({'nickname':'保留的编辑'}),false);
    expect(ProfileRepository(local,'old-account').local['pending'],true);
    expect(ProfileRepository(local,'old-account').local['nickname'],'保留的编辑');
    expect(ProfileRepository(local,'new-account').local,isEmpty);
  });
}

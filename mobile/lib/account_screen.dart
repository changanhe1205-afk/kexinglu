import 'i18n.dart';
import 'package:flutter/services.dart';

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'cloud_account.dart';
import 'cloud_sync.dart';
import 'store.dart';
import 'package:flutter_svg/flutter_svg.dart';

class AccountScreen extends StatefulWidget {
  final JournalStore store;
  const AccountScreen({super.key, required this.store});
  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  final cloud = CloudAccount.instance;
  final email = TextEditingController(),
      password = TextEditingController(),
      code = TextEditingController();
  bool busy = false, otp = false, register = false, reveal = false;
  int cooldown = 0;
  Timer? timer;
  final codeFocus = FocusNode();
  String message = '';
  String syncStage = '正在连接服务';
  int syncDone = 0, syncTotal = 0, elapsed = 0;
  Timer? progressTimer;
  @override
  void initState() {
    super.initState();
    cloud.initialize();
    cloud.refreshProviders();
    message = widget.store.settings['cloud_last_result'] as String? ?? '';
  }

  @override
  void dispose() {
    timer?.cancel();
    progressTimer?.cancel();
    email.dispose();
    password.dispose();
    code.dispose();
    codeFocus.dispose();
    super.dispose();
  }

  Future<void> act(Future<void> Function() action, String success) async {
    if (busy || !cloud.configured) return;
    FocusScope.of(context).unfocus();
    setState(() {
      busy = true;
      message = '';
      syncStage = '正在连接服务';
      syncDone = syncTotal = elapsed = 0;
    });
    progressTimer?.cancel();
    progressTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => elapsed++);
    });
    try {
      await action();
      if (mounted) {
        setState(() {
          if (success.isNotEmpty) message = success;
        });
      }
    } on AuthException catch (e) {
      if (mounted) {
        setState(
          () => message = switch (e.code) {
            'invalid_credentials' => '邮箱或密码不正确，请重试。',
            'email_not_confirmed' => '请先完成邮箱验证，也可以使用邮箱验证码登录。',
            'otp_expired' => '验证码错误或已过期，请重新获取。',
            'user_already_exists' ||
            'email_exists' => '这个邮箱已经注册过了，可以直接登录，或使用验证码登录。',
            'weak_password' => '密码强度不足，请至少 8 位并包含字母和数字。',
            'signup_disabled' => '当前暂未开放注册，请稍后再试。',
            'otp_disabled' => '当前暂未开放邮箱验证码登录，请使用密码登录。',
            'over_email_send_rate_limit' ||
            'over_request_rate_limit' => '请求较频繁，请稍后重试。',
            _ => '登录未完成，请检查邮箱、验证码及云端配置后重试。',
          },
        );
      }
    } on StateError catch (e) {
      if (mounted) setState(() => message = e.message);
    } on PostgrestException catch (e) {
      if (mounted) setState(() => message = '云端读写失败（${e.code ?? '未知状态'}），请重试。');
    } on StorageException catch (e) {
      if (mounted) {
        setState(() => message = '图片传输失败（${e.statusCode ?? '未知状态'}），请重试。');
      }
    } on FormatException catch (e) {
      if (mounted) setState(() => message = e.message);
    } catch (_) {
      if (mounted) setState(() => message = '网络或登录服务暂不可用，本地内容不受影响。');
    } finally {
      progressTimer?.cancel();
      if (mounted) setState(() => busy = false);
    }
  }

  bool validEmail() {
    if (RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email.text.trim())) {
      return true;
    }
    setState(() => message = '请输入完整邮箱地址');
    return false;
  }

  Future<void> send() async {
    if (!validEmail() || cooldown > 0) return;
    await act(() async {
      await cloud.client!.auth.signInWithOtp(email: email.text.trim());
      if (!mounted) return;
      setState(() => cooldown = 60);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && otp) codeFocus.requestFocus();
      });
      timer?.cancel();
      timer = Timer.periodic(const Duration(seconds: 1), (t) {
        if (!mounted || cooldown <= 1) {
          t.cancel();
          if (mounted) setState(() => cooldown = 0);
        } else {
          setState(() => cooldown--);
        }
      });
    }, '验证码已请求发送，请检查邮箱及垃圾邮件。');
  }

  Future<void> submit() async {
    if (!validEmail()) return;
    if (!otp && password.text.length < 8) {
      setState(() => message = '密码至少 8 位');
      return;
    }
    if (otp && !RegExp(r'^\d{6,10}$').hasMatch(code.text.trim())) {
      setState(() => message = '请输入邮件中的验证码');
      return;
    }
    await act(() async {
      final auth = cloud.client!.auth;
      if (otp) {
        await auth.verifyOTP(
          email: email.text.trim(),
          token: code.text.trim(),
          type: OtpType.email,
        );
      } else if (register) {
        final result = await auth.signUp(
          email: email.text.trim(),
          password: password.text,
        );
        if (mounted) {
          setState(() => message = result.session == null
              ? '注册成功，请到邮箱点击确认链接后再登录；没收到可以点“重发确认邮件”。'
              : '注册成功，已自动登录。');
        }
      } else {
        await auth.signInWithPassword(
          email: email.text.trim(),
          password: password.text,
        );
      }
      password.clear();
      code.clear();
    }, register && !otp ? '' : '登录成功。开启同步前会确认本地资料的归属。');
  }

  Future<void> reset() async {
    if (!validEmail()) return;
    await act(() async {
      await cloud.client!.auth.resetPasswordForEmail(
        email.text.trim(),
        redirectTo: 'com.changanhe.kexinglu://login-callback',
      );
    }, '重置邮件已发送，请到邮箱点击链接；回到 App 后在“账号安全”里设置新密码。');
  }

  Future<void> resendConfirmation() async {
    if (!validEmail()) return;
    await act(() async {
      await cloud.client!.auth.resend(
        email: email.text.trim(),
        type: OtpType.signup,
      );
    }, '确认邮件已重新发送，请检查邮箱和垃圾邮件。');
  }

  Future<void> synchronize() async {
    final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: const LocalText('同步当前资料库？'),
      content: LocalText('将本机记录与 ${cloud.email ?? "当前账号"} 的云端资料合并。两端修改冲突会保留。'),
      actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const LocalText('取消')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const LocalText('确认并同步'))],
    ));
    if (yes != true || !mounted) return;
    await act(() async {
      message = await CloudSync(widget.store, onProgress: (stage, done, total) {
        if (mounted) setState(() {syncStage = stage; syncDone = done; syncTotal = total;});
      }).run();
    }, '');
  }

  Widget passwordField({bool setting = false}) => TextField(
    controller: password, obscureText: !reveal, enabled: !busy,
    autofillHints: [setting || register ? AutofillHints.newPassword : AutofillHints.password],
    onSubmitted: setting ? null : (_) => submit(),
    decoration: InputDecoration(labelText: setting ? '新密码（至少 8 位）' : '密码（至少 8 位）',
      suffixIcon: IconButton(tooltip: reveal ? '隐藏密码' : '显示密码',
        onPressed: () => setState(() => reveal = !reveal),
        icon: Icon(reveal ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 20))),
  );

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: cloud,
    builder: (context, _) {
      final colors = Theme.of(context).colorScheme;
      final signedIn = cloud.uid != null;
      final secondary = colors.onSurface.withValues(alpha: .58);
      final border = OutlineInputBorder(borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.onSurface.withValues(alpha: .12)));
      return Scaffold(
        appBar: AppBar(title: const LocalText('账号与同步', style: TextStyle(fontSize: 17)), centerTitle: false),
        body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 480),
          child: Theme(data: Theme.of(context).copyWith(
            inputDecorationTheme: InputDecorationTheme(filled: true, fillColor: colors.surface,
              border: border, enabledBorder: border, focusedBorder: border.copyWith(
                borderSide: BorderSide(color: colors.primary, width: 1.5)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18)),
          ), child: AutofillGroup(child: ListView(
            padding: const EdgeInsets.fromLTRB(28, 28, 28, 32), children: [
              Center(child: Container(padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: colors.primary.withValues(alpha: .08), borderRadius: BorderRadius.circular(20)),
                child: SvgPicture.asset('assets/app-mark.svg', width: 32, height: 32,
                  colorFilter: ColorFilter.mode(colors.primary, BlendMode.srcIn)))),
              const SizedBox(height: 20),
              LocalText(signedIn ? '你的客行录' : register && !otp ? '创建客行录账号' : '登录客行录',
                textAlign: TextAlign.center, style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              LocalText(signedIn ? cloud.email ?? '已登录' : '在不同设备，继续同一段旅途。',
                textAlign: TextAlign.center, style: TextStyle(color: secondary, height: 1.6)),
              const SizedBox(height: 30),
              if (!cloud.configured) const LocalText('云端暂不可用，本地资料仍可正常使用。'),
              if (cloud.setupError != null) Text(cloud.setupError!),
              if (!signedIn) ...[
                SegmentedButton<bool>(showSelectedIcon: false,
                  style: SegmentedButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    side: BorderSide(color: colors.onSurface.withValues(alpha: .1)),
                    selectedBackgroundColor: colors.primary.withValues(alpha: .09), selectedForegroundColor: colors.primary),
                  segments: const [ButtonSegment(value: false, label: LocalText('密码登录')),
                    ButtonSegment(value: true, label: LocalText('验证码登录'))],
                  selected: {otp}, onSelectionChanged: busy ? null : (v) => setState(() {otp = v.first; register = false; message = ''; }),
                ),
                const SizedBox(height: 24),
                TextField(controller: email, enabled: !busy, keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email], textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(labelText: '邮箱账号', hintText: 'name@example.com')),
                const SizedBox(height: 16),
                if (otp) TextField(controller: code, focusNode: codeFocus, enabled: !busy,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  textInputAction: TextInputAction.done,
                  keyboardType: TextInputType.number, autofillHints: const [AutofillHints.oneTimeCode],
                  onSubmitted: (_) => submit(),
                  decoration: InputDecoration(labelText: '邮件验证码', suffixIcon: TextButton(
                    onPressed: busy || cooldown > 0 || !cloud.configured ? null : send,
                    child: Text(cooldown > 0 ? '${cooldown}s 后重发' : '获取验证码'))))
                else passwordField(),
                if (!otp) Align(alignment: Alignment.centerRight, child: TextButton(
                  onPressed: busy ? null : reset,
                  child: const LocalText('忘记密码？'))),
                const SizedBox(height: 14),
                SizedBox(height: 50, child: FilledButton(
                  style: FilledButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: busy || !cloud.configured ? null : submit,
                  child: LocalText(busy ? '处理中…' : register && !otp ? '创建账号' : '登录'))),
                const SizedBox(height: 10),
                Center(child: TextButton(onPressed: busy ? null : () => setState(() {
                  otp = false; register = !register; message = '';
                }), child: LocalText(register && !otp ? '已有账号？ 登录' : '还没有账号？ 注册'))),
                if (register && !otp) Center(child: TextButton(
                  onPressed: busy ? null : resendConfirmation,
                  child: const LocalText('没收到确认邮件？重发一次'))),
                for (final provider in CloudAccount.providerNames.entries)
                  if (cloud.enabledProviders.contains(provider.key)) Padding(
                    padding: const EdgeInsets.only(top: 8), child: OutlinedButton.icon(
                      onPressed: busy ? null : () => act(() => cloud.social(provider.key), '请在浏览器完成授权后返回。'),
                      icon: const Icon(Icons.open_in_browser_rounded), label: LocalText('${provider.value} 登录'))),
              ] else ...[
                Container(padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: colors.primary.withValues(alpha: .06), borderRadius: BorderRadius.circular(18)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const LocalText('资料同步', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    LocalText('本机 ${widget.store.entries.length} 条记录', style: TextStyle(color: secondary)),
                    const SizedBox(height: 18),
                    SizedBox(width: double.infinity, height: 48, child: FilledButton.icon(
                      onPressed: busy ? null : synchronize, icon: const Icon(Icons.sync_rounded),
                      label: LocalText(busy ? '同步处理中…' : '同步当前资料库'))),
                  ])),
                const SizedBox(height: 16),
              ],
              if (busy) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(value: syncTotal > 0 ? syncDone / syncTotal : null, borderRadius: BorderRadius.circular(4)),
                const SizedBox(height: 8),
                LocalText('$syncStage${syncTotal > 0 ? ' · $syncDone/$syncTotal 条' : ''} · 已用时 $elapsed 秒',
                  style: TextStyle(fontSize: 12, color: secondary)),
              ],
              if (message.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  if (signedIn && message.contains('\n')) ...[
                    Text(message.split('\n').first, style: TextStyle(fontSize: 13, height: 1.65, color: colors.onSurface)),
                    ExpansionTile(tilePadding: EdgeInsets.zero,
                      title: const LocalText('查看完整结果', style: TextStyle(fontSize: 13)),
                      children: [Align(alignment: Alignment.centerLeft,
                        child: SelectableText(message, style: TextStyle(fontSize: 12, height: 1.65, color: secondary)))])
                  ] else SelectableText(message, style: TextStyle(fontSize: 13, height: 1.65, color: colors.onSurface)),
                  if (signedIn) TextButton.icon(icon: const Icon(Icons.copy_rounded, size: 16),
                    label: const LocalText('复制完整结果'), onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: message));
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: LocalText('完整结果已复制'), duration: Duration(seconds: 2)));
                    }),
                ])),
              if (signedIn) ...[
                ExpansionTile(tilePadding: EdgeInsets.zero, title: const LocalText('账号安全', style: TextStyle(fontSize: 14)),
                  children: [passwordField(setting: true),
                    Align(alignment: Alignment.centerRight, child: TextButton(onPressed: busy ? null : () => act(() async {
                      if (password.text.length < 8) throw const FormatException('密码至少 8 位');
                      await cloud.client!.auth.updateUser(UserAttributes(password: password.text));
                      password.clear();
                    }, '密码已更新'), child: const LocalText('更新密码')))]),
                TextButton(onPressed: busy ? null : () => act(() async {
                  await cloud.client!.auth.signOut(scope: SignOutScope.local);
                }, '已退出，本机记录保留'), child: const LocalText('退出登录')),
              ],
              const SizedBox(height: 24),
              Divider(color: colors.onSurface.withValues(alpha: .08)),
              const SizedBox(height: 12),
              LocalText('资料保留在本机，登录后可手动同步。', textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, height: 1.6, color: secondary)),
            ],
          ))),
        )),
      );
    },
  );
}

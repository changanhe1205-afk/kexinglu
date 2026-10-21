"""Desktop account panel; network work is dispatched off the UI loop."""
from i18n import tr
import asyncio
import re
import queue
import time
import flet as ft
import theme
from cloud_client import current_client, CloudError
from profile_account_editor import open_editor


def build(page):
    try:
        cloud = current_client()
    except CloudError:
        return theme.glass_card(ft.Text('云端配置无效，本地内容仍可使用'), padding=22)
    field_style = dict(border_radius=12, border_color=theme.LINE, focused_border_color=theme.ACCENT,
                       bgcolor=theme.CARD_BG, text_size=14, content_padding=16)
    email = ft.TextField(label=tr('邮箱账号'), hint_text='name@example.com', keyboard_type=ft.KeyboardType.EMAIL, **field_style)
    password = ft.TextField(label=tr('密码（至少 8 位）'), password=True, can_reveal_password=True, **field_style)
    token = ft.TextField(label=tr('邮件验证码'), expand=True, **field_style)
    new_password = ft.TextField(label=tr('新密码（至少 8 位）'), password=True, can_reveal_password=True, **field_style)
    mode = 'password'
    message = ft.Text('', size=12, color=theme.TEXT_SUB, selectable=True)
    identity = ft.Text(cloud.email or '登录后，可手动同步两端资料', size=13, color=theme.TEXT_MAIN)
    avatar_badge = ft.Container(width=48, height=48, border_radius=24,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Icon(ft.Icons.PERSON_OUTLINE, color=theme.ACCENT))
    buttons = []
    busy = False
    resend_until = 0.0
    updates=queue.SimpleQueue()
    progress=ft.ProgressBar(value=None,visible=False)
    progress_text=ft.Text("",size=12,color=theme.TEXT_SUB)
    stage="正在连接服务"
    done=total=0

    def refresh():
        identity.value = cloud.email or '登录后，可手动同步两端资料'
        if cloud.uid:
            from cloud_profile import ProfileRepository
            profile = ProfileRepository(cloud).local()
            identity.value = ' · '.join(v for v in [profile.get('nickname') or cloud.email, profile.get('signature')] if v)
            avatar_badge.content = ft.Image(src=profile['avatar'], fit=ft.BoxFit.COVER) if profile.get('avatar') else ft.Icon(ft.Icons.PERSON_OUTLINE, color=theme.ACCENT)
        else:
            avatar_badge.content = ft.Icon(ft.Icons.PERSON_OUTLINE, color=theme.ACCENT)
        for button, enabled in buttons:
            button.disabled = busy or not cloud.configured or not enabled()
        paint_form()
        page.update()

    async def run(fn, success):
        nonlocal busy,stage,done,total
        if busy:
            return
        while not updates.empty():updates.get_nowait()
        busy = True
        message.value = '正在处理…'
        stage='正在连接服务';done=total=0
        progress.visible=True;progress.value=None
        started=time.monotonic()
        refresh()
        try:
            task=asyncio.create_task(asyncio.to_thread(fn))
            while not task.done():
                while not updates.empty():stage,done,total=updates.get_nowait()
                elapsed=int(time.monotonic()-started)
                progress.value=done/total if total else None
                progress_text.value=f'{stage}'+(f' · {done}/{total} 条' if total else '')+f' · 已用时 {elapsed} 秒'
                page.update()
                await asyncio.wait({task},timeout=.25)
            result=await task
            message.value = success(result) if callable(success) else success
            if cloud.uid:
                password.value = ''
                token.value = ''
        except CloudError as exc:
            message.value = str(exc)
        except Exception:
            message.value = '操作未完成，本地记录保留，请检查网络和云端配置。'
        finally:
            new_password.value = ''
            busy = False
            progress.visible=False
            progress_text.value=f'本次用时 {int(time.monotonic()-started)} 秒'
            refresh()

    def action(label, make_call, success, *, needs_email=False, enabled=lambda: True):
        def click(e):
            email.value = (email.value or '').strip()
            if needs_email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email.value or ''):
                message.value = '请输入完整邮箱地址'
                page.update()
                return
            page.run_task(run, make_call(email.value, password.value, token.value), success)
        button = ft.FilledButton(label, on_click=click, height=46,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            disabled=not cloud.configured or not enabled())
        buttons.append((button, enabled))
        return button

    login = action(tr('账号密码登录'), lambda e,p,t: lambda: cloud.password_login(e,p), tr('登录成功'), needs_email=True)
    register = action(tr('注册邮箱账号'), lambda e,p,t: lambda: cloud.register(e,p), '请查收邮箱验证邮件，再登录。', needs_email=True)
    async def resend_countdown():
        while time.monotonic() < resend_until:
            send.content = f'{max(1, int(resend_until-time.monotonic())+1)} 秒后重发'
            refresh()
            await asyncio.sleep(1)
        send.content = '发送验证码'
        refresh()

    def code_sent(result):
        nonlocal resend_until
        resend_until = time.monotonic()+60
        page.run_task(resend_countdown)
        return '验证码已发送，请查收邮箱及垃圾邮件。'

    send = action(tr('发送验证码'), lambda e,p,t: lambda: cloud.send_code(e), code_sent,
        needs_email=True, enabled=lambda: time.monotonic() >= resend_until)
    verify = action(tr('验证码登录'), lambda e,p,t: lambda: cloud.verify_code(e,t), tr('登录成功'), needs_email=True)
    provider_buttons=[]
    for provider,label in [('github','GitHub'),('google','Google'),('azure','Microsoft'),('discord','Discord'),('gitlab','GitLab')]:
        button=action(label+' 登录', lambda e,p,t,name=provider: lambda: cloud.social_login(name), tr('登录成功'),
                      enabled=lambda name=provider: name in cloud.enabled_providers)
        button.visible=provider in cloud.enabled_providers
        provider_buttons.append((provider,button))
    github = ft.Column(controls=[button for _,button in provider_buttons], spacing=8)
    logout = action(tr('退出登录'), lambda e,p,t: cloud.logout, tr('已退出，本机记录保留'), enabled=lambda: bool(cloud.uid))
    update = action(tr('设置 / 更新密码'), lambda e,p,t: lambda: cloud.set_password(new_password.value), '密码已更新', enabled=lambda: bool(cloud.uid))

    def sync_click(e):
        from desktop_sync import sync_now
        def complete(result):
            if hasattr(page, 'invalidate_cloud_views'):
                page.invalidate_cloud_views()
            failures=result.get('failures',[])
            summary=f"本轮上传 {result['uploaded']} 条、下载 {result['downloaded']} 条；云端现有 {result.get('cloud_records',0)} 条。冲突 {len(result['conflicts'])} 条。"
            if failures:
                names={'travel':'旅行','ticket':'票根','food':'食光','movie':'影视','book':'手账'}
                detail='；'.join(f"{names.get(f['key'][0],f['key'][0])} #{f['key'][1]}：{f['reason']}" for f in failures[:3])
                summary+=f"还有 {len(failures)} 条未完成，请重试。"+detail
            elif not result.get('cloud_records'):
                summary+='云端暂时没有记录，请先在有资料的设备上同步。'
            return summary
        def confirmed(e):
            page.pop_dialog()
            page.run_task(run, lambda: sync_now(cloud, True, lambda *item: updates.put(item)), complete)
        page.show_dialog(ft.AlertDialog(
            title=ft.Text('开启两端同步？'),
            content=ft.Text('将旅行、票根、收藏、手账及照片绑定到当前账号并同步。两端冲突不直接覆盖；首次同步前自动保留数据库副本。'),
            actions=[ft.TextButton(tr('暂不开启'), on_click=lambda e: page.pop_dialog()), ft.TextButton(tr('确认并同步'), on_click=confirmed)]))
    sync = ft.FilledButton(tr('同步当前资料库'), icon=ft.Icons.SYNC, height=46, on_click=sync_click, disabled=not cloud.uid)
    buttons.append((sync, lambda: bool(cloud.uid)))
    title = ft.Text('登录客行录', size=26, weight=ft.FontWeight.W_600, color=theme.TEXT_MAIN)
    subtitle = ft.Text('在不同设备，继续同一段旅途。', size=12, color=theme.TEXT_SUB)
    def choose(value):
        nonlocal mode
        if busy: return
        mode = value
        message.value = ''
        refresh()
    password_tab = ft.TextButton(tr('密码登录'), expand=True, on_click=lambda e: choose('password'))
    otp_tab = ft.TextButton(tr('验证码登录'), expand=True, on_click=lambda e: choose('otp'))
    tabs = ft.Container(bgcolor=theme.CARD_BG_SOFT, border_radius=12, padding=4,
                        content=ft.Row([password_tab, otp_tab], spacing=4))
    forgot = ft.Row(alignment=ft.MainAxisAlignment.END, controls=[
        ft.TextButton(tr('忘记密码？'), on_click=lambda e: choose('otp'))])
    register_link = ft.TextButton(tr('还没有账号？ 注册'),
        on_click=lambda e: choose('password' if mode == 'register' else 'register'))
    code_row = ft.Row([token, send], spacing=8)
    for button in (login, register, verify): button.width = 380
    login.content = '登录'; register.content = '创建账号'; verify.content = '登录'
    form = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[tabs, email, password, code_row, forgot, login, register, verify,
                  ft.Row([register_link], alignment=ft.MainAxisAlignment.CENTER), github])
    password_settings = ft.ExpansionTile(title=ft.Text(tr('账号安全'), size=14),
        controls=[new_password, update], tile_padding=0)
    manage = ft.Column(spacing=16, controls=[
        ft.OutlinedButton('编辑个人资料', icon=ft.Icons.EDIT_OUTLINED,
            on_click=lambda e: open_editor(page, cloud, refresh)),
        ft.Text(tr('资料同步'), size=18, weight=ft.FontWeight.W_600, color=theme.TEXT_MAIN),
        ft.Text('合并旅行、票根、收藏与手账，保留两端修改冲突。', size=12, color=theme.TEXT_SUB),
        sync, password_settings, logout])
    result_summary = ft.Text('', size=13, color=theme.TEXT_MAIN)
    details = ft.ExpansionTile(title=ft.Text(tr('查看完整结果'),size=12),
        controls=[message], tile_padding=0)
    status = ft.Column(spacing=8, controls=[progress, progress_text, result_summary, details])
    entry_button = ft.FilledButton(tr('登录账号'), icon=ft.Icons.PERSON_OUTLINE, height=40)
    def paint_form():
        signed = bool(cloud.uid)
        value = message.value or ''
        result_summary.value = value.split('\n')[0] if len(value) <= 160 else value[:160]+'…'
        details.visible = '\n' in value or len(value) > 160
        form.visible = not signed
        manage.visible = signed
        title.value = '你的客行录' if signed else ('创建客行录账号' if mode == 'register' else '登录客行录')
        subtitle.value = cloud.email if signed else '在不同设备，继续同一段旅途。'
        password.visible = mode != 'otp'; code_row.visible = mode == 'otp'; forgot.visible = mode != 'otp'
        login.visible = mode == 'password'; register.visible = mode == 'register'; verify.visible = mode == 'otp'
        github.visible = bool(cloud.enabled_providers)
        for provider,button in provider_buttons: button.visible=provider in cloud.enabled_providers
        status.visible = busy or bool(message.value) or bool(progress_text.value)
        register_link.content = '已有账号？ 登录' if mode == 'register' else '还没有账号？ 注册'
        for tab, active in [(password_tab,mode != 'otp'),(otp_tab,mode == 'otp')]:
            tab.style = ft.ButtonStyle(color=theme.ACCENT if active else theme.TEXT_SUB,
                bgcolor=theme.CARD_BG if active else '#00000000', shape=ft.RoundedRectangleBorder(radius=9))
            tab.disabled = busy
        for field in (email,password,token,new_password): field.disabled = busy
        entry_button.content = '管理账号' if signed else '登录账号'
    intro = ft.Container(col={'xs':12,'md':4}, padding=ft.Padding.only(right=24,top=32),
        content=ft.Column(spacing=18,controls=[theme.brand_mark(46),
            ft.Text(tr('客行录'), size=32, weight=ft.FontWeight.W_500, color=theme.TEXT_MAIN),
            ft.Text('把日子，慢慢收藏。', size=14, color=theme.TEXT_SUB)]))
    panel = ft.Container(col={'xs':12,'md':8}, padding=28, border_radius=20,
        bgcolor=theme.CARD_BG, border=ft.Border.all(1,theme.LINE),
        content=ft.Column(spacing=18, controls=[title,subtitle,form,manage,status,
            ft.Divider(height=1,color=theme.LINE),
            ft.Text(tr('资料保留在本机，登录后可手动同步。'),size=11,color=theme.TEXT_SUB)]))
    dialog = ft.AlertDialog(scrollable=True, bgcolor=theme.BG,
        title=ft.Row([ft.Text(tr('账号与同步'),size=15,color=theme.TEXT_SUB),
                      ft.Container(expand=True),ft.IconButton(ft.Icons.CLOSE,
                          tooltip='关闭账号窗口',on_click=lambda e: page.pop_dialog())]),
        content=ft.Container(width=780,content=ft.ResponsiveRow([intro,panel],spacing=16,run_spacing=12)))
    def open_account(e):
        paint_form()
        page.show_dialog(dialog)
        async def discover():
            try:
                await asyncio.to_thread(cloud.refresh_providers)
                if cloud.uid:
                    from cloud_profile import ProfileRepository
                    await asyncio.to_thread(ProfileRepository(cloud).load)
                refresh()
            except CloudError:
                pass  # Email login remains available offline / during provider discovery failure.
        page.run_task(discover)
    entry_button.on_click = open_account
    password.on_submit = lambda e: (register if mode == 'register' else login).on_click(e)
    token.on_submit = verify.on_click
    new_password.on_submit = update.on_click
    paint_form()
    return theme.glass_card(ft.Row(spacing=16,controls=[
        avatar_badge,
        ft.Column(expand=True,spacing=5,controls=[
            ft.Text(tr('账号与同步'),size=17,weight=ft.FontWeight.W_600,color=theme.TEXT_MAIN),identity]),
        entry_button]), padding=22, spacing=12)

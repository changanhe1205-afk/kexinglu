"""Desktop profile editor using the same fields and private media as mobile."""
import asyncio
import flet as ft
import theme
from cloud_profile import ProfileRepository, import_avatar
from cloud_client import CloudError


def open_editor(page, cloud, on_saved):
    repo = ProfileRepository(cloud)
    data = repo.local()
    fields = {key: ft.TextField(label=label, value=data.get(key, ''), border_radius=12,
              max_length=limit) for key, label, limit in [
                  ('nickname', '昵称', 30), ('signature', '个性签名', 160),
                  ('birthday', '出生日期 · YYYY-MM-DD', 10)]}
    gender = ft.Dropdown(label='性别', value=data.get('gender', '不公开'),
        options=[ft.dropdown.Option(v) for v in ['不公开', '男', '女', '其他']])
    avatar = ft.Container(width=80, height=80, border_radius=40,
                          clip_behavior=ft.ClipBehavior.ANTI_ALIAS, bgcolor=theme.CARD_BG_SOFT)
    note = ft.Text('', size=12, color=theme.TEXT_SUB)
    progress = ft.ProgressBar(visible=False)
    busy = False
    picker = ft.FilePicker()
    page.services.append(picker)

    def paint():
        path = data.get('avatar', '')
        avatar.content = ft.Image(src=path, fit=ft.BoxFit.COVER) if path else ft.Icon(ft.Icons.PERSON_OUTLINE, size=40)

    async def pick(e):
        if busy: return
        files = await picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM,
                                       allowed_extensions=['png', 'jpg', 'jpeg', 'webp'])
        if files and files[0].path:
            try:
                data['avatar'] = await asyncio.to_thread(import_avatar, files[0].path)
            except CloudError as exc:
                note.value = str(exc)
            paint(); page.update()

    async def save(e):
        nonlocal busy
        if busy: return
        busy = True; progress.visible = True; save_button.disabled = True
        note.value = '正在保存个人资料…'; page.update()
        value = {**data, **{k: f.value or '' for k, f in fields.items()}, 'gender': gender.value}
        try:
            await asyncio.to_thread(repo.save, value)
            note.value = '已保存，两端使用同一份个人资料。'
            on_saved()
        except CloudError as exc:
            note.value = str(exc) + '；尚未上传的修改会保留，可再次保存。'
        finally:
            busy = False; progress.visible = False; save_button.disabled = False; page.update()

    save_button = ft.FilledButton('保存个人资料', on_click=save)
    paint()
    dialog = ft.AlertDialog(title=ft.Text('个人资料'), scrollable=True,
        content=ft.Container(width=460, content=ft.Column(spacing=16, controls=[
            ft.Row([avatar, ft.TextButton('更换头像', on_click=pick)]),
            *fields.values(), gender, progress, note])),
        actions=[ft.TextButton('返回', on_click=lambda e: None if busy else page.pop_dialog()), save_button])
    page.show_dialog(dialog)

    async def load():
        nonlocal busy
        busy = True; save_button.disabled = True; progress.visible = True; page.update()
        for control in [*fields.values(), gender]: control.disabled = True
        try:
            fresh = await asyncio.to_thread(repo.load)
            data.clear(); data.update(fresh)
            for key, control in fields.items(): control.value = data.get(key, '')
            gender.value = data.get('gender', '不公开'); paint()
        except CloudError as exc:
            note.value = str(exc)
        finally:
            busy = False; save_button.disabled = False; progress.visible = False
            for control in [*fields.values(), gender]: control.disabled = False
            page.update()
    page.run_task(load)

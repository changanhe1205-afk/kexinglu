"""Personal profile shared with Android via Auth metadata, scoped by account."""
from datetime import date
from pathlib import Path
import config
import cloud_media
from cloud_client import CloudError


def import_avatar(path):
    import hashlib
    import io
    from PIL import Image, ImageOps
    try:
        with Image.open(path) as source:
            image = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (512, 512))
            output = io.BytesIO(); image.save(output, format='JPEG', quality=90)
        raw = output.getvalue()
        target = Path(config.data_dir()) / 'profile-media' / (hashlib.sha256(raw).hexdigest() + '.jpg')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return str(target)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise CloudError('无法读取这张图片，请选择 PNG、JPEG 或 WebP 图片') from None


class ProfileRepository:
    def __init__(self, client):
        self.client = client
        self.uid = client.uid
        self.key = 'personal_profile:' + (self.uid or 'guest')

    def local(self):
        return dict(config.get(self.key, {}))

    def check(self):
        if not self.uid or self.client.uid != self.uid:
            raise CloudError('账号已变化，请重新打开个人资料')

    def load(self):
        self.check()
        cached = self.local()
        if cached.get('pending'):
            return cached
        user = self.client.request('/auth/v1/user', authenticated=True)
        raw = user.get('user_metadata', {}).get('kexinglu_profile')
        if not isinstance(raw, dict):
            return cached
        value = dict(raw)
        for field in ('avatar', 'cover'):
            if isinstance(value.get(field), dict):
                pointer = value[field]
                try:
                    value[field] = cloud_media.download(self.client, {'image': pointer},
                        Path(config.data_dir()) / 'profile-media' / self.uid)['image']
                except CloudError:
                    value[field] = cached.get(field, '')
                    value[field + '_remote'] = pointer
        self.check()
        config.set(self.key, value)
        return value

    def save(self, value):
        self.check()
        value = dict(value)
        value['nickname'] = str(value.get('nickname', '')).strip()[:30]
        value['signature'] = str(value.get('signature', '')).strip()[:160]
        birthday = value.get('birthday', '')
        if birthday:
            try:
                if date.fromisoformat(birthday) > date.today():
                    raise ValueError()
            except ValueError:
                raise CloudError('请填写有效出生日期，例如 2000-10-21') from None
        config.set(self.key, {**value, 'pending': True})
        remote = {k: v for k, v in value.items() if k != 'pending'}
        for field in ('avatar', 'cover'):
            media = remote.get(field)
            pointer = remote.pop(field + '_remote', None)
            if not media and pointer:
                remote[field] = pointer
            elif isinstance(media, str) and media and not media.startswith('preset:'):
                remote[field] = cloud_media.upload(self.client, {'image': media})['image']
        self.check()
        self.client.request('/auth/v1/user', {'data': {'kexinglu_profile': remote}},
                            method='PUT', authenticated=True)
        self.check()
        config.set(self.key, {**value, 'pending': False})
        return value

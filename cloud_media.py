"""Private media transport; never interpret a server string as a local filename."""
import base64
import hashlib
import io
import re
from pathlib import Path
from cloud_client import CloudError

ASSET = re.compile(r'^[0-9a-f]{64}\.(?:png|jpg|jpeg|webp|heic|bin)$')
LIMIT=10*1024*1024
SOURCE_LIMIT=100*1024*1024

def prepare_image(raw, ext):
    """Optimize only oversized upload copies; never write to the source file."""
    if len(raw)<=2*1024*1024:return raw,ext
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(raw)) as source:
            picture=ImageOps.exif_transpose(source)
            picture.thumbnail((2560,2560))
            alpha=picture.mode in ('RGBA','LA') or 'transparency' in picture.info
            picture=picture.convert('RGBA' if alpha else 'RGB')
            for _ in range(5):
                output=io.BytesIO()
                if alpha:picture.save(output,format='PNG',optimize=True)
                else:picture.save(output,format='JPEG',quality=85,optimize=True)
                result=output.getvalue()
                if len(result)<=2*1024*1024 or (picture.width<=1024 and len(result)<=LIMIT):return result,'png' if alpha else 'jpg'
                picture.thumbnail((max(1,int(picture.width*.7)),max(1,int(picture.height*.7))))
    except (OSError,ValueError,Image.DecompressionBombError,UnidentifiedImageError) as exc:
        raise CloudError('大图无法转换，请将该图片另存为 JPEG 或 PNG 后重试') from exc
    raise CloudError('图片压缩后仍超过上传限制')


def walk(value, transform, media=False):
    if isinstance(value,dict):
        if '$asset' in value or '$inline' in value: return transform(value)
        return {k:walk(v,transform,k in ('image','poster') or (k=='text' and value.get('kind')=='image')) for k,v in value.items()}
    if isinstance(value,list): return [walk(v,transform) for v in value]
    return transform(value) if media and value else value

def json_key(value):
    return tuple(sorted(value.items())) if isinstance(value,dict) else value

def upload(client,data,prepared=None,seen=None):
    seen=set() if seen is None else seen
    prepared={} if prepared is None else prepared
    def one(value):
        cache_key=json_key(value)
        if cache_key in prepared:return prepared[cache_key]
        if isinstance(value,dict):
            if '$asset' in value and ASSET.fullmatch(str(value['$asset'])): return value
            raw=base64.b64decode(value['$inline'],validate=True);ext='png' if raw.startswith(b'\x89PNG') else 'jpg'
        else:
            # Desktop notebook images are embedded; regular records store paths.
            if len(value)>1024 or re.fullmatch(r'[A-Za-z0-9+/=]{80,}',value):
                raw=base64.b64decode(value,validate=True);ext='png' if raw.startswith(b'\x89PNG') else 'jpg'
            else:
                path=Path(value)
                if not path.is_file(): raise CloudError('有图片无法读取，请恢复原图片后重试')
                if path.stat().st_size>SOURCE_LIMIT: raise CloudError('单张原图超过 100 MiB，请先缩小该图片')
                raw=path.read_bytes();ext=path.suffix.lstrip('.').lower()
                if ext not in ('png','jpg','jpeg','webp','heic'):ext='bin'
        if len(raw)>SOURCE_LIMIT: raise CloudError('单张原图超过 100 MiB，请先缩小该图片')
        raw,ext=prepare_image(raw,ext)
        name=hashlib.sha256(raw).hexdigest()+'.'+ext
        if name not in seen:
            client.request('/storage/v1/object/journal-media/'+client.uid+'/'+name,raw=raw,method='POST',authenticated=True)
            seen.add(name)
        prepared[cache_key]={'$asset':name}
        return prepared[cache_key]
    return walk(data,one)

def download(client,data,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    def one(value):
        if not isinstance(value,dict) or not ASSET.fullmatch(str(value.get('$asset',''))):
            raise CloudError('云端图片引用格式无效，未写入本地记录')
        name=value['$asset'];path=directory/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==name.split('.')[0]:return str(path)
        raw=client.request('/storage/v1/object/authenticated/journal-media/'+client.uid+'/'+name,authenticated=True,binary=True)
        if len(raw)>LIMIT or hashlib.sha256(raw).hexdigest()!=name.split('.')[0]:raise CloudError('图片校验未通过')
        temporary=path.with_suffix('.part');temporary.write_bytes(raw);temporary.replace(path)
        return str(path)
    return walk(data,one)

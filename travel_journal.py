"""User-created travel notebooks. Snapshots never modify source travel records."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime
from html import escape
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageOps
import database

STYLES = {
    'paper': ('纸上旅途', '#F5F0E6', '#322E28', '#8B6345'),
    'forest': ('山野来信', '#E8EEE7', '#243C32', '#52765A'),
    'night': ('夜行拾光', '#222B35', '#F1E9DB', '#D6B98C'),
    'kraft': ('复古牛皮', '#EBDDCA', '#463827', '#8A5B36'),
    'linen': ('亚麻线装', '#F2F0E8', '#3F4743', '#777D64'),
    'rose': ('蔷薇压花', '#FCF1EC', '#62484C', '#A66976'),
    'ocean': ('海岸活页', '#EEF4F3', '#284B58', '#407E93'),
    'mono': ('黑白影集', '#F6F5F2', '#282828', '#606060'),
}

# Shared by native paper rendering and the portable HTML reader.
BINDINGS = {
    'paper': dict(cover='#8C5139', gold='#F1D5A2', texture='leather', binding='bound', detail='暖棕皮面 · 烫金书名'),
    'forest': dict(cover='#314D3D', gold='#DDDFC2', texture='cloth', binding='sewn', detail='松绿布面 · 线装书脊'),
    'night': dict(cover='#192739', gold='#DDBF83', texture='leather', binding='bound', detail='午夜蓝皮面 · 黄铜书签'),
    'kraft': dict(cover='#A67D50', gold='#302A22', texture='grain', binding='sewn', detail='牛皮纸封套 · 旅行邮戳'),
    'linen': dict(cover='#BAB49E', gold='#39433B', texture='cloth', binding='sewn', detail='原色亚麻 · 手工缝线'),
    'rose': dict(cover='#966775', gold='#F9E5D0', texture='floral', binding='bound', detail='玫瑰色封面 · 压花边框'),
    'ocean': dict(cover='#447689', gold='#EDF1DC', texture='cloth', binding='rings', detail='海蓝布面 · 金属活页环'),
    'mono': dict(cover='#30302F', gold='#E8E5DB', texture='grain', binding='album', detail='炭黑硬壳 · 白边相纸'),
}


def init_db():
    with database.get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS travel_notebooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            document TEXT NOT NULL, updated_at TEXT NOT NULL)''')


def list_books():
    init_db()
    with database.get_conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT id,title,updated_at,json_extract(document,'$.style') AS style FROM travel_notebooks ORDER BY updated_at DESC,id DESC")]


def get_book(book_id):
    init_db()
    with database.get_conn() as conn:
        row = conn.execute('SELECT document FROM travel_notebooks WHERE id=?', (book_id,)).fetchone()
    if not row:
        return None
    return dict(json.loads(row['document']), id=book_id)


def save_book(book):
    document = deepcopy(book)
    book_id = document.pop('id', None)
    document['title'] = str(document.get('title', '')).strip()
    if not document['title']:
        raise ValueError('请为手账起一个名字')
    if not document.get('pages'):
        raise ValueError('请至少保留一页手账')
    if document.get('style') not in STYLES:
        raise ValueError('请选择手账风格')
    init_db()
    values = (document['title'], json.dumps(document, ensure_ascii=False),
              datetime.now().isoformat(timespec='microseconds'))
    with database.get_conn() as conn:
        if book_id is None:
            book_id = conn.execute('INSERT INTO travel_notebooks(title,document,updated_at) VALUES(?,?,?)', values).lastrowid
        else:
            cursor = conn.execute('UPDATE travel_notebooks SET title=?,document=?,updated_at=? WHERE id=?', (*values, book_id))
            if cursor.rowcount != 1:
                raise ValueError('这本手账已被删除，请重新创建')
    book['id'] = book_id
    return book_id


def delete_book(book_id):
    init_db()
    with database.get_conn() as conn:
        conn.execute('DELETE FROM travel_notebooks WHERE id=?', (book_id,))


def snapshot_photo(path):
    """Portable, orientation-correct copy; no dependency on the original photo."""
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((1400, 1400))
            if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                rgba = image.convert('RGBA')
                image = Image.new('RGB', rgba.size, '#F5F0E6')
                image.paste(rgba, mask=rgba.getchannel('A'))
            else:
                image = image.convert('RGB')
            output = BytesIO()
            image.save(output, 'JPEG', quality=83, optimize=True)
            return base64.b64encode(output.getvalue()).decode('ascii')
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def new_book(logs, title, style='paper', subtitle='把路上的片刻，留在这一册。'):
    if not logs:
        raise ValueError('请至少选择一条旅行记录')
    pages, missing = [], 0
    for log in sorted(logs, key=lambda row: (row.get('visit_date') or '9999', row['id'])):
        photos = []
        originals = log.get('photos') or ([{'image': log['image']}] if log.get('image') else [])
        for photo in originals:
            encoded = snapshot_photo(photo.get('image') or '')
            if encoded:
                photos.append({'image': encoded, 'caption': photo.get('caption') or '', 'included': True})
            else:
                missing += 1
        pages.append({'title': log.get('title') or log.get('city') or '路上的一页',
                      'place': log.get('city') or '', 'date': log.get('visit_date') or '',
                      'note': log.get('note') or '', 'photos': photos,
                      'source_id': log['id']})
    return {'title': title, 'subtitle': subtitle, 'style': style,
            'pages': pages, 'missing_photos': missing, 'schema': 1}


def render_html(book):
    from notebook_export import render
    return render(book)


def export_html(book, destination):
    path = Path(destination)
    if path.suffix.lower() != '.html':
        path = path.with_suffix('.html')
    path.write_text(render_html(book), encoding='utf-8')
    return path

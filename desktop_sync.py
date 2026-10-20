"""SQLite adapter. Network code never holds the local write transaction."""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import cloud_media
from cloud_client import CloudError
from sync_engine import digest, synchronize
from sync_schema import TABLES, to_shared, to_desktop

_lock=threading.Lock()

class ClosingConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

class DesktopReplica:
    def __init__(self,path,uid):
        self.path=str(path);self.uid=uid
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS cloud_binding (id INTEGER PRIMARY KEY CHECK(id=1),uid TEXT NOT NULL)')
            bound=db.execute('SELECT uid FROM cloud_binding WHERE id=1').fetchone()
            if bound and bound[0]!=uid:raise CloudError('这份本地资料已绑定其他账号。为防止混入数据，本次同步已停止。')
            db.execute('INSERT OR IGNORE INTO cloud_binding VALUES(1,?)',(uid,))
            db.execute('CREATE TABLE IF NOT EXISTS cloud_meta(kind TEXT,local_id INTEGER,rid TEXT UNIQUE,revision INTEGER,hash TEXT,PRIMARY KEY(kind,local_id))')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15,factory=ClosingConnection);db.row_factory=sqlite3.Row;return db
    def snapshots(self,connection=None):
        db=connection or self.connect()
        try:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            result={}
            for kind,table in TABLES.items():
                if table not in tables:continue
                for record in db.execute(f'SELECT * FROM {table}'):
                    row=dict(record)
                    if kind=='book':row=json.loads(row['document'])
                    if kind=='travel' and 'travel_photos' in tables:
                        row['photos']=[dict(p) for p in db.execute('SELECT * FROM travel_photos WHERE log_id=? ORDER BY sort,id',(record['id'],))]
                    result[(kind,record['id'])]=to_shared(kind,row)
            return result
        finally:
            if connection is None:db.close()
    def metadata(self):
        with self.connect() as db:return {(r['kind'],r['local_id']):dict(r) for r in db.execute('SELECT * FROM cloud_meta')}
    def register(self,key,rid):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO cloud_meta VALUES(?,?,?,0,?)',(*key,rid,digest(None)))
        return self.metadata()[key]
    def ack(self,key,revision,signature):
        with self.connect() as db:db.execute('UPDATE cloud_meta SET revision=?,hash=? WHERE kind=? AND local_id=?',(revision,signature,*key))
    def apply(self,key,record,data,expected):
        kind=record['kind']
        if kind not in TABLES:raise CloudError('云端记录类型不支持')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if key and digest(self.snapshots(db).get(key))!=expected:return False
            table=TABLES[kind]
            if data is None:
                if key:
                    db.execute(f'DELETE FROM {table} WHERE id=?',(key[1],))
                    if kind=='travel':db.execute('DELETE FROM travel_photos WHERE log_id=?',(key[1],))
                else:
                    # Negative local keys represent remote tombstones never seen locally.
                    lowest=db.execute('SELECT min(local_id) FROM cloud_meta WHERE kind=?',(kind,)).fetchone()[0] or 0
                    key=(kind,min(0,lowest)-1)
            else:
                row=to_desktop(kind,data)
                photos=row.pop('photos',[])
                if kind=='book':
                    row={'title':row.get('title','旅行手账'),'document':json.dumps(row,ensure_ascii=False),'updated_at':datetime.now().isoformat()}
                cols={r[1] for r in db.execute(f'PRAGMA table_info({table})')}
                row={k:v for k,v in row.items() if k in cols and k!='id'}
                row.setdefault('created_at',datetime.now().isoformat()) if 'created_at' in cols else None
                if not key or key[1]<0:
                    cursor=db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",list(row.values()))
                    if key:db.execute('DELETE FROM cloud_meta WHERE kind=? AND local_id=?',key)
                    key=(kind,cursor.lastrowid)
                else:db.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in row)} WHERE id=?",[*row.values(),key[1]])
                if kind=='travel':
                    db.execute('DELETE FROM travel_photos WHERE log_id=?',(key[1],))
                    for index,photo in enumerate(photos):
                        if photo.get('image'):db.execute('INSERT INTO travel_photos(log_id,image,caption,sort,created_at) VALUES(?,?,?,?,?)',(key[1],photo['image'],photo.get('caption',''),index,datetime.now().isoformat()))
            signature=digest(self.snapshots(db).get(key))
            db.execute('INSERT OR REPLACE INTO cloud_meta VALUES(?,?,?,?,?)',(*key,record['id'],record['revision'],signature))
        return True

class Remote:
    def __init__(self,client,media_dir):
        self.client=client;self.media_dir=media_dir
        self.prepared={};self.uploaded_media=set()
    def put(self,rid,kind,data,revision):
        payload={} if data is None else cloud_media.upload(self.client,data,self.prepared,self.uploaded_media)
        return self.client.request('/rest/v1/rpc/put_journal_record',{'record_id':rid,'record_kind':kind,'payload':payload,'expected_revision':revision,'is_deleted':data is None},authenticated=True)
    def list(self):
        cursor=''
        while True:
            rows=self.client.request('/rest/v1/journal_records?select=*&order=id&limit=20'+('&id=gt.'+cursor if cursor else ''),authenticated=True)
            yield from rows
            if len(rows)<20:return
            cursor=rows[-1]['id']
    def materialize(self,data):return cloud_media.download(self.client,data,self.media_dir)

def sync_now(client,confirmed=False,progress=None):
    if not confirmed:raise CloudError('请先确认将本地资料绑定并上传到当前账号')
    original_session=client.session
    session=client.session_copy()
    if not session.uid:raise CloudError('请先登录')
    if not _lock.acquire(blocking=False):raise CloudError('同步正在进行，请稍候')
    try:
        import database,travel_journal,travel_db,ticket_db,food_db
        database.init_db();travel_journal.init_db()
        directory=Path(database.BASE_DIR)
        # SQLite backup is consistent even when WAL is present. Only synthetic data
        # is used by tests; this function runs on real data solely via user action.
        backup=directory/'before-first-cloud-sync.db'
        if not backup.exists():
            with sqlite3.connect(database.DB_PATH,factory=ClosingConnection) as source,sqlite3.connect(backup,factory=ClosingConnection) as target:source.backup(target)
        # Capture one account for the entire run, even if the settings page is
        # rebuilt and a different login completes while this worker is active.
        return synchronize(DesktopReplica(database.DB_PATH,session.uid),Remote(session,directory/'cloud-media'),progress)
    finally:
        if client.session is original_session:client.session=session.session
        _lock.release()

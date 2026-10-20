import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cloud_client import CloudClient, CloudError
from cloud_media import download
from desktop_sync import DesktopReplica, ClosingConnection
from sync_engine import synchronize, digest
from sync_schema import to_shared, to_desktop

class Server:
    def __init__(self):self.rows={};self.fail_after_write=False
    def put(self,rid,kind,data,revision):
        old=self.rows.get(rid)
        if old and old['data']==(data or {}) and old['deleted']==(data is None):return {'accepted':True,'record':copy.deepcopy(old)}
        if old and old['revision']!=revision:return {'accepted':False,'record':copy.deepcopy(old)}
        row={'id':rid,'kind':kind,'data':copy.deepcopy(data or {}),'deleted':data is None,'revision':(old['revision'] if old else 0)+1}
        self.rows[rid]=row
        if self.fail_after_write:self.fail_after_write=False;raise OSError('lost response')
        return {'accepted':True,'record':copy.deepcopy(row)}
    def list(self):return copy.deepcopy(list(self.rows.values()))
    def materialize(self,data):return copy.deepcopy(data)

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.a=self.replica('a');self.b=self.replica('b');self.remote=Server()
    def replica(self,name):
        path=Path(self.tmp.name)/(name+'.db')
        with sqlite3.connect(path, factory=ClosingConnection) as db:
            db.execute('CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT,kind TEXT,genre TEXT,watch_date TEXT,rating INTEGER,review TEXT,poster TEXT,created_at TEXT)')
        return DesktopReplica(path,'same-account')
    def add(self,rep,title):
        with rep.connect() as db:db.execute("INSERT INTO movies(title,kind,genre,watch_date,rating,review,poster) VALUES(?,'电影','剧情','2026-10-05',4,'note','')",(title,))
    def edit(self,rep,title):
        with rep.connect() as db:db.execute('UPDATE movies SET title=?',(title,))
    def test_roundtrip_update_delete(self):
        self.add(self.a,'first');synchronize(self.a,self.remote);synchronize(self.b,self.remote)
        self.assertEqual(next(iter(self.b.snapshots().values()))['title'],'first')
        self.edit(self.b,'second');synchronize(self.b,self.remote);synchronize(self.a,self.remote)
        self.assertEqual(next(iter(self.a.snapshots().values()))['title'],'second')
        with self.a.connect() as db:db.execute('DELETE FROM movies')
        synchronize(self.a,self.remote);synchronize(self.b,self.remote)
        self.assertFalse(self.b.snapshots());self.assertTrue(next(iter(self.remote.rows.values()))['deleted'])
        self.assertEqual(synchronize(self.b,self.remote)['uploaded'],0)
    def test_conflict_keeps_both_versions(self):
        self.add(self.a,'first');synchronize(self.a,self.remote);synchronize(self.b,self.remote)
        self.edit(self.a,'computer');self.edit(self.b,'phone');synchronize(self.a,self.remote)
        result=synchronize(self.b,self.remote)
        self.assertTrue(result['conflicts']);self.assertEqual(next(iter(self.b.snapshots().values()))['title'],'phone')
        self.assertEqual(next(iter(self.remote.rows.values()))['data']['title'],'computer')
    def test_lost_response_retry_does_not_duplicate(self):
        self.add(self.a,'one');self.remote.fail_after_write=True
        self.assertTrue(synchronize(self.a,self.remote)["failures"])
        synchronize(self.a,self.remote)
        self.assertEqual(len(self.remote.rows),1);self.assertEqual(next(iter(self.remote.rows.values()))['revision'],1)
    def test_edit_racing_download_is_not_overwritten(self):
        self.add(self.a,'one');synchronize(self.a,self.remote);synchronize(self.b,self.remote)
        key=next(iter(self.b.snapshots()));expected=digest(self.b.snapshots()[key]);self.edit(self.b,'new local')
        record=next(iter(self.remote.rows.values()))
        self.assertFalse(self.b.apply(key,record,record['data'],expected))
    def test_account_switch_rejected(self):
        with self.assertRaises(CloudError):DesktopReplica(self.a.path,'different-account')
    def test_desktop_fields_survive_phone_changes(self):
        row={'vehicle':'火车','from_city':'枣庄','to_city':'贵阳北','depart_date':'2026-10-05','depart_time':'10:30','passenger_id':'masked','style':'classic','price':'CNY 100'}
        shared=to_shared('ticket',row);shared['price']='120';back=to_desktop('ticket',shared)
        self.assertEqual(back['depart_time'],'10:30');self.assertEqual(back['vehicle'],'火车');self.assertEqual(back['price'],'120')
    def test_book_geometry_and_extra_fields(self):
        doc={'title':'书','style':'forest','pages':[{'design':{'paper':'grid','elements':[{'kind':'text','text':'文字','x':84,'y':116,'w':210,'size':28,'rotation':15,'font':'KaiTi','bold':True}]}}]}
        shared=to_shared('book',doc);back=to_desktop('book',shared)
        e=back['pages'][0]['design']['elements'][0]
        self.assertAlmostEqual(e['x'],84);self.assertAlmostEqual(e['rotation'],15);self.assertEqual(e['font'],'KaiTi');self.assertTrue(e['bold']);self.assertEqual(back['style'],'forest')
    def test_untouched_desktop_layout_outside_mobile_limits_survives(self):
        doc={'title':'书','style':'paper','pages':[{'design':{'paper':'plain','elements':[{'kind':'text','text':'大标题','x':-10,'y':0,'w':500,'size':150,'rotation':0}]}}]}
        back=to_desktop('book',to_shared('book',doc))
        e=back['pages'][0]['design']['elements'][0]
        self.assertEqual((e['x'],e['w'],e['size']),(-10,500,150))
    def test_cloud_cannot_inject_local_image_path(self):
        with self.assertRaises(CloudError):download(None,{'image':'C:/secret.txt'},Path(self.tmp.name)/'media')
        with self.assertRaises(CloudError):download(None,{'image':{'$asset':'../../secret'}},Path(self.tmp.name)/'media')
    def test_failed_record_does_not_block_other_uploads(self):
        self.add(self.a,'blocked');self.add(self.a,'healthy')
        original=self.remote.put
        def put(rid,kind,data,revision):
            if data.get('title')=='blocked':raise CloudError('图片不可读取')
            return original(rid,kind,data,revision)
        self.remote.put=put
        result=synchronize(self.a,self.remote)
        self.assertEqual(result['uploaded'],1)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(result['cloud_records'],1)
        self.remote.put=original
        result=synchronize(self.a,self.remote)
        self.assertEqual(result['uploaded'],1)
        self.assertEqual(len(self.remote.rows),2)

    def test_bad_download_does_not_block_other_records(self):
        self.add(self.a,'blocked');self.add(self.a,'healthy');synchronize(self.a,self.remote)
        def materialize(data):
            if data['title']=='blocked':raise CloudError('图片校验失败')
            return data
        self.remote.materialize=materialize
        result=synchronize(self.b,self.remote)
        self.assertEqual(result['downloaded'],1)
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(next(iter(self.b.snapshots().values()))['title'],'healthy')

    def test_large_photo_upload_optimizes_copy_and_preserves_original(self):
        import os,io,hashlib
        from PIL import Image
        from cloud_media import upload,LIMIT
        path=Path(self.tmp.name)/'large.png'
        Image.frombytes('RGB',(2048,2048),os.urandom(2048*2048*3)).save(path)
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertGreater(path.stat().st_size,LIMIT)
        class Client:
            uid='owner'
            calls=[]
            def request(self,*args,**kwargs):self.calls.append(kwargs['raw'])
        client=Client()
        result=upload(client,{'image':str(path),'_desktop':{'image':str(path)}})
        self.assertEqual(len(client.calls),1)
        self.assertLess(len(client.calls[0]),LIMIT)
        Image.open(io.BytesIO(client.calls[0])).verify()
        self.assertEqual(result['image'],result['_desktop']['image'])
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_storage_duplicate_400_is_idempotent_but_other_400_is_error(self):
        import io,time
        import urllib.error
        from unittest.mock import patch
        client=CloudClient({'url':'https://test.supabase.co','publishableKey':'sb_publishable_test'})
        client.session={'user':{'id':'owner'},'access_token':'test','expires_at':time.time()+3600}
        for detail,accepted in [({'error':'Duplicate'},True),({'code':'ResourceAlreadyExists'},True),({'error':'InvalidRequest'},False)]:
            failure=urllib.error.HTTPError('https://test',400,'bad',{},io.BytesIO(json.dumps(detail).encode()))
            with patch('urllib.request.urlopen',side_effect=failure):
                if accepted:self.assertEqual(client.request('/storage/v1/object/journal-media/owner/test',raw=b'data',authenticated=True),{})
                else:
                    with self.assertRaises(CloudError):client.request('/storage/v1/object/journal-media/owner/test',raw=b'data',authenticated=True)

    def test_progress_reports_real_record_counts(self):
        self.add(self.a,'one');self.add(self.a,'two');events=[]
        result=synchronize(self.a,self.remote,lambda *event:events.append(event))
        self.assertEqual(result['uploaded'],2)
        self.assertIn(('上传记录',0,2),events)
        self.assertIn(('上传记录',2,2),events)
        self.assertEqual(events[-1],('同步检查完成',2,2))
        self.assertTrue(all(0<=done<=total for _,done,total in events))

    def test_rejects_secret_key_and_insecure_endpoint(self):
        with self.assertRaises(CloudError):CloudClient({'url':'https://test.supabase.co','publishableKey':'sb_secret_nope'})
        with self.assertRaises(CloudError):CloudClient({'url':'http://test.supabase.co','publishableKey':'sb_publishable_test'})

if __name__=='__main__':unittest.main()

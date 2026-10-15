from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import database
import travel_journal as journal


class TravelNotebookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        for attr,value in [('BASE_DIR',str(self.root)),('POSTER_DIR',str(self.root/'posters')),
                           ('DB_PATH',str(self.root/'test.db'))]:
            patcher=patch.object(database,attr,value);patcher.start();self.addCleanup(patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def log(self, key=1, date='2026-10-05', **extra):
        return dict(id=key,title='西湖',city='杭州',visit_date=date,note='湖边的一天',photos=[],**extra)

    def test_opt_in_and_independent_editing_roundtrip(self):
        self.assertEqual(journal.list_books(),[])
        log=self.log();original=deepcopy(log)
        book=journal.new_book([log],'杭州手记')
        self.assertEqual(journal.list_books(),[])  # Composition is not an implicit save.
        book['pages'][0]['note']='在手账中另写的一段话'
        key=journal.save_book(book)
        self.assertEqual(journal.get_book(key)['pages'][0]['note'],'在手账中另写的一段话')
        self.assertEqual(log,original)
        book['title']='改名后的旅行';journal.save_book(book)
        self.assertEqual(len(journal.list_books()),1)
        self.assertEqual(journal.list_books()[0]['title'],book['title'])
        journal.delete_book(key)
        self.assertIsNone(journal.get_book(key))
        self.assertEqual(log,original)

    def test_chronology_single_record_missing_photo_and_no_photo(self):
        older=self.log(2,'2026-09-01');newer=self.log(1,'2026-10-05')
        newer['photos']=[{'image':str(self.root/'missing.jpg')}]
        book=journal.new_book([newer,older],'全部地点')
        self.assertEqual([p['source_id'] for p in book['pages']],[2,1])
        self.assertEqual(book['missing_photos'],1)
        self.assertEqual(len(journal.new_book([older],'一次旅行')['pages']),1)
        with self.assertRaises(ValueError):journal.new_book([],'空手账')
        book['title']=' '
        with self.assertRaises(ValueError):journal.save_book(book)

    def test_embedded_photos_survive_original_deletion_and_export_escapes_html(self):
        image=self.root/'旅行照片.png';Image.new('RGB',(1800,900),'green').save(image)
        log=self.log();log['photos']=[{'image':str(image),'caption':'<script>alert(1)</script>'}]
        book=journal.new_book([log],'<script>标题</script>')
        journal.save_book(book);image.unlink()
        loaded=journal.get_book(book['id'])
        html=journal.render_html(loaded)
        self.assertIn('data:image/jpeg;base64,',html)
        self.assertNotIn('<script>标题</script>',html)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertEqual(html.count('<script>'),1)  # Only the trusted page-turn controller.
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn(str(self.root),html)
        result=journal.export_html(loaded,self.root/'分享.html')
        self.assertEqual(result.read_text(encoding='utf-8'),html)
        loaded['pages'][0]['photos'][0]['included']=False
        self.assertNotIn('data:image/jpeg;base64,',journal.render_html(loaded))

    def test_reordered_custom_pages_and_dynamic_data_directory(self):
        book=journal.new_book([self.log(),self.log(2,'2026-10-06')],'两页')
        book['pages'].reverse();book['pages'].append(dict(title='写在最后',place='',date='',note='后记',photos=[]))
        journal.save_book(book)
        self.assertEqual(journal.get_book(book['id'])['pages'][-1]['title'],'写在最后')
        with patch.object(database,'DB_PATH',str(self.root/'other.db')):
            self.assertEqual(journal.list_books(),[])
        self.assertEqual(len(journal.list_books()),1)

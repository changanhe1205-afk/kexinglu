from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from io import BytesIO
import base64
from PIL import Image
from notebook_collage import make_design, html_canvas, LAYOUTS, PAPERS, element, snapshot_sticker, preview_image


class CollageTests(unittest.TestCase):
    def test_layouts_do_not_mutate_source_and_geometry_stays_on_paper(self):
        source={'title':'西湖','note':'我自己的记录','photos':[{'image':'sample','included':True}]}
        original=deepcopy(source)
        for layout in LAYOUTS:
            for paper in PAPERS:
                design=make_design(source,layout,paper)
                for obj in design['elements']:
                    self.assertLessEqual(obj['x']+obj['w'],420)
                    self.assertLessEqual(obj['y']+obj['h'],580)
                design['elements'].append(element(text='新内容'))
        self.assertEqual(source,original)

    def test_export_escapes_text_and_keeps_placement(self):
        design=make_design({},'blank')
        design['elements'].append(element(text='<script>alert(1)</script>',x=42,y=58,rotation=12))
        result=html_canvas(design)
        self.assertNotIn('<script>',result)
        self.assertIn('&lt;script&gt;',result)
        self.assertIn('left:10.0%',result)
        self.assertIn('rotate(12.0deg)',result)

    def test_empty_layout_is_actually_empty(self):
        self.assertEqual(make_design({'note':'original'},'blank')['elements'],[])

    def test_transparent_material_survives_original_deletion_and_cached_redraw(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sticker.png'
            img=Image.new('RGBA',(20,30),(40,90,130,0));img.putpixel((10,15),(40,90,130,255));img.save(path)
            material=snapshot_sticker(path);path.unlink()
            decoded=Image.open(BytesIO(base64.b64decode(material['image'])))
            self.assertEqual(decoded.getpixel((0,0))[3],0)
            self.assertEqual(decoded.getpixel((10,15))[3],255)
            a=preview_image(material['image']);b=preview_image(material['image'])
            self.assertEqual(a,b)
            self.assertTrue(Path(a).exists())
            design=make_design({},'blank');design['elements']=[element('image',image=material['image'],mime=material['mime'])]
            self.assertIn('data:image/png;base64,',html_canvas(design))

    def test_text_effects_and_hidden_layers_export(self):
        design=make_design({},'blank')
        design['elements']=[element(text='可见',font='KaiTi',bold=True,italic=True,underline=True,shadow=True,highlight='#FFDD00'),
                            element(text='隐藏内容',hidden=True)]
        result=html_canvas(design)
        for fragment in ('font-family:KaiTi','font-weight:700','font-style:italic','text-decoration:underline','text-shadow:','background:#FFDD00'):
            self.assertIn(fragment,result)
        self.assertNotIn('隐藏内容',result)

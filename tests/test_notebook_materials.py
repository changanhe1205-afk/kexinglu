import base64
from copy import deepcopy
from io import BytesIO
import unittest
from PIL import Image
from notebook_materials import catalog, EXTRA_NAMES
from notebook_collage import html_canvas


class MaterialTests(unittest.TestCase):
    def test_new_illustrations_are_distinct_transparent_and_exportable(self):
        drawings=set()
        for category,names in EXTRA_NAMES.items():
            for name,obj in catalog(category):
                self.assertIn(name,names)
                with Image.open(BytesIO(base64.b64decode(obj['image']))) as im:
                    self.assertEqual(im.mode,'RGBA')
                    self.assertEqual(im.getpixel((0,0))[3],0)
                    self.assertIsNotNone(im.getbbox())
                    if category=='frame':self.assertEqual(im.getpixel((120,120))[3],0)
                self.assertNotIn(obj['image'],drawings);drawings.add(obj['image'])
                self.assertIn('data:image/png;base64,',html_canvas({'paper':'plain','elements':[obj]}))
        self.assertEqual(len(drawings),32)

    def test_copied_template_edit_does_not_mutate_catalog(self):
        template=catalog('travel')[0][1]
        placed=deepcopy(template);placed['x']=222;placed['name']='自己的票'
        self.assertNotEqual(placed,template)
        self.assertEqual(template['name'],'登机牌')


if __name__=='__main__':unittest.main()

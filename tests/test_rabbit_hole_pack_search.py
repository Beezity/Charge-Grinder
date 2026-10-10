import os
from pathlib import Path
import unittest
from unittest.mock import Mock
from source.rabbit_hole_pack_search import search_pack, PackVision
from source.rabbit_hole import CheckpointRequired

class PackSearchTests(unittest.TestCase):
    def test_existing_target_avoids_purchase(self):
        io=Mock();v=Mock();v.active.return_value=False;v.target.return_value=(320,680)
        self.assertEqual(search_pack(io,1,v),(320,680));io.click.assert_not_called()
    def test_purchase_once_after_scroll(self):
        io=Mock();v=Mock();v.active.return_value=False;v.target.side_effect=[None,None,(960,570),(320,680)]
        self.assertEqual(search_pack(io,2,v),(320,680))
        io.scroll.assert_called_once()
        self.assertEqual([c.args[0] for c in io.click.call_args_list],[(280,70),(410,330),(960,570),(1180,870),(1145,740)])
    def test_missing_pack_never_confirms_or_substitutes(self):
        io=Mock();v=Mock();v.active.return_value=False;v.target.return_value=None
        with self.assertRaises(CheckpointRequired):search_pack(io,4,v)
        self.assertEqual(io.click.call_count,2);self.assertEqual(io.scroll.call_count,12)

@unittest.skipUnless(os.environ.get('RABBIT_PACK_CAPTURE_DIR'),'Original pack screenshots not enabled')
class CaptureTests(unittest.TestCase):
    def test_required_offered_and_search_titles(self):
        import cv2
        v=PackVision();root=Path(os.environ['RABBIT_PACK_CAPTURE_DIR'])
        for floor,n,lib in [(1,'87a4c4ae-c716-4644-bcda-d2032f763cb3',False),(2,'25480267-bc9f-4ec2-bc0e-8be343a4e537',False),(3,'efc0a73f-c3af-4693-a07f-533b1b60e49c',False),(4,'d500302d-78d1-4bf4-98c4-07bd65faccc3',False),(5,'5c4654b1-19e1-4089-a174-45d25b203dd3',False),(4,'d29bea99-18d8-4f0e-860a-456419d9d2f9',True)]:
            with self.subTest(floor=floor,library=lib):
                f=cv2.imread(str(root/('codex-clipboard-'+n+'.png')))
                self.assertIsNotNone(v.target(f,floor,lib))
        inactive=cv2.imread(str(root/"codex-clipboard-efc0a73f-c3af-4693-a07f-533b1b60e49c.png"))
        active=cv2.imread(str(root/"codex-clipboard-4092b9cf-247c-4193-9ea7-268ee6066768.png"))
        self.assertFalse(v.active(inactive));self.assertTrue(v.active(active))
        for floor,n in [(1,'afa82e94-c4d6-42a2-81ce-2cea6e5586f2'),(2,'18715f15-d008-4658-8aae-bdf5321bc2b5'),(5,'95c32a50-ec03-475d-aea0-81b665630bd7')]:
            f=cv2.imread(str(root/('codex-clipboard-'+n+'.png')))
            self.assertTrue(v.library(f,floor));self.assertIsNone(v.target(f,floor,True))

"""Optional replay against the user's original recordings (never distributed)."""
import os
from pathlib import Path
import unittest
import cv2
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_vision import ShopVision

VIDEO_DIR = os.environ.get('RABBIT_SHOP_VIDEO_DIR')


@unittest.skipUnless(VIDEO_DIR, 'Set RABBIT_SHOP_VIDEO_DIR for original video replay')
class ShopVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.v = ShopVision()

    def frame(self, clip, sample=None, seconds=None):
        name = '2026-10-10 09-19-07.mp4' if clip == 'a' else '2026-10-10 09-21-37.mp4'
        cap = cv2.VideoCapture(str(Path(VIDEO_DIR) / name))
        # ffmpeg fps=2 selects frame 14 of the first 30-frame window.
        if seconds is None: seconds = (sample-1)*.5 + 14/60
        cap.set(cv2.CAP_PROP_POS_MSEC, seconds*1000)
        ok, frame = cap.read(); cap.release()
        self.assertTrue(ok, name)
        return frame

    def test_screen_sequence(self):
        for clip, sample, expected in [('a', 11, 'shop'), ('a', 16, 'heal'),
                ('a', 21, 'heal_select'), ('a', 23, 'heal_result'),
                ('a', 41, 'keyword'), ('a', 87, 'fusion_confirm'),
                ('b', 61, 'gift_result'), ('b', 63, 'sell'),
                ('b', 67, 'sale_confirm'), ('a', 95, 'upgrade'),
                ('a', 97, 'upgrade_confirm'), ('a', 109, 'leave_confirm'), ('a', 113, 'map')]:
            with self.subTest(clip=clip, sample=sample):
                self.assertEqual(self.v.state(self.frame(clip, sample)), expected)

    def test_sale_names_and_prices(self):
        self.assertEqual(self.v.sale_details(self.frame('b', 67)), ('Little and To-be-Naughty Plushie', 0, 96))
        self.assertEqual(self.v.sale_details(self.frame('b', 77)), ('Prejudice', 0, 76))

    def test_purchase_preview(self):
        frame = self.frame('b', seconds=7.8666667)
        self.assertEqual(self.v.state(frame), 'buy_confirm')
        self.assertEqual(self.v.purchase_details(frame), ('Dimensional Perception Modifier', 250))

    def test_upgrade_before_after(self):
        self.assertEqual(self.v.upgrade_details(self.frame('a', 97)),
                         (('Clear Mirror, Calm Water', 0), ('Clear Mirror, Calm Water', 2), 300))
        self.assertEqual(self.v.selected(self.frame('a', 101)), ('Clear Mirror, Calm Water', 2))

    def test_forecast_and_reject_wrong_tier_or_keyword(self):
        self.v.verify_forecast(self.frame('a', 59), 'POISE')
        self.v.verify_forecast(self.frame('b', 41), 'SINKING')
        with self.assertRaises(CheckpointRequired): self.v.verify_forecast(self.frame('b', 37), 'SINKING')
        with self.assertRaises(CheckpointRequired): self.v.verify_forecast(self.frame('b', 41), 'POISE')

    def test_fusion_ingredients_and_wrong_item(self):
        frame = self.frame('a', 81)
        icons = [self.v.icon(frame, 1252, 347), self.v.icon(frame, 1540, 347),
                 self.v.icon(self.frame('a', 73), 959, 526)]
        self.v.verify_ingredients(self.frame('a', 87), icons)
        with self.assertRaises(CheckpointRequired):
            self.v.verify_ingredients(self.frame('a', 87), icons[:2]+[self.v.icon(frame, 965, 345)])

    def test_actual_result_is_read(self):
        self.assertEqual(self.v.result_name(self.frame('b', 61)), 'Artistic Sense')

    def test_sp_and_currency(self):
        self.assertEqual(self.v.sp(self.frame('a', 11), 155), -40)
        self.assertEqual(self.v.sp(self.frame('a', 25), 155), 5)
        self.assertEqual(self.v.number(self.frame('b', 13), (857,175,99,57)), 278)

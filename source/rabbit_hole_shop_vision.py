"""Offline-capable shop reader. All coordinates are game-client coordinates.

OCR is lazy and local (models ship in rapidocr-onnxruntime). Low-confidence
transaction fields are errors, never guessed numbers or approximate gift names.
"""
from dataclasses import dataclass
from pathlib import Path
import re
from difflib import SequenceMatcher
import cv2
import numpy as np
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_policy import PROTECTED


def key(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


CANONICAL = {key(n): n for n in PROTECTED | {'Cigarette Holder', 'Grand Welcome'}}
CANONICAL['sharpneedlesandthreads'] = 'Sharp Needles & Threads'


def gift_name(text):
    text = text.strip()
    level = len(text) - len(text.rstrip('+'))
    base = text.rstrip('+').strip()
    if not base or '?' in base or level > 2:
        raise CheckpointRequired('Unreadable gift name or enhancement level.')
    normalized = key(base)
    if normalized not in CANONICAL and any(SequenceMatcher(None, normalized, k).ratio() > .72 for k in CANONICAL):
        raise CheckpointRequired('Ambiguous protected-gift name; refusing to guess.')
    return CANONICAL.get(normalized, base), level


@dataclass(frozen=True)
class Word:
    text: str
    score: float
    x: float
    y: float


class ShopVision:
    def __init__(self, engine=None):
        if engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError as exc:
                raise CheckpointRequired('Install requirements-rabbit-hole.txt with Python 3.11 or 3.12 for shop OCR.') from exc
            engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
        self.engine = engine
        root = Path(__file__).resolve().parents[1] / 'ImageAssets/UI/shop/fuse'
        self.tiers = {i: cv2.imread(str(root / f'{i}.png'), 0) for i in range(1, 5)}

    def read(self, frame, roi=(0, 0, 1920, 1080), scale=1):
        if frame is None or frame.shape[:2] != (1080, 1920):
            raise CheckpointRequired('Shop requires a 1920x1080 game-client capture.')
        x, y, w, h = roi
        crop = frame[y:y+h, x:x+w]
        if scale != 1:
            crop = cv2.resize(crop, None, fx=scale, fy=scale)
        result, _ = self.engine(crop)
        return [Word(t, float(c), x + np.mean(np.array(b)[:, 0])/scale,
                     y + np.mean(np.array(b)[:, 1])/scale) for b, t, c in result or []]

    def text(self, frame, roi, *, confidence=.90, scale=2):
        words = self.read(frame, roi, scale)
        if not words or any(w.score < confidence for w in words):
            raise CheckpointRequired('Shop text could not be read confidently.')
        return ' '.join(w.text for w in words)

    def number(self, frame, roi, *, signed=False):
        x, y, w, h = roi
        values = []
        for pad in (0, 3, 5):
            result, _ = self.engine(frame[y+pad:y+h-pad, x:x+w], use_det=False, use_cls=False)
            if not result or len(result) != 1: continue
            text, score = result[0]
            text = text.replace(' ', '')
            if score >= .95 and re.fullmatch(r'-?\d+' if signed else r'\d+', text):
                values.append(int(text))
        if not values or len(set(values)) != 1:
            raise CheckpointRequired('Unreadable or conflicting shop numeric field.')
        return values[0]

    @staticmethod
    def classify(words):
        lines = [w.text.lower() for w in words if w.score >= .85]
        text = ' '.join(lines)
        compact = key(text)
        if 'connecting' in compact: return 'loading'
        if 'sell[' in text or re.search(r'sell\s*\[', text): return 'sale_confirm'
        if 'leave the shop' in text: return 'leave_confirm'
        if 'keywordselection' in compact: return 'keyword'
        if 'selectedegogifts' in compact and 'prediction' in compact: return 'fusion_confirm'
        if 'egogiftget' in compact: return 'gift_result'
        if 'enhanceegogift' in compact and 'spend' in compact and 'confirm' in compact: return 'upgrade_confirm'
        if 'purchaseegogifts' in compact: return 'buy_confirm'
        if 'sellegogift' in compact: return 'sell'
        if 'enhanceegogift' in compact: return 'upgrade'
        if 'fuseegogift' in compact: return 'fuse'
        if 'healsinners' in compact:
            if 'hpandsphealedfor' in compact: return 'heal_result'
            if 'choosethesinner' in compact: return 'heal_select'
            return 'heal'
        if 'shop' in lines and 'refresh' in compact and 'leave' in compact: return 'shop'
        if any(w.score >= .94 and key(w.text).startswith('exploring') and w.x < 350 and w.y < 210 for w in words): return 'map'
        return 'unknown'

    def state(self, frame):
        return self.classify(self.read(frame))

    def selected(self, frame):
        # Numeric sale-price badge is above this name region.
        return gift_name(self.text(frame, (455, 285, 380, 118)))

    def sale_details(self, frame):
        text = self.text(frame, (605, 490, 710, 130), confidence=.95, scale=2)
        match = re.fullmatch(r'Sell\s*\[(.+)\]\s*for\s*(\d+)\s*Cost\?', text, re.I)
        if not match:
            raise CheckpointRequired('Could not verify the exact sale name and price.')
        name, level = gift_name(match[1])
        return name, level, int(match[2])

    def slots(self, frame):
        """Locate tier marks; retain the best of overlapping Roman numerals."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hits = []
        for tier, template in self.tiers.items():
            scores = cv2.matchTemplate(gray[290:750, 940:1660], template, cv2.TM_CCOEFF_NORMED)
            for _ in range(40):
                _, value, _, (x, y) = cv2.minMaxLoc(scores)
                if value < .89: break
                hits.append((value, tier, x + 940, y + 290))
                scores[max(0, y-30):y+30, max(0, x-35):x+35] = 0
        result = []
        for score, tier, x, y in sorted(hits, reverse=True):
            if any(abs(x-a[1]) < 65 and abs(y-a[2]) < 65 for a in result): continue
            # Full icon body must be visible; next page covers partial bottom row.
            if y + 86 > 750: continue
            result.append((tier, x, y))
        return sorted(result, key=lambda r: (r[2]//70, r[1]))

    @staticmethod
    def icon(frame, x, y):
        return frame[y+36:y+86, x+22:x+72].copy()

    @staticmethod
    def locate_icon(frame, template):
        region = frame[290:745, 940:1660]
        result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(result)
        return (x+965, y+315) if score >= .96 else None

    def button(self, frame, label):
        matches = [w for w in self.read(frame) if key(w.text) == key(label) and w.score >= .94]
        if len(matches) != 1:
            raise CheckpointRequired(f'Could not uniquely identify the {label} button.')
        return (round(matches[0].x), round(matches[0].y))

    def upgrade_details(self, frame):
        old = gift_name(self.text(frame, (410, 280, 445, 115)))
        new = gift_name(self.text(frame, (1190, 280, 485, 115)))
        text = self.text(frame, (230, 743, 665, 60), confidence=.95)
        match = re.fullmatch(r'Spend\s+(\d+)\s+Cost to Enhance the E\.G\.O Gift\?', text, re.I)
        if not match: raise CheckpointRequired('Unreadable enhancement cost.')
        return old, new, int(match[1])

    def purchase_details(self, frame):
        name = gift_name(self.text(frame, (520, 550, 230, 100), confidence=.93))[0]
        old = self.number(frame, (1235, 230, 54, 46))
        new = self.number(frame, (1318, 230, 48, 46))
        if old < new: raise CheckpointRequired('Invalid purchase balance preview.')
        return name, old-new

    def result_name(self, frame):
        return gift_name(self.text(frame, (480, 610, 275, 118), confidence=.93))[0]

    def offer_tier(self, frame, x, y):
        # Shop thumbnails are 75% of inventory size.
        crop = cv2.cvtColor(frame[y-48:y-15, x-46:x-10], cv2.COLOR_BGR2GRAY)
        crop = cv2.resize(crop, None, fx=4/3, fy=4/3)
        matches = [(cv2.minMaxLoc(cv2.matchTemplate(crop, t, cv2.TM_CCOEFF_NORMED))[1], tier)
                   for tier, t in self.tiers.items() if crop.shape[0] >= t.shape[0] and crop.shape[1] >= t.shape[1]]
        score, tier = max(matches)
        if score < .89: raise CheckpointRequired('Could not verify offered gift tier.')
        return tier

    def verify_forecast(self, frame, keyword):
        import base64, json
        data = json.loads(Path(__file__).with_name('rabbit_hole_shop_assets.json').read_text())
        spec = data[keyword]
        template = cv2.imdecode(np.frombuffer(base64.b64decode(spec), np.uint8), cv2.IMREAD_COLOR)
        score = cv2.minMaxLoc(cv2.matchTemplate(frame[672:728, 580:650], template, cv2.TM_CCOEFF_NORMED))[1]
        def patch_matches(name, roi):
            template = cv2.imdecode(np.frombuffer(base64.b64decode(data[name]), np.uint8), cv2.IMREAD_COLOR)
            x, y, w, h = roi
            return cv2.minMaxLoc(cv2.matchTemplate(frame[y:y+h, x:x+w], template, cv2.TM_CCOEFF_NORMED))[1] >= .96
        if (score < .96 or not patch_matches('tier_iv', (450, 680, 45, 45))
                or not patch_matches('chance_90', (645, 680, 80, 45))):
            raise CheckpointRequired('Fusion must show guaranteed tier IV and 90% for the intended keyword.')
        # Wishmaking costs Starlight. Never enable it as an implicit fallback.
        square = frame[744:773, 396:423]
        if np.mean(cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)) > 65:
            raise CheckpointRequired('Wishmaking must be off for this shop plan.')

    def verify_ingredients(self, frame, icons):
        words = key(self.text(frame, (450, 250, 530, 62), confidence=.90))
        if '33' not in words: raise CheckpointRequired('Fusion confirmation did not show 3/3 ingredients.')
        region = frame[320:610, 190:1120].copy()
        for icon in icons:
            best = (-1, None, None)
            for scale in (i/100 for i in range(100, 221, 2)):
                template = cv2.resize(icon, None, fx=scale, fy=scale)
                _, score, _, pos = cv2.minMaxLoc(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED))
                if score > best[0]: best = (score, pos, template.shape)
            score, (x, y), shape = best
            if score < .88: raise CheckpointRequired('Fusion confirmation ingredients do not match.')
            h, w = shape[:2]
            region[max(0,y-10):y+h+10, max(0,x-10):x+w+10] = 0

    def sp(self, frame, x):
        import base64, json
        data = json.loads(Path(__file__).with_name('rabbit_hole_shop_assets.json').read_text())
        template = cv2.imdecode(np.frombuffer(base64.b64decode(data['sp_minus_40']), np.uint8), cv2.IMREAD_COLOR)
        region = frame[985:1032, x-4:x+48]
        score = cv2.minMaxLoc(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED))[1]
        if score >= .98: return -40
        value = self.number(frame, (x, 987, 43, 43), signed=True)
        b, g, r = np.mean(frame[989:1027, x:x+40], axis=(0, 1))
        if r > b * 1.3 and value >= 0:
            raise CheckpointRequired('Negative SP bubble disagrees with OCR sign.')
        return value

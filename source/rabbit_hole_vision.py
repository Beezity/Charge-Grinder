"""Conservative recognition of the supplied 1920x1080 Hollow screenshots."""
import base64
import json
from pathlib import Path

import cv2
import numpy as np


class HollowVision:
    def __init__(self, path=None):
        path = path or Path(__file__).with_name("rabbit_hole_assets.json")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.templates = {}
        for name, spec in data["templates"].items():
            image = cv2.imdecode(np.frombuffer(base64.b64decode(spec["png_base64"]), dtype=np.uint8),
                                 cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise ValueError(f"Invalid Rabbit Hole template: {name}")
            self.templates[name] = (spec, image)

    def scores(self, frame):
        if frame is None or frame.shape[:2] != (1080, 1920):
            return {}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        result = {}
        for name, (spec, template) in self.templates.items():
            x, y, w, h = spec["search"]
            match = cv2.matchTemplate(gray[y:y+h, x:x+w], template, cv2.TM_CCOEFF_NORMED)
            result[name] = float(cv2.minMaxLoc(match)[1])
        return result

    def observe(self, frame):
        scores = self.scores(frame)
        def has(name):
            return scores.get(name, 0) >= self.templates[name][0]["threshold"]
        # Refuse turn 2, subsequent waves and unrecognized dimensions.
        if not (has("turn1") and has("wave1")):
            return "unknown"
        if has("mao_menu"):
            if has("hollow") and has("menu_overclock"):
                return "overclock_menu"
            if has("le_trou"):
                return "le_trou_menu"
            return "unknown"
        if has("mao_solo") and has("winrate"):
            if has("ready_overclock") and has("start"):
                return "ready"
            if has("slot_overclock") or has("ready_overclock"):
                return "slotted"
            if not has("start"):
                return "battle"
        return "unknown"

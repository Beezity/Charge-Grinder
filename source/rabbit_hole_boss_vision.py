"""Recognition of recorded solo boss layouts at 1920x1080."""
from pathlib import Path
import cv2
from source.rabbit_hole_vision import HollowVision
from source.rabbit_hole_combat_policy import BattleState


class BossVision(HollowVision):
    def __init__(self):
        super().__init__(Path(__file__).with_name('rabbit_hole_boss_assets.json'))

    def locate(self, frame, name):
        if frame is None or frame.shape[:2] != (1080, 1920):
            return None
        spec, template = self.templates[name]
        x,y,w,h = spec['search']
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        match = cv2.matchTemplate(gray[y:y+h,x:x+w], template, cv2.TM_CCOEFF_NORMED)
        _,score,_,point = cv2.minMaxLoc(match)
        if score < spec['threshold']:
            return None
        return (x+point[0]+template.shape[1]//2,y+point[1]+template.shape[0]//2)

    def ego_selected(self, frame):
        return any(self.locate(frame,n) is not None for n in self.templates if n.startswith("ego_slot"))

    def inspect(self, frame):
        scores = self.scores(frame)
        def has(name):
            return scores.get(name,0) >= self.templates[name][0]['threshold']
        turns = [i for i in (1,2,3) if has(f'turn{i}')]
        if not turns and has('winrate') and has('mao_solo'):
            from source.rabbit_hole_shop_vision import ShopVision
            from source.rabbit_hole import CheckpointRequired
            if not hasattr(self,'reader'):
                self.reader = ShopVision()
            try:
                turn = self.reader.number(frame,(88,87,40,45))
                if 4 <= turn <= 20:
                    turns = [turn]
            except CheckpointRequired:
                pass
        if len(turns) != 1:
            return None, None
        bosses = [name for name in ('kod','faelantern','roses') if has(name)]
        if 'faelantern' not in bosses and any(has(n) for n in self.templates if n.startswith('faelantern_')):
            bosses.append('faelantern')
        boss = bosses[0] if len(bosses) == 1 else None
        state = BattleState(turns[0], planning=has('winrate') and has('mao_solo'),
                            emerged=has('emerged') or has('emerged_small'))
        return boss,state

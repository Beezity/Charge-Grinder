"""Exact-name Pack Search with bounded scrolling and replacement verification."""
import base64
import json
from pathlib import Path
import cv2
import numpy as np
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_vision import ShopVision, key

NAMES = {1:'Flat-broke Gamblers',2:"Hell's Chicken",3:'To be Cleaved',4:'Hatred and Despair',5:'Line 2'}

class PackVision:
    def __init__(self, reader=None):
        self.reader=reader or ShopVision()
        data=json.loads(Path(__file__).with_name("rabbit_hole_pack_assets.json").read_text())
        self.templates={k:cv2.imdecode(np.frombuffer(base64.b64decode(v),np.uint8),0) for k,v in data.items()}

    def active(self, frame):
        crop=cv2.cvtColor(frame[295:370,365:460],cv2.COLOR_BGR2GRAY)
        return cv2.minMaxLoc(cv2.matchTemplate(crop,self.templates["search_active"],cv2.TM_CCOEFF_NORMED))[1]>=.90

    def words(self, frame, roi):
        return self.reader.read(frame,roi,scale=2)

    def target(self, frame, floor, library=False):
        roi=(860,290,915,500) if library else (180,630,1560,100)
        words=self.words(frame,roi)
        template=self.templates.get(('library' if library else 'offered')+str(floor))
        if template is not None:
            x,y,w,h=roi
            gray=cv2.cvtColor(frame[y:y+h,x:x+w],cv2.COLOR_BGR2GRAY)
            _,score,_,pos=cv2.minMaxLoc(cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED))
            if score>=.90:
                px=x+pos[0]+template.shape[1]//2;py=y+pos[1]+template.shape[0]//2
                if not library or not any(key(t.text)=='unselectable' and abs(t.x-px)<85 and 0<py-t.y<260 for t in words):
                    return px,py
        matches=[w for w in words if w.score>=.90 and key(w.text)==key(NAMES[floor])]
        if matches and max(w.x for w in matches)-min(w.x for w in matches)<85:
            matches=[max(matches,key=lambda w:w.y)]
        if len(matches)!=1:
            return None
        w=matches[0]
        if library:
            # A pack already offered cannot replace another card.
            if any(key(t.text)=='unselectable' and abs(t.x-w.x)<85 and 0<w.y-t.y<260 for t in words):
                return None
        return (round(w.x),round(w.y))

    def library(self, frame, floor):
        text=''.join(key(w.text) for w in self.words(frame,(350,160,650,70)) if w.score>=.90)
        return f'searchthemepacksforfloor{floor}' in text or (floor==5 and 'searchthemepacksforfloors' in text)

    def replacement(self, frame, floor):
        text=''.join(key(w.text) for w in self.words(frame,(610,355,705,110)) if w.score>=.90)
        before, separator, after = text.partition('replacedwith')
        return bool(separator and before.endswith('packwillbe')
                    and after == key(NAMES[floor]) + 'pack')


def _ready_to_pull(io, floor, vision, frame):
    # Search mode must be off before pulling the selected card.
    if vision.active(frame):
        io.click((280,70))
        frame=io.wait_for(lambda f:not vision.active(f) and vision.target(f,floor) is not None,
                          'Pack Search did not close after selecting the target.')
    point=vision.target(frame,floor)
    if point is None:
        raise CheckpointRequired('The required offered pack is no longer visible; no card was pulled.')
    return point


def search_pack(io, floor, vision):
    """Return a verified offered-card point after at most one purchase."""
    frame=io.capture()
    # Resume an already-open search without clicking through its overlay.
    if vision.library(frame,floor):
        io.click((760,870))
        frame=io.wait_for(lambda f:not vision.library(f,floor),
                          'The existing Pack Search panel did not close.')
    point=vision.target(frame,floor)
    if point:
        return _ready_to_pull(io,floor,vision,frame)
    if not vision.active(frame):
        io.click((280,70))
        io.wait_for(vision.active,'Pack Search mode did not activate.')
    io.click((410,330))
    io.wait_for(lambda f:vision.library(f,floor),'Pack Search did not open.')
    for attempt in range(12):
        frame=io.capture()
        point=vision.target(frame,floor,library=True)
        if point:
            io.click(point)
            io.sleep(.3)
            io.click((1180,870))
            io.wait_for(lambda f:vision.replacement(f,floor),'The replacement confirmation does not name the required pack.')
            io.click((1145,740))
            frame=io.wait_for(lambda f:not vision.library(f,floor) and vision.target(f,floor) is not None,
                              'The purchased pack did not appear in the offered cards.',seconds=15)
            return _ready_to_pull(io,floor,vision,frame)
        # Scroll only inside the pack list; select only a recognized title.
        io.scroll()
        io.sleep(.4)
    raise CheckpointRequired(f'Pack Search could not find selectable {NAMES[floor]}; no substitute was purchased.')


class PackIO:
    def __init__(self):
        from source.rabbit_hole_boss_combat import SoloBattleIO
        from source.rabbit_hole_boss_vision import BossVision
        self.base=SoloBattleIO(BossVision())
    def capture(self):return self.base.capture()
    def click(self,point):self.base.click(point)
    def sleep(self,seconds):
        self.base.guard();self.base.u.time.sleep(seconds)
    def wait_for(self,predicate,detail,seconds=8):return self.base.wait_for(predicate,detail,seconds)
    def scroll(self):
        self.base.guard()
        self.base.u.win_moveTo(1500,650,tsize=(1,1))
        self.base.u.gui.scroll(-4)
    def drag(self,start,end):
        self.base.guard();u=self.base.u
        u.win_moveTo(*start,tsize=(1,1))
        try:u.win_dragTo(*end,duration=.6)
        finally:u.gui.mouseUp()


def select_required_pack():
    from source.utils import utils as u
    from source.rabbit_hole_runtime import checkpoint
    try:
        io=PackIO();point=search_pack(io,u.p.LVL,PackVision())
        io.drag((point[0],500),(point[0],800))
        io.wait_for(lambda f:not u.now.button('PackChoice'),'The selected pack did not enter the floor.',seconds=15)
        u.p.MOVE_ANIMATION=u.p.LVL!=1
        return True
    except CheckpointRequired as exc:
        checkpoint('pack',str(exc))

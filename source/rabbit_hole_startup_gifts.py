"""Verified starter and paid gift-search selection at 1920x1080."""
from pathlib import Path
import cv2
from source.rabbit_hole_vision import HollowVision
from source.rabbit_hole_boss_combat import SoloBattleIO
from source.rabbit_hole import CheckpointRequired


class StartupVision(HollowVision):
    def __init__(self):
        super().__init__(Path(__file__).with_name('rabbit_hole_startup_assets.json'))

    def has(self, frame, name):
        return self.locate(frame, name) is not None

    def locate(self, frame, name):
        if frame is None or frame.shape[:2] != (1080,1920):
            return None
        spec, template = self.templates[name]
        x,y,w,h = spec['search']
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        result = cv2.matchTemplate(gray[y:y+h,x:x+w],template,cv2.TM_CCOEFF_NORMED)
        _,score,_,point = cv2.minMaxLoc(result)
        if score < spec['threshold']:
            return None
        return x+point[0]+template.shape[1]//2, y+point[1]+template.shape[0]//2


class StartupIO(SoloBattleIO):
    def wait_search(self):
        deadline = self.u.time.monotonic()+45
        confirmed = False
        while self.u.time.monotonic()<deadline:
            frame = self.capture()
            if self.vision.has(frame,'search'):
                return
            # Retain the upstream acknowledgement after selecting a starter.
            if not confirmed and self.u.now.button('Confirm.0'):
                self.press('space')
                confirmed = True
            self.u.time.sleep(.2)
        raise CheckpointRequired('The EGO Gift Search screen did not open after the starter selection.')

    def wait_entered(self):
        deadline = self.u.time.monotonic()+45
        while self.u.time.monotonic()<deadline:
            self.guard()
            if self.u.now.button('PackChoice') or self.u.now.button('Move'):
                return
            self.u.time.sleep(.2)
        raise CheckpointRequired('Gift search was confirmed, but dungeon entry did not finish. The purchase was not repeated.')


def select_starting_gifts(io):
    v=io.vision
    frame=io.capture()
    if v.has(frame,'starter'):
        # Like Arayashu, enable the follow-up search after the free starter.
        io.guard()
        io.u.now_click.button('giftSearch')
        io.wait_for(lambda f:v.has(f,'search_on'),'Gift Search is not enabled.')
        io.click((535,665))  # Poise, not the preset's Rupture affinity.
        io.wait_for(lambda f:v.has(f,'cigarette'),'Cigarette Holder is not visible.')
        frame=io.capture()
        if not (v.has(frame,'cigarette_border') and v.has(frame,'starter_selected')):
            io.click((1239,395))
        io.wait_for(lambda f:v.has(f,'cigarette') and v.has(f,'cigarette_border') and v.has(f,'starter_selected'),
                    'Cigarette Holder selection was not verified.')
        io.click((1624,882))
        io.wait_search()
    elif not v.has(frame,'search'):
        raise CheckpointRequired('Neither the starter nor the EGO Gift Search screen is recognized.')

    io.click((985,286))  # Arayashu's existing Keywordless search tab.
    io.wait_for(lambda f:v.has(f,'search') and v.has(f,'keywordless'),
                'The Keywordless search tab is not selected.')
    frame=io.capture()
    if not any(v.has(frame,n) for n in ('count0','count1','count2')):
        raise CheckpointRequired('Unrecognized search count; no gifts selected.')
    if v.has(frame,'count1') and not v.has(frame,'welcome_name'):
        raise CheckpointRequired('An unexpected gift is already selected. No purchase was made.')
    if v.has(frame,'count2') and not (v.has(frame,'welcome_name') and v.has(frame,'needle_name')):
        raise CheckpointRequired('Unexpected gifts are already selected. No purchase was made.')
    # Do not trust hovered/highlighted icons: verify the selected list and count.
    for icon,label in (('welcome_icon','welcome_name'),('needle_icon','needle_name')):
        frame=io.capture()
        if v.has(frame,label):
            continue
        point=v.locate(frame,icon)
        if point is None:
            raise CheckpointRequired('Required starting gift is not visible on the Keywordless search tab.')
        io.click(point)
        io.wait_for(lambda f:v.has(f,label),'The selected gift did not appear in the search list.')
    io.wait_for(lambda f:v.has(f,'welcome_name') and v.has(f,'needle_name')
                and v.has(f,'count2') and v.has(f,'cost160'),
                'Expected exactly Grand Welcome and Sharp Needle & Thread, totaling 160 Starlight.')
    io.click((1645,860))
    io.wait_for(lambda f:v.has(f,'confirm160'),'The 160-Starlight search confirmation was not verified.')
    io.click((1149,743))
    io.wait_entered()


def run_starting_gifts():
    from source.rabbit_hole_runtime import checkpoint
    try:
        select_starting_gifts(StartupIO(StartupVision()))
    except CheckpointRequired as exc:
        checkpoint('starting-gifts',str(exc))

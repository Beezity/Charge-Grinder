"""Solo battle controller with verified selection and battle-local EGO history."""
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_combat import DesktopInput
from source.rabbit_hole_combat_policy import BattlePolicy
from source.rabbit_hole_shop_vision import ShopVision, key


class SoloBattleIO(DesktopInput):
    def __init__(self, vision):
        super().__init__(vision)
        self.reader = None

    def capture(self):
        self.guard()
        return self.u.screenshot()

    def observe_battle(self):
        return self.vision.inspect(self.capture())

    def wait_for(self, predicate, detail, seconds=8):
        deadline = self.u.time.monotonic() + seconds
        hits = 0
        while self.u.time.monotonic() < deadline:
            frame = self.capture()
            hits = hits + 1 if predicate(frame) else 0
            if hits >= 2:
                return frame
            self.u.time.sleep(.15)
        raise CheckpointRequired(detail + ' No input was repeated.')

    def auto_select(self, mode):
        frame = self.capture()
        point = self.vision.locate(frame, 'winrate')
        if point is None:
            raise CheckpointRequired('The combat selection controls are not verified.')
        # Both controls are present in the supplied full-size captures.
        self.click(point if mode == 'winrate' else (point[0],point[1]+59))
        self.wait_for(lambda f: self.vision.locate(f,'start') is not None,
                      f'{mode} did not produce the Start control.')

    def card_visible(self, frame, card):
        if self.vision.locate(frame,card) is not None:
            return True
        labels = {'le_trou':'letrou','boucher':'boucheruntrou'}
        return any(w.score >= .94 and key(w.text) == labels[card]
                   for w in self._reader().read(frame,(1040,495,320,55),scale=2))

    def overclock_visible(self, frame):
        return self.vision.locate(frame,'menu_overclock') is not None

    def choose_ego(self, action):
        frame = self.capture()
        slots = self.vision.targets(frame,'mao_solo')
        point = min(slots,key=lambda pos:pos[0]) if slots else None
        if point is None:
            raise CheckpointRequired('Mao Faust is not selectable for EGO.')
        self.hold(point,1.5)
        card = 'le_trou' if action in ('le_trou','hollow') else 'boucher'
        self.wait_for(lambda f: self.vision.locate(f,'mao_menu') is not None and
                      self.card_visible(f,card),
                      f'The expected {card} card is not visible.')
        if action == 'hollow':
            self.hold((1180,391),1.5)
            self.wait_for(lambda f: self.overclock_visible(f),
                          'Hollow corrosion was not verified.')
        self.click((1180,391))
        self.wait_for(lambda f: self.vision.ego_selected(f) and
                      self.vision.locate(f,'mao_menu') is None,
                      'The selected EGO did not appear in the skill slot.')
        self.auto_select('winrate')
        if not self.vision.ego_selected(self.capture()):
            raise CheckpointRequired('Win Rate did not retain the selected EGO.')

    def start(self, state):
        if self.vision.locate(self.capture(),'start') is None:
            raise CheckpointRequired('Start is not visible; no turn was started.')
        self.press('enter')
        self.wait_for(lambda f: self.vision.locate(f,'winrate') is None,
                      'The turn did not leave the planning screen.',seconds=12)

    def finished(self):
        return any(self.u.now.button(name) for name in
                   ('EGObin','encounterreward','victory','defeat','Move','PackChoice'))

    def _reader(self):
        if self.reader is None:
            self.reader = ShopVision()
        return self.reader

    def retarget_ego(self, source, target):
        self.guard()
        self.u.win_moveTo(*source, tsize=(1,1))
        try:
            self.u.win_dragTo(*target, duration=.5, tsize=(1,1))
        finally:
            self.u.gui.mouseUp()
        self.guard()
        self.u.time.sleep(.3)

    def verify_roses(self):
        # Win Rate may clash with a part whose weight does not cover the flower.
        # Try only recognized boss skills; never start an unverified arrangement.
        tried=[]
        for _ in range(7):
            frame=self.capture()
            if self.vision.roses_targets(frame):
                self.wait_for(self.vision.roses_targets,
                              'Roses target coverage changed before Start.')
                return
            sources=[self.vision.locate(frame,n) for n in self.vision.templates
                     if n.startswith('ego_slot')]
            sources=[point for point in sources if point is not None]
            targets=[]
            for name in ('roses_red','roses_red_alt','roses_green','roses_green_alt'):
                targets.extend(self.vision.targets(frame,name))
            candidates=[point for point in sorted(targets)
                        if all(abs(point[0]-old[0])+abs(point[1]-old[1])>25 for old in tried)]
            if not sources or not candidates or len(tried)>=6:
                break
            point=candidates[0]
            tried.append(point)
            self.retarget_ego(min(sources,key=lambda p:p[0]),point)
        raise CheckpointRequired('Boucher could not cover both Roses parts and the flower after bounded retargeting. No turn was started.')

    def reset(self):
        # The supplied clip verifies Esc -> Retry Stage -> defeat/loading.
        # This action has no separate confirmation dialog.
        self.press('esc')
        frame = self.wait_for(lambda f: self.vision.locate(f,'retry_stage') is not None,
                              'The Retry Stage menu did not appear.')
        self.click(self.vision.locate(frame,'retry_stage'))
        deadline = self.u.time.monotonic()+60
        deployed=False
        while self.u.time.monotonic() < deadline:
            self.guard()
            _,state = self.observe_battle()
            if state is not None and state.turn == 1 and state.planning:
                return state
            if self.u.now.button('TOBATTLE') and not deployed:
                from source.battle import select
                if not select(['FAUST']):
                    raise CheckpointRequired('Could not redeploy Faust after Retry Stage.')
                deployed=True
            self.u.time.sleep(.2)
        raise CheckpointRequired('Retry Stage did not return to a verified turn-1 battle; no retry click was repeated.')

    def wait(self):
        self.guard()
        self.u.time.sleep(.2)


def advance(policy, state, io):
    """Perform at most one verified action for this observed turn."""
    action = policy.decide(state)
    if action in ('wait','finished'):
        return action
    if action == 'reset':
        policy.reset_verified(io.reset())
        return 'reset'
    if action in ('le_trou','boucher','boucher_roses','hollow'):
        io.choose_ego('boucher' if action == 'boucher_roses' else action)
        if action == 'boucher_roses':
            io.verify_roses()
    else:
        io.auto_select('damage' if action == 'damage' else 'winrate')
    io.start(state)
    policy.started(action,state)
    return action


def run_solo_battle(vision, encounter):
    from source.rabbit_hole_runtime import checkpoint
    io = SoloBattleIO(vision)
    policy = BattlePolicy(encounter)
    resets = 0
    deadline = io.u.time.monotonic() + 180
    try:
        while io.u.time.monotonic() < deadline:
            io.guard()
            if io.finished():
                io.u.p.RABBIT_NODE = None
                return
            detected,state = io.observe_battle()
            if detected is not None and detected != encounter:
                raise CheckpointRequired('The recognized boss changed during this battle.')
            if state is not None:
                if policy.decide(state) == 'reset' and resets >= 3:
                    raise CheckpointRequired('KoD reached turn 3 after three retries; stopped to avoid a retry loop.')
                action = advance(policy,state,io)
                if action == 'reset':
                    resets += 1
                if action not in ('wait','finished'):
                    deadline = io.u.time.monotonic()+180
            io.wait()
        raise CheckpointRequired('The battle did not advance within 180 seconds.')
    except CheckpointRequired as exc:
        checkpoint('combat',str(exc))

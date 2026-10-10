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

    def choose_ego(self, action):
        frame = self.capture()
        point = self.vision.locate(frame,'mao_solo')
        if point is None:
            raise CheckpointRequired('Mao Faust is not selectable for EGO.')
        self.hold(point,1.5)
        card = 'le_trou' if action == 'le_trou' else 'boucher'
        self.wait_for(lambda f: self.vision.locate(f,'mao_menu') is not None and
                      self.card_visible(f,card),
                      f'The expected {card} card is not visible.')
        # Click once for Awakening. No hold to force overclock/corrosion.
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

    def text_button(self, frame, labels):
        words = self._reader().read(frame)
        matches = [w for w in words if w.score >= .94 and key(w.text) in labels]
        if len(matches) != 1:
            raise CheckpointRequired('The expected battle retry control is not uniquely recognized.')
        return (round(matches[0].x),round(matches[0].y))

    def reset(self):
        # Never use the run-forfeit action as a battle retry.
        self.press('esc')
        self.u.time.sleep(.3)
        frame = self.capture()
        point = self.text_button(frame,{'retry','retrybattle','restartbattle','retrystage'})
        self.click(point)
        self.u.time.sleep(.3)
        frame = self.capture()
        words = self._reader().read(frame)
        prompt = key(' '.join(w.text for w in words if w.score >= .94))
        if 'battle' not in prompt or not ('retry' in prompt or 'restart' in prompt):
            raise CheckpointRequired('Battle retry confirmation is unrecognized; no confirmation was clicked.')
        self.click(self.text_button(frame,{'confirm'}))
        result = self.wait_for(lambda f: (lambda b,s: s is not None and s.turn == 1 and s.planning)(
            *self.vision.inspect(f)), 'Battle retry did not return to turn 1.',seconds=45)
        return self.vision.inspect(result)[1]

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
    if action == 'boucher_roses':
        raise CheckpointRequired('Sign of Roses requires verified Rose, Signpost and Flesh targeting; no turn was started.')
    if action in ('le_trou','boucher'):
        io.choose_ego(action)
    else:
        io.auto_select('damage' if action in ('damage','wait_emergence') else 'winrate')
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

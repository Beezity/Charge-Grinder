"""Windows shop adapter calibrated from the two October 10 recordings.

No transaction is retried. Observation may open/cancel sale confirmations to
read exact names and prices, but never confirms a sale. The controller alone
chooses which verified transaction to perform.
"""
from itertools import combinations
import re
import time
import cv2
from source.rabbit_hole import CheckpointRequired
from source.rabbit_hole_shop_policy import (ShopState, Sale, Offer, Fusion, PROTECTED,
                                           REQUIRED_BY_FLOOR)
from source.rabbit_hole_shop_vision import ShopVision, key, gift_name

MENU = {'sell': (595, 585), 'upgrade': (250, 585), 'fuse': (410, 585)}
SINNERS = {'Yi Sang': (150, 970), 'Faust': (260, 970)}


class WindowsShopIO:
    def __init__(self):
        from source.utils import utils
        self.u = utils

    def guard(self):
        if self.u.p.stop_event.is_set(): raise self.u.StopExecution
        if self.u.p.LIMBUS_NAME not in (self.u.gui.getActiveWindowTitle() or ''):
            raise CheckpointRequired('Limbus lost focus during a shop operation.')

    def capture(self):
        self.guard()
        return self.u.screenshot()

    def click(self, point):
        self.guard()
        self.u.win_click(*point, tsize=(1, 1))
        self.u.win_moveTo(1810, 830, tsize=(1, 1))

    def scroll(self, amount):
        self.guard()
        self.u.win_moveTo(1580, 590, tsize=(1, 1))
        self.u.gui.scroll(amount)
        self.u.win_moveTo(1810, 830, tsize=(1, 1))

    def wait(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.guard()
            time.sleep(.05)


class WindowsShopAdapter:
    def __init__(self, floor, io=None, vision=None):
        self.floor = floor
        self.io = io or WindowsShopIO()
        self.vision = vision or ShopVision()
        self.icons = {}
        self.inventory = {}
        self.offers = {}
        self.before = None
        self.last_fusion_result = None

    def expect(self, *states):
        previous = None
        for _ in range(12):
            self.io.wait(.2)
            frame = self.io.capture()
            state = self.vision.state(frame)
            if state in states and previous == state: return frame
            previous = state
        raise CheckpointRequired(f'Shop did not reach {states}; no input was repeated.')

    def click_wait(self, point, *states):
        self.io.click(point)
        return self.expect(*states)

    def open_panel(self, panel):
        self.expect('shop')
        self.click_wait(MENU[panel], panel)
        self.io.scroll(30)
        self.io.wait(.4)

    def close_panel(self):
        self.click_wait((735, 876), 'shop')

    def currency(self, frame):
        return self.vision.number(frame, (857, 175, 99, 57))

    def scan_inventory(self):
        self.open_panel('sell')
        owned, sales, icons, tiers = {}, [], {}, {}
        previous_layout = None
        for page in range(16):
            frame = self.expect('sell')
            slots = self.vision.slots(frame)
            layout = []
            for tier, x, y in slots:
                icon = self.vision.icon(frame, x, y)
                # Previously read gifts can recur on adjacent scroll pages.
                known = next((n for n, t in icons.items()
                              if cv2.matchTemplate(icon, t, cv2.TM_CCOEFF_NORMED)[0, 0] >= .97), None)
                if known:
                    layout.append((known, round(y/8)))
                    continue
                self.click_wait((x+48, y+55), 'sell')
                confirm = self.click_wait((1190, 876), 'sale_confirm')
                name, level, price = self.vision.sale_details(confirm)
                self.click_wait((780, 777), 'sell')  # Cancel; observation never sells.
                if name in owned:
                    raise CheckpointRequired('Duplicate or ambiguous inventory identity; cannot prove a complete scan.')
                owned[name], icons[name], tiers[name] = level, icon, tier
                sales.append(Sale(name, price, True, tier))
                layout.append((name, round(y/8)))
            signature = tuple(layout)
            if previous_layout == signature:
                self.close_panel()
                self.icons, self.inventory = icons, tiers
                return owned, tuple(sales)
            previous_layout = signature
            self.io.scroll(-3)
            self.io.wait(.4)
        raise CheckpointRequired('Inventory scan did not reach its end within 16 pages.')

    def find_item(self, name):
        template = self.icons.get(name)
        if template is None: raise CheckpointRequired(f'No verified icon for {name}.')
        self.io.scroll(30)
        self.io.wait(.4)
        for _ in range(16):
            frame = self.io.capture()
            point = self.vision.locate_icon(frame, template)
            if point: return point
            self.io.scroll(-3)
            self.io.wait(.3)
        raise CheckpointRequired(f'Could not relocate {name}; no transaction was confirmed.')

    def observe(self):
        frame = self.expect('shop')
        currency = self.currency(frame)
        sp = {}
        # Read only the relevant sinner; unrelated low-resolution SP does not
        # prevent visiting the shop. Yi Sang is the event-check ID in the video.
        name = 'Yi Sang' if self.floor == 1 else 'Faust' if self.floor == 4 else None
        if name:
            x = 155 if name == 'Yi Sang' else 267
            value = self.vision.sp(frame, x)
            if not -45 <= value <= 45: raise CheckpointRequired('Invalid SP reading.')
            sp[name] = value
        offers = self.read_offers(frame)
        owned, sales = self.scan_inventory()
        # Return to a fresh main screen so projected transaction totals cannot
        # be confused with the actual balance.
        if self.currency(self.expect('shop')) != currency:
            raise CheckpointRequired('Currency changed during read-only inventory scan.')
        for target in ('Clear Mirror, Calm Water', 'Artistic Sense'):
            if target in owned:
                self.open_panel('upgrade')
                selected = self.click_wait(self.find_item(target), 'upgrade')
                name, level = self.vision.selected(selected)
                if name != target: raise CheckpointRequired('Enhancement inventory identity did not match.')
                owned[target] = level
                self.close_panel()
        fusions = self.plan_fusions(owned)
        state = ShopState(currency, owned, sp, offers, sales, fusions,
                          'Yi Sang' if self.floor == 1 else None)
        self.before = state
        return state

    def read_offers(self, frame):
        offers, locations = [], {}
        for x, y in [(1167, 399), (1400, 399), (1632, 399), (935, 630), (1167, 630)]:
            try:
                text = self.vision.text(frame, (x-110, y+92, 220, 66), confidence=.93)
                if key(text) in ('purchased', ''): continue
                name, _ = gift_name(text)
                price = self.vision.number(frame, (x-11, y+56, 66, 40))
                tier = self.vision.offer_tier(frame, x, y)
            except CheckpointRequired:
                # Unreadable offers are unavailable, never blindly purchased.
                continue
            offers.append(Offer(name, tier, price, True))
            locations[name] = (x, y)
        self.offers = locations
        return tuple(offers)

    def plan_fusions(self, owned):
        candidates = [n for n in owned if n not in PROTECTED
                      and not (self.floor == 1 and n == 'Grand Welcome')]
        candidates.sort(key=lambda n: (n == 'Cigarette Holder', self.inventory[n], n))
        points = {1: 3, 2: 6, 3: 10, 4: 15}
        combo = next((c for c in combinations(candidates, 3)
                      if 25 <= sum(points[self.inventory[n]] for n in c) <= 45), None)
        if not combo: return ()
        return tuple(Fusion(n, combo, 0, True, True)
                     for n in sorted(REQUIRED_BY_FLOOR[self.floor] - owned.keys()))

    def execute(self, action):
        if self.before is None: raise CheckpointRequired('Shop must be observed before acting.')
        if action.kind == 'sell': self.sell(action)
        elif action.kind == 'upgrade': self.upgrade(action)
        elif action.kind == 'heal': self.heal(action)
        elif action.kind == 'buy': self.buy(action)
        elif action.kind == 'fuse': self.fuse(action)
        else: return False
        return True

    def sell(self, action):
        if action.name in PROTECTED or (self.floor == 1 and action.name == 'Grand Welcome'):
            raise CheckpointRequired('Refusing to sell a protected gift.')
        expected = next((s for s in self.before.sales if s.name == action.name and s.verified), None)
        if expected is None: raise CheckpointRequired('Sale was not observed.')
        self.open_panel('sell')
        self.click_wait(self.find_item(action.name), 'sell')
        frame = self.click_wait((1190, 876), 'sale_confirm')
        name, level, price = self.vision.sale_details(frame)
        if (name, level, price) != (action.name, self.before.owned[action.name], expected.price):
            raise CheckpointRequired('Sale confirmation does not match the planned item and price.')
        self.click_wait((1140, 777), 'sell')
        self.close_panel()

    def upgrade(self, action):
        if action.name not in {'Clear Mirror, Calm Water', 'Artistic Sense'} or self.floor != 4:
            raise CheckpointRequired('Upgrade is outside the Rabbit Hole plan.')
        self.open_panel('upgrade')
        self.click_wait(self.find_item(action.name), 'upgrade')
        self.click_wait((1190, 876), 'upgrade_confirm')
        # Select one tier, making each policy action cost 100 or 200.
        level = self.before.owned[action.name]
        frame = self.click_wait((1365 if level == 0 else 1548, 768), 'upgrade_confirm')
        old, new, cost = self.vision.upgrade_details(frame)
        expected_level = self.before.owned[action.name]
        if old != (action.name, expected_level) or new != (action.name, expected_level+1) or cost != action.cost:
            raise CheckpointRequired('Upgrade names, levels or cost did not match.')
        self.click_wait((1190, 876), 'upgrade')
        self.close_panel()

    def heal(self, action):
        required = 'Yi Sang' if self.floor == 1 else 'Faust' if self.floor == 4 else None
        if action.name != required or action.cost != 100:
            raise CheckpointRequired('SP healing is outside the floor-specific plan.')
        self.expect('shop')
        self.click_wait((295, 707), 'heal')
        frame = self.expect('heal')
        text = self.vision.text(frame, (1240, 241, 500, 45), confidence=.93)
        price = self.vision.number(frame, (1770, 244, 48, 44))
        if not re.search(r'greatlyh?healasingle', key(text)) or price != 100:
            raise CheckpointRequired('Could not verify the single-sinner healing option.')
        self.click_wait((1530, 305), 'heal_select')
        frame = self.click_wait(SINNERS[action.name], 'heal_select')
        # The visible Select button is required before committing healing.
        if 'select' not in key(self.vision.text(frame, (1590, 923, 270, 90))):
            raise CheckpointRequired('Selected-sinner healing was not ready.')
        frame = self.click_wait((1710, 970), 'heal_result', 'shop')
        if self.vision.state(frame) == 'heal_result':
            result = key(self.vision.text(frame, (100, 560, 470, 55), confidence=.90))
            if key(action.name) not in result:
                raise CheckpointRequired('Healing result did not identify the intended sinner.')
            self.click_wait((1710, 970), 'shop')

    def buy(self, action):
        offer = next((o for o in self.before.offers if o.name == action.name and o.price == action.cost), None)
        if offer is None or action.name not in self.offers:
            raise CheckpointRequired('Purchase was not observed.')
        self.expect('shop')
        frame = self.click_wait(self.offers[action.name], 'buy_confirm')
        name, price = self.vision.purchase_details(frame)
        if name != action.name or price != action.cost:
            raise CheckpointRequired('Purchase confirmation differs from the offer.')
        # Button is found from its visible label, not a guessed popup coordinate.
        self.io.click(self.vision.button(frame, 'Purchase'))
        frame = self.expect('gift_result')
        self.click_wait(self.vision.button(frame, 'Confirm'), 'shop')

    def fuse(self, action):
        if (len(action.ingredients) != 3 or len(set(action.ingredients)) != 3
                or any(n in PROTECTED for n in action.ingredients)
                or any(n not in self.before.owned for n in action.ingredients)):
            raise CheckpointRequired('Fusion ingredients are not verified unprotected gifts.')
        keyword = 'POISE' if action.name in {'Fragment of Conceit', 'Clear Mirror, Calm Water'} else 'SINKING'
        self.open_panel('fuse')
        frame = self.click_wait((545, 540), 'keyword')
        self.io.click(self.vision.button(frame, keyword))
        self.click_wait((1190, 849), 'fuse')
        for name in action.ingredients:
            self.click_wait(self.find_item(name), 'fuse')
        frame = self.expect('fuse')
        self.vision.verify_forecast(frame, keyword)
        frame = self.click_wait((1190, 876), 'fusion_confirm')
        self.vision.verify_ingredients(frame, [self.icons[n] for n in action.ingredients])
        self.click_wait((1190, 876), 'gift_result')
        frame = self.expect('gift_result')
        self.last_fusion_result = self.vision.result_name(frame)
        self.click_wait(self.vision.button(frame, 'Confirm'), 'fuse')
        self.close_panel()

    def leave(self):
        self.expect('shop')
        frame = self.click_wait((1705, 967), 'leave_confirm')
        self.io.click(self.vision.button(frame, 'Confirm'))
        self.expect('map')


def run_windows_shop():
    from source.utils import params as p
    from source.rabbit_hole_runtime import checkpoint
    from source.rabbit_hole_shop_controller import run_shop
    try:
        report = run_shop(p.LVL, WindowsShopAdapter(p.LVL))
        print('Rabbit Hole shop complete; unavailable:', ', '.join(report.missing))
    except CheckpointRequired as exc:
        checkpoint('shop', str(exc))

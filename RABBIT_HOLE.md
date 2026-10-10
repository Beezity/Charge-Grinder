# Rabbit Hole / Mao Faust — assisted calibration draft

Target: Windows, English Limbus Company, **1920×1080 game client**, Mao Faust.
Based on Walpth/Charge-Grinder commit `306d17325a5b76fc54ca3e036c5d87ab3a730036`.
Strategy source: [Rabbit Hole, updated 8 October 2026](https://docs.google.com/spreadsheets/d/1xt72hupklzKFN8AEvsjphApR1D2CRyYvurzAFMxA76s/htmlview#gid=486536596).

**This draft does not automate a complete run.** It adds strict pack selection,
the floor-5 difficulty switch, conservative map navigation, early first-turn
Hollow overclock and manual checkpoints.
The shop adapter now handles purchases, sales, fusion, upgrades and SP healing
with visual verification. The new solo combat controller selects Le Trou and Boucher
un trou, resets KoD at turn 3, verifies Roses attack-weight targets, and applies
Win Rate/Damage fallbacks. Gifts, trials,
unrecognized combat, unrecognized trials and unavailable exact packs still require manual
action. Shared event, gift/card reward, end-of-run and defeat handlers are connected. MD entry, preset selection and graces reuse the upstream startup flow;
starting gifts now use the calibrated free-starter and gift-search sequence. Shop and combat inputs await live Windows validation.
Windows input and live recognition have not been tested in this environment.

## Windows setup

Extract the full ZIP into a new folder. This is Python source, not a prebuilt EXE.
Use 64-bit Python **3.11 or 3.12** for the shop OCR dependency. In that folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-rabbit-hole.txt
```

Use a fresh virtual environment: the Rabbit Hole requirements include OpenCV
through RapidOCR, and should not be mixed with a separate OpenCV-headless install.
OCR runs locally using bundled CPU models; no cloud OCR account is required.

The current upstream Windows input bridge and its startup checks are retained.
If your existing Charge-Grinder setup cannot initialize that bridge, this draft
cannot control the game either. No bridge/driver changes are included here.

Double-click `Start-Rabbit-Hole.bat`. Enter the current floor, or the destination
floor if on pack selection. The window title explicitly says “assisted draft”.
Enable **Rabbit Hole (Rupture)** beside Arayashu in the configuration panel.
The dedicated launcher enables it by default; it is also available from `App.py`.
The toggle is saved with your settings. Select exactly one MD team with
**Rupture as its first keyword**, and disable Arayashu, Extreme and Luxcavation.
Name/tag the in-game preset Rupture as shown in your team screenshot.
Ordinary Rupture behavior is available with the Rabbit Hole toggle off.
The app's ordinary affinity/shop settings are not used by this assisted runtime.
Prepare the correct Mao Faust team manually. For eligible early encounters the
runtime deploys Faust alone using upstream selection, including the confirmed
solo Faelantern configuration.

Prepare a level 60+ UT3+ Mao Faust preset with only Hollow equipped
(TS3+, TS4 preferred). Start automation from the home/Drive/MD entry screen
with floor 1 selected, or resume at a pack/map screen with the current floor.
The existing MD startup flow selects the Rupture preset and graces 1 and 3.
It enables Gift Search like Arayashu, takes Cigarette Holder from Poise, then
selects Grand Welcome and Sharp Needle & Thread on the Keywordless search tab.
Before purchasing, it verifies both selected names, exactly two gifts and the
160-Starlight total, then verifies the confirmation dialog and enters the dungeon.
The guide estimates about 21 Starlight lost per run. The draft does not configure
identities/EGO. Windows timing still needs live validation.

At each checkpoint automation stops and saves a screenshot under
`data/rabbit-hole/`. Read the instruction, complete the step manually, then start
again in the same app. The last recognized floor is retained in that app session.
Each start asks for the current floor, so correct it if you changed floors
manually or started a new run. The app run count controls repeated runs. Successful runs use the shared reward
collection flow; failed runs use the shared defeat flow and respect Restart.
Three consecutive failed runs stop automation. Enkephalin checks use the existing
setting and handler. New runs reset to floor 1 and repeat the prepared startup.

Launching `App.py` uses the saved Rabbit Hole toggle. Check the toggle and window
title before starting; the keyword alone does not enable Rabbit Hole.

## Route and decisions

| Floor | Difficulty | Required pack | Combat and shop strategy |
| --- | --- | --- | --- |
| 1 | Normal | Flat-broke Gamblers | Solo Faust, overclock Hollow. Buy T2/T3 material. SP-heal a non-Faust event-check ID to 45. |
| 2 | Normal | Hell's Chicken | Overclock Hollow. Buy T2/T3 material and fuse Fragment of Conceit. Grand Welcome can be consumed now. Keep CMCW unupgraded. |
| 3 | Normal | To Be Cleaved | Avoid risky encounters. Overclock regular fights. Do not auto-heal Faust here; finish Poise Rock. Use Awakening on boss turns 1/2. |
| 4 | Normal | Hatred and Despair | Heal Faust to 45 SP. Have Poise Rock, CMCW++, Sinking Rock and Artistic Sense++. Awakening turns 1/2; retry if KoD survives turn 2. |
| 5 | Hard | Line 2 | Solo Faust, no new SP heal. Awakening turns 1/2; turn 2 must hit Rose, Signpost and Flesh. |

Faelantern on floor 3 fields Mao Faust solo. Use Win Rate until the emerged
state is recognized, then hold Le Trou to select Hollow corrosion. Surviving
Faelantern uses Damage. EGO selection holds Faust's leftmost recognized slot.

Pack selection now checks the required offered title first. If absent, it opens
Pack Search, chooses a replacement slot, scrolls the search list, and buys the
exact target only after the confirmation names it. It then verifies the replaced
card before pulling it. Floors 1–4 stay Normal; floor 5 switches to Hard for Line 2.
Missing or unselectable targets stop without purchasing a substitute.

Whole-path routing prefers safer recognized paths, permits unavoidable risky
paths, and uses the existing map fallback for unknown nodes. Live Windows
validation is still required.

## Early Hollow overclock

The five supplied screenshots calibrate these transitions at 1920×1080:

1. Recognize turn 1, wave 1/1, solo Mao's portrait and the single-slot battle layout.
2. Hold the portrait to open EGO selection; verify Le Trou is visible.
3. Hold Le Trou to overclock; verify both Hollow and the overclock warning.
4. Click the card to slot it; verify the slotted overclock warning.
5. Press P to select targets; verify START and the overclock skill remain visible.
6. Press Enter once and wait for the encounter to finish.

This is enabled on floors 1/2 and on floor 3 only when the bot entered a recognized
non-boss combat node. Resuming an unknown floor-3 encounter stops for manual review.
This overclock sequence itself does not handle Awakening or later waves. If
enemies survive, the new controller applies Win Rate on later recognized solo
turns instead of selecting EGO again. Unrecognized layouts still stop. Failed transitions stop
without repeated clicks. A turn that does not finish in 180 seconds also stops.
Switching away or stopping during a hold releases the mouse button.

The hold duration and Windows input behavior still need a live trial. Recognition
tests use the supplied frames, not independent gameplay captures.

## Milestone 4 — combat controller draft

The five combat videos supplied on 10 October calibrate turn counters 1/2/3,
Boucher's menu, selected EGO, KoD/Faelantern/Roses scenes, and Faelantern's emerged
and held-click overlay states, the Retry Stage menu and Roses target arrows. EGO usage is recorded only after a verified turn
start; duplicate planning frames cannot repeat an input. Resuming a later turn
without usage history stops rather than guessing whether EGO was used.

- KoD: Le Trou then Boucher; counter 3 triggers a battle retry before a fallback.
  The supplied retry clip calibrates Esc → Retry Stage → defeat/loading, with
  no separate confirmation. The handler redeploys Faust if selection appears and
  waits for verified turn 1 before clearing EGO usage. At most three retries are
  attempted; timeouts never repeat the retry click.
- Faelantern: Win Rate until emerged and selectable, then Hollow corrosion.
  Surviving enemies use Damage. Charm does not cause a retry.
- Other supported solo fights: after overclock Hollow or Boucher, surviving enemies
  use Win Rate. Ordinary later-floor solo encounters now select Awakening.
- Sign of Roses: Le Trou on turn 1; Boucher on turn 2. Before starting, require
  a yellow clash arrow at one body part, cyan attack-weight arrow at the other
  body part, and cyan attack-weight arrow at the flower. The reader identifies
  both body skill groups and the flower separately. Missing coverage stops
  without starting or recording Boucher as used. Changed layouts still need
  calibration; this build does not guess targets or drag across unknown layouts.

Still needed: independent Windows input trials, KoD retry completion through
redeployment, and remaining layout coverage. Roses arrows and the retry menu
are calibrated from the supplied recordings. This is a combat implementation
draft; Milestone 4 still requires live validation.

Checkpoint screenshots are local only; the draft does not upload them.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**93 tests pass locally**, including policy/controller/settings tests, five supplied combat
screenshot cases, eight shop video replay tests, and twenty-five new combat checks
(eight replay the new recordings). To include the originals:

```powershell
$env:RABBIT_CAPTURE_DIR = "C:\path\to\combat-screenshots"
$env:RABBIT_SHOP_VIDEO_DIR = "C:\path\to\OBS Recordings"
$env:RABBIT_COMBAT_VIDEO_DIR = "C:\path\to\OBS Recordings"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Original videos are not distributed. Shop replays read
`2026-10-10 09-19-07.mp4` and `2026-10-10 09-21-37.mp4`. Combat replays read
the supplied `11-06-36`, `11-08-43`, `11-11-00`, `11-14-17` and `11-17-41` clips
from 10 October 2026.

Mechanics reference: [Faelantern/Enemy](https://limbuscompany.wiki.gg/wiki/Faelantern/Enemy).
The indexed page confirms solo Charm exclusion and that breaking Fairy exposes
Body. It does not independently document the portrait-color UI cue.
Desktop input is mocked; passing replay tests does not prove Windows click timing,
complete inventory traversal or AFK readiness. Upstream GPL-3.0 is preserved.

## Milestone 3 — connected shop adapter, Windows validation pending

The new `source/rabbit_hole_shop_policy.py` makes deterministic shop decisions
from *verified* state, and `source/rabbit_hole_shop_controller.py` checks that
each transaction visibly changes inventory, SP, or currency before continuing.
**The runtime now calls `WindowsShopAdapter` at shops.** It reads the shelf and
inventory, executes the chosen action, verifies the transaction, and leaves when
no eligible action remains. It does not call upstream tier-only selling.

Inventory observation opens and cancels sale dialogs to read exact item names and
prices, scrolls to the end, and checks target enhancement levels separately. The
floor-1 event-check sinner is Yi Sang, matching the supplied recording. Unknown
text, ambiguous protected names, unsupported SP readings or failed transitions
still produce a diagnostic checkpoint. The recordings support the displayed
layout, not every possible gift or SP value; live Windows testing is still needed.

* Sell an identified, unprotected gift **only when a specific pending action
  costs more than available currency**. Prefer other spare gifts before
  Cigarette Holder. Retain Grand Welcome throughout floor 1.
* Never sell **or consume as fusion material**: Clear Mirror, Calm Water;
  Fragment of Decay; Fragment of Conceit; Artistic Sense; Sharp Needles & Threads.
* If a required gift cannot be bought or fused, **continue the dungeon with
  available gifts**. An unrecognized screen or an unverified transaction is
  a separate safety checkpoint, not a missing-gift condition.
* On floor 1, restore a verified non-Faust event-check ID to 45 SP.
  Restore Faust to 45 SP **only at the floor-4 shop**, never at floors 2/3/5.
* A tier-IV gift costs **300 currency from base to ++** (100 then 200).
  Clear Mirror, Calm Water++ plus Artistic Sense++ require up to 600,
  plus 100 per floor-4 Faust treatment when needed. The recorded option adds
  45 SP, so negative starting SP can require two treatments: up to 800 total
  for both base-to-++ upgrades and healing. Verify each result and recompute.
* Floors 1–3 prioritize tier-II/III materials and Fragment of Conceit;
  floor 4 prioritizes essential gifts and upgrades, without consuming protected
  ingredients.

The adapter can make one keyword-fusion attempt per missing target per visit,
using three identified unprotected ingredients whose tier points total at least
25. It requires a visible guaranteed tier-IV forecast and 90% intended-keyword
chance, with Wishmaking off. All three ingredient icons are checked again on
confirmation. The resulting gift is read and checked against consumed ingredients;
a different verified result is not treated as a failed transaction. The policy
then continues with available gifts. No refresh or Starlight spending is added.

The controller verifies exact currency changes and inventory differences. Healing
can repeat only after a verified 45-SP gain, until the intended sinner reaches
+45 or no affordable action remains. Transactions are never retried blindly.

## Remaining milestones after the shop

1. Validate Awakening, turn 2, Faelantern, Knight of Despair retries and Sign of
   Roses on Windows. The solo controller, retry menu and three-target verifier
   are implemented; live input, retry redeployment and additional layouts remain.
2. Automate startup, gifts, events, trials, pack search, rewards and transitions.
3. Add bounded recovery, restart/repeat runs and resource/stop conditions.
4. Validate complete and repeated AFK runs on Windows.

The intended final mode is autonomous. Current checkpoints mark unfinished or
unrecognized behavior; this build is still a calibration draft.

## Startup integration update

Rabbit Hole calls the same `Bot.dungeon_start` and `select_grace` functions as
normal MD, starting outside the dungeon with floor 1 selected. It uses the
prepared Rupture preset. Its callback replaces the ordinary affinity gifts with
Cigarette Holder followed by two Keywordless searches: Grand Welcome (70
Starlight) and Sharp Needle & Thread (90). It verifies list entries, selection
count, total cost and the confirmation dialog; hovered icons do not prove
selection. Unexpected selections stop before purchase. Input is guarded by
focus/Stop checks, and transitions are bounded without repeated purchases.

The shared team-confirmation handler still tries the existing ConfirmInvert
recognizer first. A new specific underlevel-message template supports the
supplied popup when the old button template does not match. This applies to
normal MD startup too; Rabbit Hole has no separate popup handler.

Fourteen startup tests cover shared navigation, strategy defaults, warning
handling, exact gift selection, cost mismatch, missing gifts, and replay of the
eight supplied screenshots. Enable those three screenshot replay tests with
`RABBIT_STARTUP_CAPTURE_DIR` pointing to the original PNG folder. Originals are
not bundled. Actual Windows clicks and transition timing await validation.

## Shared progression update

Rabbit Hole now calls the existing event, EGO gift, reward-card, confirmation,
victory/reward collection and defeat handlers. Reward priorities are initialized
with Rupture, Poise and Sinking gifts and relevant Keywordless preferences,
without changing the Rupture preset tag. Events that start fights lead into the
ordinary solo combat controller. Floor-number recognition, difficulty switching
and exact route selection remain in the shared pack handler.

Trials use the existing recognition and gift/trial selection code, preferring
recognized non-HP options. If those are absent, local OCR selects the lowest
confidently readable positive HP percentage. Ambiguous or missing percentages
stop rather than selecting an arbitrary penalty. The OCR fallback needs live
trial-screen validation. Normal non-Rabbit trial behavior is unchanged.

Recognized server-error dialogs receive at most three retries. Loading waits
and run failures are bounded. Existing resource exhaustion behavior is retained.
The generic blind click-recovery function is not used for unknown combat.

Nine new checks cover actual runtime dispatch to shared handlers, preferences,
run counts, failure limits, Stop, connection retries and HP ranking. The complete
Windows run still needs testing. Pack Search now uses the supplied layouts. Unrecognized combat interfaces and
unsuccessful map entry still produce checkpoints. No full AFK certification is claimed.

## Unavoidable encounter update

Whole-path routing prefers recognized safer routes, but risky floor-3 nodes and
unknown nodes are no longer forbidden. If unavoidable, upstream routing and its
existing map fallback enter them. Faust deploys solo and uses the existing EGO
controller; surviving ordinary enemies use Win Rate. Known bosses encountered
through an unknown node keep their specific handling, including Faelantern's
Damage fallback and KoD turn-3 retry. Unknown combat UI still requires recognition
before inputs. A map fallback that cannot actually enter a node still stops.

## Pack Search update

Exact targets are Flat-broke Gamblers, Hell's Chicken, To be Cleaved, Hatred and
Despair, and Hard Line 2, in floor order. Existing win-screen rewards, repeat runs,
and the configured enkephalin-module setting continue through shared handlers.

Validation: 122 checks passed with 24 external-capture checks skipped. The new
Pack Search screenshot check was enabled, and all 13 early Hollow checks also
passed separately with their original screenshots. Windows inputs remain untested.

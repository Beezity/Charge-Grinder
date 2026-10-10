# Rabbit Hole / Mao Faust — assisted calibration draft

Target: Windows, English Limbus Company, **1920×1080 game client**, Mao Faust.
Based on Walpth/Charge-Grinder commit `306d17325a5b76fc54ca3e036c5d87ab3a730036`.
Strategy source: [Rabbit Hole, updated 8 October 2026](https://docs.google.com/spreadsheets/d/1xt72hupklzKFN8AEvsjphApR1D2CRyYvurzAFMxA76s/htmlview#gid=486536596).

**This draft does not automate a complete run.** It adds strict pack selection,
the floor-5 difficulty switch, conservative map navigation, early first-turn
Hollow overclock and manual checkpoints.
The shop adapter now handles purchases, sales, fusion, upgrades and SP healing
with visual verification. Gifts, trials, events, startup, later combat and reward
collection still require manual action. Shop inputs await live Windows validation.
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
runtime deploys Faust alone using upstream selection. Later boss deployment is manual.

Manually start Normal with level 60+ UT3+ Mao Faust and only Hollow equipped
(TS3+, TS4 preferred). Select graces 1 and 3 and two Gift Searches; obtain
Cigarette Holder, Grand Welcome and Sharp Needles & Threads. The guide estimates
about 21 Starlight lost per run. Start automation at the pack or map screen.

At each checkpoint automation stops and saves a screenshot under
`data/rabbit-hole/`. Read the instruction, complete the step manually, then start
again in the same app. The last recognized floor is retained in that app session.
Each start asks for the current floor, so correct it if you changed floors
manually or started a new run. The draft does not collect rewards or repeat runs.

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

Faelantern exception on floor 3: Slash/Pride/Lust identifies the boss. Field
seven sinners, use their skills on turn 1 alongside Faust's Le Trou, and retry if
Faust is Charmed. Use Boucher un trou only after Faelantern emerges; other sinners
must not attack after turn 1. On floor 4, optional meatshields must not attack.
Choose no HP increase or the lowest HP trial available throughout the run.

The bot uses existing image recognition for pack names and floor numbers. Missing
required packs trigger available refreshes, then a checkpoint for manual Pack
Search. It never chooses a substitute pack. It verifies the difficulty toggle
before choosing. Map routing rejects recognized risky paths on floor 3 and stops
instead of using unknown-node fallback clicks. Recognition can still fail; this
draft needs observed gameplay validation before unattended use.

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
Focused layouts, later turns, later waves, extra slots, unrecognized portraits,
Awakening and floors 4/5 are not handled by this sequence. Failed transitions stop
without repeated clicks. A turn that does not finish in 180 seconds also stops.
Switching away or stopping during a hold releases the mouse button.

The hold duration and Windows input behavior still need a live trial. Recognition
tests use the supplied frames, not independent gameplay captures.

## Remaining calibration

Provide original 1920×1080 screenshots, or preferably a short video, showing:

1. The turn-2 Awakening form, Boucher un trou, and its target indicators.
2. Focused-encounter skill selection with Hollow open and selected.
3. Later: Faelantern charm/emergence, KoD after turn 2, and Sign of Roses with all
   three parts highlighted. The two supplied shop recordings are now calibrated.

Checkpoint screenshots are local only; the draft does not upload them.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**68 tests pass locally**, including policy/controller/settings tests, five supplied combat
screenshot cases, and eight shop video replay tests. To include the originals:

```powershell
$env:RABBIT_CAPTURE_DIR = "C:\path\to\combat-screenshots"
$env:RABBIT_SHOP_VIDEO_DIR = "C:\path\to\OBS Recordings"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Original videos are not distributed. The replay reads the filenames
`2026-10-10 09-19-07.mp4` and `2026-10-10 09-21-37.mp4`.
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

1. Finish Awakening, turn 2, focused combat, Faelantern, Knight of Despair retries,
   and Sign of Roses targeting.
2. Automate startup, gifts, events, trials, pack search, rewards and transitions.
3. Add bounded recovery, restart/repeat runs and resource/stop conditions.
4. Validate complete and repeated AFK runs on Windows.

The intended final mode is autonomous. Current checkpoints mark unfinished or
unrecognized behavior; this build is still a calibration draft.

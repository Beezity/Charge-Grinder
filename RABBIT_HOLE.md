# Rabbit Hole / Mao Faust — Windows test build

Target: English Limbus Company, **1920×1080 game client**, Mao Faust solo.
Based on Walpth/Charge-Grinder commit `306d17325a5b76fc54ca3e036c5d87ab3a730036`.
Strategy: [Rabbit Hole guide](https://docs.google.com/spreadsheets/d/1xt72hupklzKFN8AEvsjphApR1D2CRyYvurzAFMxA76s/htmlview#gid=486536596), with the user's later combat and pack-selection instructions taking precedence.

Startup, starter gifts, Pack Search, navigation, shops, combat, rewards and repeat
runs are connected. This is a source build for live testing, not a validated AFK
release. Automated checks use recorded images and simulated input; this Linux
workspace cannot validate the Windows input bridge or live game timing.

## Windows installation and launch

Extract the complete ZIP into a new folder. Use 64-bit Python **3.11 or 3.12**.
Open PowerShell in the extracted `Charge-Grinder` folder and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-rabbit-hole.txt
.\.venv\Scripts\python.exe App.py
```

Use a fresh virtual environment. RapidOCR supplies OpenCV and local CPU models;
do not mix these requirements with a separate OpenCV-headless installation.
The upstream Windows input bridge, bundled DLL and its startup checks are used.

Alternatively, double-click `Start-Rabbit-Hole.bat`. That launcher enables Rabbit
Hole by default and asks for the current floor. The same mode is available in the
normal app through **Rabbit Hole (Rupture)** beside Arayashu.

Select exactly one MD team with **Rupture as the first keyword**. Disable
Arayashu, Extreme and Luxcavation. Prepare the in-game Rupture preset with level
60+ UT3+ Mao Faust and only Le Trou/Hollow equipped (TS3+, preferably TS4).
Equipment and identities are not changed by the bot.

Start outside Mirror Dungeon with floor 1 selected. When resuming at a map, use
the current floor; at pack selection, use the destination floor. The normal app
asks for the floor when starting Rabbit Hole. A partially completed battle's EGO
history is not persisted across restarts; resume from pack selection or a map.

## Startup, packs and routes

The existing startup navigates into MD, selects the Rupture preset and graces
1 and 3, and confirms the recognized underleveled-team warning. It selects
Cigarette Holder from Poise, enables Gift Search, then selects Grand Welcome and
Sharp Needle & Thread from Keywordless. The two-gift, 160-Starlight purchase is
verified before confirmation.

| Floor | Difficulty | Required pack |
| --- | --- | --- |
| 1 | Normal | Flat-broke Gamblers |
| 2 | Normal | Hell's Chicken |
| 3 | Normal | To be Cleaved |
| 4 | Normal | Hatred and Despair |
| 5 | Hard | Line 2 |

Difficulty changes automatically at floor 5. Pack selection uses an already
offered exact target first. Otherwise it opens Pack Search, scrolls the list,
selects the target, and verifies that the replacement popup names that exact
pack before confirming. It verifies the replaced card and turns off search mode
before pulling. Pack Search spends the game's displayed Starlight cost; it does
not use a substitute pack. Missing/unselectable targets produce a checkpoint.

The existing whole-path planner is retained. Safer recognized routes are
preferred, but unavoidable risky and unknown nodes use the existing navigation
fallback. Recognized bosses retain their specific combat rules.

## Combat

Faust is deployed solo. EGO selection holds her leftmost recognized portrait/slot,
then verifies the EGO menu, selected skill and start controls.

- Floors 1–2 and recognized ordinary floor-3 encounters: overclock Hollow on the
  first turn. Surviving ordinary enemies use Win Rate.
- Other supported ordinary encounters: Le Trou, then Boucher un trou; survivors
  use Win Rate. Unknown floor-3 nodes use this path unless a boss is recognized.
- **Faelantern:** Win Rate until the emerged state is recognized and Faust is
  selectable, then hold Le Trou to select Hollow corrosion. Survivors use Damage.
  Charm does not trigger a retry.
- **Knight of Despair:** Le Trou, then Boucher un trou. Counter 3 triggers Retry
  Stage before any fallback, with at most three retries. EGO history is cleared
  only after verified return to turn 1.
- **Sign of Roses:** Le Trou, then Boucher un trou. Before starting Boucher, verify
  the yellow primary clash and cyan secondary targeting cover both boss parts
  and the flower. If needed, try up to six recognized boss skill targets and
  recheck coverage. If none covers all three, stop without starting the turn.

Usage is recorded after a verified start in the solo controller. Brief unknown
screens receive a bounded recognition wait; they do not cause blind combat input.

## Shops and progression

Shop transactions check item identity, cost, currency changes and inventory
changes. Protected gifts are Clear Mirror, Calm Water; Fragment of Conceit;
Fragment of Decay; Artistic Sense; and Sharp Needle & Thread. Unprotected gifts
are sold only to fund an available action; Cigarette Holder is kept last. Grand
Welcome is protected on floor 1 and can become fusion material afterward.

- Floor 1: buy up to two tier-II/III materials and heal the calibrated non-Faust
  event-check sinner, Yi Sang, toward +45 SP. Do not heal Faust.
- Floors 2–3: buy materials and try to obtain Fragment of Conceit. Keep Clear
  Mirror, Calm Water unupgraded; do not heal Faust.
- Floor 4: heal Faust toward +45 SP, obtain missing target gifts when possible,
  and upgrade Clear Mirror, Calm Water and Artistic Sense to ++.
- Floor 5: no automatic Faust healing or upgrades.

Unavailable gifts do not abort the run. Keyword fusion verifies its forecast and
actual result; it cannot guarantee the desired gift. Unrecognized transactions
stop without repeating a purchase, sale or fusion.

Shared handlers manage events, gift/card rewards, victory collection and defeat.
Trials prioritize recognized non-HP options, otherwise the lowest confidently
read HP increase. The app's run count and Restart setting are respected. Three
consecutive failed runs stop the automation. The configured module-conversion
check runs after every completed attempt, including the final requested run.
New runs reset to floor 1. Stop prevents subsequent transactions and runs.

## Testing and diagnostics

First test one complete run while watching the game, then test multiple runs.
Pay particular attention to startup gifts, scrolling and confirmation in Pack
Search, shop transactions, Faelantern emergence, KoD retry, Roses coverage and
return to the home screen. Leave module conversion enabled only if desired in
the normal app settings.

A checkpoint stops automation and saves a screenshot in `data/rabbit-hole/`.
Preserve the console/log and screenshot when reporting a failure. The original
user recordings and screenshots are not bundled with the ZIP.

Remaining validation is live Windows operation and repeated unattended runs.
Additional combat or trial layouts may require recognition changes. Recorded
frame recognition and unit tests do not establish that live input timing works.

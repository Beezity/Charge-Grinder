"""Windows launcher for the explicitly assisted Rabbit Hole calibration draft."""
import argparse
import os
from pathlib import Path
import runpy


def main():
    parser = argparse.ArgumentParser(description="Rabbit Hole / Mao Faust — assisted calibration draft")
    parser.add_argument("--floor", type=int, choices=range(1, 6), default=1,
                        help="Current floor when resuming, or destination floor at pack selection")
    parser.add_argument("--ask-floor", action="store_true", help="Ask for the current floor before opening the app")
    args = parser.parse_args()
    if args.ask_floor:
        answer = input("Current floor (1-5), or destination floor at pack selection [1]: ").strip() or "1"
        if answer not in {"1", "2", "3", "4", "5"}:
            parser.error("Floor must be 1 through 5.")
        args.floor = int(answer)
    os.chdir(Path(__file__).resolve().parent)
    import source.utils.params as p
    p.RABBIT_HOLE = True
    p.LVL = args.floor
    print("Rabbit Hole draft: MD entry, preset, graces, starting gifts, shops and calibrated combat are connected. Pack Search and shared progression are connected; live Windows validation is pending.")
    runpy.run_path("App.py", run_name="__main__")


if __name__ == "__main__":
    main()

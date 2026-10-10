@echo off
setlocal
cd /d "%~dp0"
echo Rabbit Hole - Mao Faust - ASSISTED CALIBRATION DRAFT
echo Early overclock is implemented; later combat and shops are manual. Read RABBIT_HOLE.md.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RabbitHole.py --ask-floor
) else (
    py RabbitHole.py --ask-floor
)
pause
